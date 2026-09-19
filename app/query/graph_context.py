from __future__ import annotations

from app.infrastructure.neo4j_client import Neo4jClient


def _dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def expand_neighborhood(
    neo4j: Neo4jClient,
    repo_id: str,
    qualified_names: list[str],
    depth: int = 1,
) -> list[str]:
    if not qualified_names:
        return []
    d = max(1, min(int(depth), 3))
    query = f"""
    MATCH (s {{repo_id: $repo_id}})
    WHERE s.qualified_name IN $qns
    CALL (s) {{
      MATCH (s)-[:CALLS|DEFINES|REFERENCES|BELONGS_TO*1..{d}]-(n)
      RETURN DISTINCT n.qualified_name AS qn
    }}
    RETURN DISTINCT qn
    """
    with neo4j.driver.session() as sess:
        result = sess.run(query, repo_id=repo_id, qns=qualified_names)
        out = [r["qn"] for r in result if r.get("qn")]
        return _dedupe(out)[:50]


def files_mentioning_symbol(
    neo4j: Neo4jClient, repo_id: str, symbol_name: str
) -> list[str]:
    query = """
    MATCH (sym {repo_id: $repo_id})
    WHERE sym.name = $name
    MATCH (f:File)-[:REFERENCES]->(sym)
    RETURN DISTINCT f.path AS path
    LIMIT 30
    """
    with neo4j.driver.session() as sess:
        result = sess.run(query, repo_id=repo_id, name=symbol_name)
        return [r["path"] for r in result if r.get("path")]


def get_call_flows(
    neo4j: Neo4jClient,
    repo_id: str,
    qualified_names: list[str],
    max_depth: int = 4,
) -> list[str]:
    if not qualified_names:
        return []
    query = f"""
    MATCH path = (s:Function {{repo_id: $repo_id}})-[:CALLS*1..{max_depth}]->(n:Function)
    WHERE s.qualified_name IN $qns
    RETURN [node in nodes(path) | node.name] AS call_chain
    """
    with neo4j.driver.session() as sess:
        result = sess.run(query, repo_id=repo_id, qns=qualified_names)
        out = [" -> ".join(r["call_chain"]) for r in result if r.get("call_chain")]
        return out[:50]


def snippet_around(text: str, needle: str, max_len: int = 900) -> str:
    idx = text.lower().find(needle.lower())
    if idx < 0:
        return text[:max_len]
    start = max(0, idx - 200)
    end = min(len(text), idx + 600)
    return text[start:end]
