from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from app.infrastructure.neo4j_client import Neo4jClient
from app.infrastructure.vector_store import VectorStore
from app.ingestion.ast_extract import ClassSymbol, FunctionSymbol, iter_code_files
from app.ingestion.indexer import index_repo

LANG_MAP: dict[str, Language | None] = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".jsx": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
}


def _doc_id(repo_id: str, qualified_name: str) -> str:
    h = hashlib.sha256(f"{repo_id}|{qualified_name}".encode("utf-8")).hexdigest()[:24]
    return f"sym_{h}"


@dataclass
class IngestResult:
    repo_id: str
    files_indexed: int
    symbols_indexed: int


def ingest_repo(
    neo4j: Neo4jClient,
    repo_id: str,
    source: str,
    branch: str | None = None,
    added_or_modified_files: list[str] | None = None,
    deleted_files: list[str] | None = None,
) -> IngestResult:
    repo_root = Path(source).resolve()
    if not repo_root.is_dir():
        raise ValueError(f"Repository path does not exist: {source}")

    if deleted_files:
        neo4j.delete_files(repo_id, deleted_files)

    indexed = index_repo(
        repo_id=repo_id,
        repo_root=repo_root,
        target_files=added_or_modified_files,
    )

    neo4j.ensure_repository(repo_id)

    for f in indexed.files:
        neo4j.upsert_file(repo_id=repo_id, path=f.rel_path)

    all_functions: list[FunctionSymbol] = []
    all_classes: list[ClassSymbol] = []

    for f in indexed.files:
        for sym in f.symbols:
            if isinstance(sym, FunctionSymbol):
                all_functions.append(sym)
            elif isinstance(sym, ClassSymbol):
                all_classes.append(sym)

    for fn in all_functions:
        neo4j.upsert_function(
            repo_id=repo_id,
            qualified_name=fn.qualified_name,
            name=fn.name,
            file_path=fn.file_path,
        )
        if fn.calls:
            neo4j.add_calls(
                repo_id=repo_id,
                caller_qn=fn.qualified_name,
                callees=fn.calls,
            )

    for cls in all_classes:
        neo4j.upsert_class(
            repo_id=repo_id,
            qualified_name=cls.qualified_name,
            name=cls.name,
            file_path=cls.file_path,
        )

    all_symbol_qns = [s.qualified_name for s in all_functions] + [s.qualified_name for s in all_classes]
    neo4j.add_belongs_to(repo_id=repo_id, qualified_names=all_symbol_qns)

    name_to_qn: dict[str, str] = {}
    for s in all_functions:
        name_to_qn.setdefault(s.name, s.qualified_name)
    for s in all_classes:
        name_to_qn.setdefault(s.name, s.qualified_name)

    for f in indexed.files:
        mentioned = [qn for name, qn in name_to_qn.items() if name in f.identifiers]
        neo4j.add_references(repo_id=repo_id, file_path=f.rel_path, symbol_qns=mentioned)

    vs = VectorStore.from_settings(repo_id=repo_id)
    doc_ids: list[str] = []
    doc_texts: list[str] = []
    doc_metadatas: list[dict] = []
    seen_ids: set[str] = set()

    file_texts = {f.rel_path: f.source_text for f in indexed.files}
    grouped: dict[str, list[FunctionSymbol | ClassSymbol]] = {}
    for f in indexed.files:
        grouped.setdefault(f.rel_path, []).extend(f.symbols)

    for file_path, symbols in grouped.items():
        text = file_texts.get(file_path, "")
        if not text:
            continue

        raw = text.encode("utf-8")
        ext = Path(file_path).suffix.lower()
        lang = LANG_MAP.get(ext)
        splitter = (
            RecursiveCharacterTextSplitter.from_language(language=lang, chunk_size=2000, chunk_overlap=200)
            if lang
            else RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        )

        for sym in symbols:
            code = raw[sym.start_byte : sym.end_byte].decode("utf-8", errors="ignore")
            if not code:
                continue

            chunks = splitter.split_text(code)
            for i, chunk in enumerate(chunks):
                did = _doc_id(repo_id, sym.qualified_name)
                if len(chunks) > 1:
                    did = f"{did}_ch{i}"
                if did in seen_ids:
                    continue
                seen_ids.add(did)

                doc_ids.append(did)
                doc_texts.append(f"{sym.qualified_name}\n\n{chunk}")
                doc_metadatas.append(
                    {
                        "repo_id": repo_id,
                        "qualified_name": sym.qualified_name,
                        "kind": "function" if isinstance(sym, FunctionSymbol) else "class",
                        "file_path": file_path,
                        "name": sym.name,
                        "chunk_index": i,
                    }
                )

    vs.upsert_documents(ids=doc_ids, texts=doc_texts, metadatas=doc_metadatas)

    return IngestResult(
        repo_id=repo_id,
        files_indexed=len(indexed.files),
        symbols_indexed=len(all_functions) + len(all_classes),
    )
