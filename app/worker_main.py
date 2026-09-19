from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers.health import router as health_router
from app.api.routers.ingest import router as ingest_router
from app.api.routers.query import router as query_router
from app.api.routers.test import router as test_router
from app.infrastructure.neo4j_client import Neo4jClient


import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    neo4j = None
    try:
        neo4j = Neo4jClient.from_settings()
        neo4j.init_schema()
        logger.info("Neo4j connected")
    except Exception as e:
        logger.warning("Neo4j unavailable: %s. Ingest endpoints will fail until Neo4j is running.", e)
    app.state.neo4j = neo4j
    try:
        yield
    finally:
        if neo4j:
            neo4j.close()


app = FastAPI(title="RepoRover API", version="0.1.0", lifespan=lifespan)

app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(test_router)
