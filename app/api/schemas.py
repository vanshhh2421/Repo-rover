from __future__ import annotations

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    repo_id: str = Field(..., alias="repoId")
    source: str = Field(..., alias="sourceUrl")
    branch: str | None = None
    added_or_modified_files: list[str] = Field(default_factory=list, alias="addedOrModifiedFiles")
    deleted_files: list[str] = Field(default_factory=list, alias="deletedFiles")


class IngestResponse(BaseModel):
    repo_id: str
    files_indexed: int
    symbols_indexed: int


class QueryRequest(BaseModel):
    repo_id: str = Field(..., alias="repoId")
    question: str
    top_k: int = 8


class QueryResponse(BaseModel):
    answer: str
    context_items: int
