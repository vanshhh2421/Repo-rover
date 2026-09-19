from __future__ import annotations

import os
from functools import lru_cache

import chromadb
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.settings import settings

os.environ["CHROMA_TELEMETRY"] = "false"


@lru_cache(maxsize=1)
def _embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=settings.embed_model,
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=32)
def _chroma_for_repo(repo_id: str) -> Chroma:
    client = chromadb.PersistentClient(path=settings.chroma_dir)
    return Chroma(
        client=client,
        collection_name=f"reporover_{repo_id}",
        embedding_function=_embeddings(),
    )


class VectorStore:
    def __init__(self, repo_id: str) -> None:
        self._repo_id = repo_id
        self._chroma = _chroma_for_repo(repo_id)

    @classmethod
    def from_settings(cls, repo_id: str) -> VectorStore:
        return cls(repo_id)

    @classmethod
    def clear_all(cls) -> None:
        _chroma_for_repo.cache_clear()
        try:
            client = chromadb.PersistentClient(path=settings.chroma_dir)
            for collection in client.list_collections():
                client.delete_collection(collection.name)
        except Exception:
            pass

    @classmethod
    def clear_repo(cls, repo_id: str) -> None:
        _chroma_for_repo.cache_clear()
        try:
            client = chromadb.PersistentClient(path=settings.chroma_dir)
            for c in client.list_collections():
                if c.name == f"reporover_{repo_id}":
                    client.delete_collection(c.name)
                    break
        except Exception:
            pass

    def upsert_documents(
        self, ids: list[str], texts: list[str], metadatas: list[dict]
    ) -> None:
        if not ids:
            return
        self._chroma.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def as_retriever(self, top_k: int = 8) -> VectorStoreRetriever:
        return self._chroma.as_retriever(search_kwargs={"k": top_k})

    def get_documents_by_qns(self, qns: list[str]) -> list[str]:
        if not qns:
            return []
        try:
            results = self._chroma.get(where={"qualified_name": {"$in": qns}})
            return results.get("documents", []) or []
        except Exception:
            return []
