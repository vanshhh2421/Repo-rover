from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Request

from app.core.settings import settings
from app.infrastructure.neo4j_client import Neo4jClient
from app.infrastructure.vector_store import VectorStore

router = APIRouter(prefix="/test", tags=["test"])


@router.post("/reset")
def reset_database(request: Request):
    neo4j: Neo4jClient = request.app.state.neo4j
    neo4j.wipe_all()
    neo4j.init_schema()

    VectorStore.clear_all()

    dirs_to_delete = [Path(settings.chroma_dir), Path(settings.work_dir)]
    deleted = []
    for d in dirs_to_delete:
        if d.exists() and d.is_dir():
            try:
                shutil.rmtree(d, ignore_errors=True)
                deleted.append(str(d))
            except Exception:
                pass

    return {
        "status": "success",
        "message": "Database reset complete",
        "directories_deleted": deleted,
    }
