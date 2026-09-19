from __future__ import annotations

from pathlib import Path

from tree_sitter import Node


def _get_text(src: bytes, node: Node | None) -> str:
    if node is None:
        return ""
    return src[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")


def _resolve_python_module(
    repo_root: Path, current_file_rel: Path, module_name: str, level: int = 0
) -> Path | None:
    parts = module_name.split(".") if module_name else []

    if level > 0:
        base_dir = repo_root / current_file_rel.parent
        for _ in range(level - 1):
            base_dir = base_dir.parent
        search_path = base_dir.joinpath(*parts)
    else:
        search_path = repo_root.joinpath(*parts)

    file_target = search_path.with_suffix(".py")
    if file_target.is_file():
        return file_target.relative_to(repo_root)

    pkg_target = search_path / "__init__.py"
    if pkg_target.is_file():
        return pkg_target.relative_to(repo_root)

    return None


def resolve_python_import(
    repo_root: Path, current_file_rel: str, import_node: Node, src: bytes
) -> list[str]:
    resolved_fqns: list[str] = []
    curr_path = Path(current_file_rel)

    if import_node.type == "import_from_statement":
        module_node = None
        for child in import_node.named_children:
            if child.type == "dotted_name":
                module_node = child
                break
        raw_text = _get_text(src, import_node)
        level = 0
        if raw_text.startswith("from"):
            after_from = raw_text[4:].lstrip()
            while after_from.startswith("."):
                level += 1
                after_from = after_from[1:]
        module_name = _get_text(src, module_node) if module_node else ""
        rel_target = _resolve_python_module(repo_root, curr_path, module_name, level)
        if not rel_target:
            return []
        for child in import_node.named_children:
            if child.type == "dotted_name" and child != module_node:
                name = _get_text(src, child)
                resolved_fqns.append(f"{rel_target.as_posix()}::{name}")
            elif child.type == "aliased_import":
                orig = child.named_children[0] if child.named_children else None
                name = _get_text(src, orig)
                resolved_fqns.append(f"{rel_target.as_posix()}::{name}")

    elif import_node.type == "import_statement":
        for child in import_node.named_children:
            if child.type == "dotted_name":
                module_name = _get_text(src, child)
                rel_target = _resolve_python_module(repo_root, curr_path, module_name, 0)
                if rel_target:
                    resolved_fqns.append(f"{rel_target.as_posix()}::")
            elif child.type == "aliased_import":
                orig = child.named_children[0] if child.named_children else None
                module_name = _get_text(src, orig)
                rel_target = _resolve_python_module(repo_root, curr_path, module_name, 0)
                if rel_target:
                    resolved_fqns.append(f"{rel_target.as_posix()}::")

    return resolved_fqns


def resolve_import(
    lang: str,
    repo_root: Path,
    current_file_rel: str,
    import_node: Node,
    src: bytes,
) -> list[str]:
    if lang == "python":
        return resolve_python_import(repo_root, current_file_rel, import_node, src)
    return []
