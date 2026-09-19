from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ingestion.ast_extract import FunctionSymbol, ClassSymbol, parse_file, iter_code_files


@dataclass
class IndexedFile:
    rel_path: str
    source_text: str
    symbols: list[FunctionSymbol | ClassSymbol]
    imports: list[str]
    resolved_imports: list[str]
    identifiers: set[str]


@dataclass
class IndexedRepo:
    repo_id: str
    repo_root: Path
    files: list[IndexedFile]


def index_repo(
    repo_id: str,
    repo_root: Path,
    target_files: list[str] | None = None,
) -> IndexedRepo:
    indexed_files: list[IndexedFile] = []

    if target_files is not None:
        file_paths = [repo_root / p for p in target_files if (repo_root / p).is_file()]
    else:
        file_paths = iter_code_files(repo_root)

    for fp in file_paths:
        result = parse_file(fp, repo_root)
        if result is None:
            continue

        rel = str(fp.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
        indexed_files.append(
            IndexedFile(
                rel_path=rel,
                source_text=result.source_text,
                symbols=result.symbols,
                imports=result.imports,
                resolved_imports=result.resolved_imports,
                identifiers=result.identifiers,
            )
        )

    return IndexedRepo(repo_id=repo_id, repo_root=repo_root, files=indexed_files)
