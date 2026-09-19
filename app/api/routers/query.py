from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.schemas import QueryRequest, QueryResponse
from app.services.query_service import answer_question

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, request: Request):
    neo4j = request.app.state.neo4j
    result = await answer_question(
        neo4j=neo4j,
        repo_id=req.repo_id,
        question=req.question,
        top_k=req.top_k,
    )
    return QueryResponse(
        answer=result.answer,
        context_items=result.context_items,
    )
