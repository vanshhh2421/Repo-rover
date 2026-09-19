from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path

from tree_sitter import Node
from tree_sitter_languages import get_parser

from app.ingestion.import_resolver import resolve_import

EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
}

_SKIP_DIRS = {".work", ".chroma", "node_modules", ".git", ".venv", "dist", "build", "__pycache__"}


class Symbol(ABC):
    qualified_name: str
    name: str
    file_path: str
    start_byte: int
    end_byte: int


@dataclass
class FunctionSymbol(Symbol):
    qualified_name: str
    name: str
    file_path: str
    start_byte: int
    end_byte: int
    calls: list[str] = field(default_factory=list)


@dataclass
class ClassSymbol(Symbol):
    qualified_name: str
    name: str
    file_path: str
    start_byte: int
    end_byte: int


@dataclass
class ParseResult:
    symbols: list[FunctionSymbol | ClassSymbol]
    source_text: str
    imports: list[str]
    resolved_imports: list[str]
    identifiers: set[str]


def _text(src: bytes, tree_node: Node | None) -> str:
    if tree_node is None:
        return ""
    return src[tree_node.start_byte : tree_node.end_byte].decode("utf-8", errors="ignore")


def _named_child(tree_node: Node, child_type: str) -> Node | None:
    for c in tree_node.named_children:
        if c.type == child_type:
            return c
    return None


def _collect_nodes(root: Node, node_types: set[str]) -> list[Node]:
    result: list[Node] = []
    stack: list[Node] = [root]
    while stack:
        current = stack.pop()
        if current.type in node_types:
            result.append(current)
        stack.extend(reversed(current.named_children))
    return result


def _collect_callee_names(src: bytes, scope: Node) -> list[str]:
    call_nodes = _collect_nodes(scope, {"call", "call_expression"})
    names: list[str] = []
    for cn in call_nodes:
        callee = cn.named_children[0] if cn.named_children else None
        if callee:
            text = _text(src, callee).strip()
            if text:
                names.append(text[:200])
    return names


def _build_fqn(src: bytes, rel_path: str, start_at: Node, local_name: str) -> str:
    segments = [local_name]
    parent = start_at.parent
    while parent:
        if parent.type in {"class_definition", "class_declaration", "function_definition", "function_declaration"}:
            name_node = _named_child(parent, "name") or _named_child(parent, "identifier")
            if name_node:
                segments.append(_text(src, name_node).strip())
        parent = parent.parent
    segments.reverse()
    return f"{rel_path}::{'.'.join(segments)}"


def _extract_imports(src: bytes, root: Node, lang: str, repo_root: Path, rel_path: str) -> tuple[list[str], list[str]]:
    import_node_types = {"import_statement", "import_from_statement", "import_declaration"}
    raw_imports: list[str] = []
    resolved: list[str] = []
    for node in _collect_nodes(root, import_node_types):
        snippet = _text(src, node).strip()
        if snippet:
            raw_imports.append(snippet[:300])
        resolved.extend(resolve_import(lang, repo_root, rel_path, node, src))
    return raw_imports, resolved


def _extract_functions(src: bytes, root: Node, rel_path: str) -> list[FunctionSymbol]:
    func_types = {"function_definition", "function_declaration", "method_definition"}
    symbols: list[FunctionSymbol] = []
    for node in _collect_nodes(root, func_types):
        name_node = _named_child(node, "name") or _named_child(node, "identifier")
        name = _text(src, name_node).strip() if name_node else "anonymous"
        symbols.append(
            FunctionSymbol(
                qualified_name=_build_fqn(src, rel_path, node, name),
                name=name,
                file_path=rel_path,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                calls=_collect_callee_names(src, node),
            )
        )
    return symbols


def _extract_arrow_functions(src: bytes, root: Node, rel_path: str) -> list[FunctionSymbol]:
    symbols: list[FunctionSymbol] = []
    for vd in _collect_nodes(root, {"variable_declarator"}):
        ident = _named_child(vd, "identifier")
        if ident is None:
            continue
        name = _text(src, ident).strip()
        fn_node = None
        for c in vd.named_children:
            if c is ident:
                continue
            if c.type in {"arrow_function", "function", "function_expression"}:
                fn_node = c
                break
        if fn_node is None:
            continue
        symbols.append(
            FunctionSymbol(
                qualified_name=_build_fqn(src, rel_path, fn_node, name),
                name=name,
                file_path=rel_path,
                start_byte=fn_node.start_byte,
                end_byte=fn_node.end_byte,
                calls=_collect_callee_names(src, fn_node),
            )
        )
    return symbols


def _extract_classes(src: bytes, root: Node, rel_path: str) -> list[ClassSymbol]:
    class_types = {"class_definition", "class_declaration"}
    symbols: list[ClassSymbol] = []
    for node in _collect_nodes(root, class_types):
        name_node = _named_child(node, "name") or _named_child(node, "identifier")
        name = _text(src, name_node).strip() if name_node else "AnonymousClass"
        symbols.append(
            ClassSymbol(
                qualified_name=_build_fqn(src, rel_path, node, name),
                name=name,
                file_path=rel_path,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
            )
        )
    return symbols


def _extract_identifiers(src: bytes, root: Node) -> set[str]:
    identifiers: set[str] = set()
    for node in _collect_nodes(root, {"identifier"}):
        text = _text(src, node).strip()
        if text:
            identifiers.add(text)
    return identifiers


def parse_file(file_path: Path, repo_root: Path) -> ParseResult | None:
    ext = file_path.suffix.lower()
    lang = EXT_TO_LANG.get(ext)
    if lang is None:
        return None

    src = file_path.read_bytes()
    parser = get_parser(lang)
    tree = parser.parse(src)
    root = tree.root_node

    rel_path = str(file_path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")

    raw_imports, resolved_imports = _extract_imports(src, root, lang, repo_root, rel_path)
    functions = _extract_functions(src, root, rel_path)
    arrow_functions = _extract_arrow_functions(src, root, rel_path)
    classes = _extract_classes(src, root, rel_path)
    identifiers = _extract_identifiers(src, root)

    source_text = src.decode("utf-8", errors="ignore")

    return ParseResult(
        symbols=[*functions, *arrow_functions, *classes],
        source_text=source_text,
        imports=raw_imports,
        resolved_imports=resolved_imports,
        identifiers=identifiers,
    )


def iter_code_files(repo_root: Path) -> list[Path]:
    exts = set(EXT_TO_LANG.keys())
    found: list[Path] = []

    for dirpath, dirnames, filenames in __import__("os").walk(str(repo_root.resolve())):
        dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP_DIRS]
        for f in filenames:
            p = Path(dirpath) / f
            if p.suffix.lower() in exts:
                found.append(p)
    return found
