from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import IngestRequest, IngestResponse
from app.services.ingest_service import ingest_repo

router = APIRouter()

_executor = ThreadPoolExecutor()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest, request: Request):
    neo4j = request.app.state.neo4j
    if neo4j is None:
        raise HTTPException(status_code=503, detail="Neo4j is not connected")
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            _executor,
            ingest_repo,
            neo4j,
            req.repo_id,
            req.source,
            req.branch,
            req.added_or_modified_files,
            req.deleted_files,
        )
        return IngestResponse(
            repo_id=result.repo_id,
            files_indexed=result.files_indexed,
            symbols_indexed=result.symbols_indexed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
