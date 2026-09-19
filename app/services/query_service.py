from __future__ import annotations

import time
from dataclasses import dataclass

from app.infrastructure.neo4j_client import Neo4jClient
from app.query.agent import run_agent_query


@dataclass
class QueryResult:
    answer: str
    context_items: int


async def answer_question(
    neo4j: Neo4jClient, repo_id: str, question: str, top_k: int
) -> QueryResult:
    start = time.monotonic()
    answer, tool_calls = await run_agent_query(
        neo4j=neo4j, repo_id=repo_id, question=question
    )
    elapsed = time.monotonic() - start
    print(f"[QUERY] repo={repo_id} tools={tool_calls} elapsed={elapsed:.2f}s")
    return QueryResult(answer=answer, context_items=tool_calls)
