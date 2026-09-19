from __future__ import annotations

from neo4j import Driver, GraphDatabase

from app.core.settings import settings


class Neo4jClient:
    def __init__(self, driver: Driver) -> None:
        self.driver = driver

    @classmethod
    def from_settings(cls) -> Neo4jClient:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        return cls(driver)

    def close(self) -> None:
        self.driver.close()

    def init_schema(self) -> None:
        queries = [
            "CREATE CONSTRAINT repo_key IF NOT EXISTS FOR (r:Repository) REQUIRE r.repo_id IS UNIQUE",
            "CREATE CONSTRAINT file_key IF NOT EXISTS FOR (f:File) REQUIRE (f.repo_id, f.path) IS UNIQUE",
            "CREATE CONSTRAINT func_key IF NOT EXISTS FOR (fn:Function) REQUIRE (fn.repo_id, fn.qualified_name) IS UNIQUE",
            "CREATE CONSTRAINT class_key IF NOT EXISTS FOR (c:Class) REQUIRE (c.repo_id, c.qualified_name) IS UNIQUE",
        ]
        with self.driver.session() as s:
            for q in queries:
                s.run(q)

    def ensure_repository(self, repo_id: str) -> None:
        with self.driver.session() as s:
            s.run(
                "MERGE (r:Repository {repo_id: $repo_id})",
                repo_id=repo_id,
            )

    def upsert_file(self, repo_id: str, path: str) -> None:
        with self.driver.session() as s:
            s.run(
                """
                MERGE (f:File {repo_id: $repo_id, path: $path})
                """,
                repo_id=repo_id,
                path=path,
            )

    def upsert_function(
        self, repo_id: str, qualified_name: str, name: str, file_path: str
    ) -> None:
        with self.driver.session() as s:
            s.run(
                """
                MERGE (fn:Function {repo_id: $repo_id, qualified_name: $qualified_name})
                SET fn.name = $name
                WITH fn
                MATCH (f:File {repo_id: $repo_id, path: $file_path})
                MERGE (f)-[:DEFINES]->(fn)
                """,
                repo_id=repo_id,
                qualified_name=qualified_name,
                name=name,
                file_path=file_path,
            )

    def upsert_class(
        self, repo_id: str, qualified_name: str, name: str, file_path: str
    ) -> None:
        with self.driver.session() as s:
            s.run(
                """
                MERGE (c:Class {repo_id: $repo_id, qualified_name: $qualified_name})
                SET c.name = $name
                WITH c
                MATCH (f:File {repo_id: $repo_id, path: $file_path})
                MERGE (f)-[:DEFINES]->(c)
                """,
                repo_id=repo_id,
                qualified_name=qualified_name,
                name=name,
                file_path=file_path,
            )

    def add_belongs_to(self, repo_id: str, qualified_names: list[str]) -> None:
        if not qualified_names:
            return
        with self.driver.session() as s:
            s.run(
                """
                UNWIND $qns AS qn
                MATCH (r:Repository {repo_id: $repo_id})
                MATCH (sym {repo_id: $repo_id, qualified_name: qn})
                MERGE (sym)-[:BELONGS_TO]->(r)
                """,
                repo_id=repo_id,
                qns=qualified_names,
            )

    def add_calls(self, repo_id: str, caller_qn: str, callees: list[str]) -> None:
        if not callees:
            return
        with self.driver.session() as s:
            s.run(
                """
                MATCH (caller:Function {repo_id: $repo_id, qualified_name: $caller_qn})
                UNWIND $callees AS callee_name
                MERGE (callee:Function {repo_id: $repo_id, qualified_name: $repo_id + '::external::' + callee_name})
                SET callee.name = callee_name
                MERGE (caller)-[:CALLS]->(callee)
                """,
                repo_id=repo_id,
                caller_qn=caller_qn,
                callees=callees[:200],
            )

    def add_references(
        self, repo_id: str, file_path: str, symbol_qns: list[str]
    ) -> None:
        if not symbol_qns:
            return
        with self.driver.session() as s:
            s.run(
                """
                MATCH (f:File {repo_id: $repo_id, path: $file_path})
                UNWIND $qns AS qn
                MATCH (sym {repo_id: $repo_id, qualified_name: qn})
                MERGE (f)-[:REFERENCES]->(sym)
                """,
                repo_id=repo_id,
                file_path=file_path,
                qns=symbol_qns[:500],
            )

    def delete_files(self, repo_id: str, file_paths: list[str]) -> None:
        if not file_paths:
            return
        with self.driver.session() as s:
            s.run(
                """
                MATCH (f:File {repo_id: $repo_id})
                WHERE f.path IN $file_paths
                OPTIONAL MATCH (f)-[:DEFINES]->(sym)
                DETACH DELETE f, sym
                """,
                repo_id=repo_id,
                file_paths=file_paths,
            )

    def find_symbol(self, repo_id: str, symbol_name: str) -> list[dict]:
        with self.driver.session() as s:
            result = s.run(
                """
                MATCH (sym {repo_id: $repo_id})
                WHERE sym.name = $name OR sym.qualified_name CONTAINS $name
                RETURN
                  sym.qualified_name AS qualified_name,
                  labels(sym)[0] AS kind,
                  sym.file_path AS file_path,
                  sym.name AS name
                LIMIT 10
                """,
                repo_id=repo_id,
                name=symbol_name,
            )
            return [dict(r) for r in result]

    def get_callers(self, repo_id: str, qn: str) -> list[dict]:
        with self.driver.session() as s:
            result = s.run(
                """
                MATCH (caller:Function {repo_id: $repo_id})-[:CALLS]->(callee:Function {repo_id: $repo_id, qualified_name: $qn})
                RETURN caller.name AS caller_name,
                       caller.qualified_name AS caller_qn,
                       caller.file_path AS file_path
                LIMIT 50
                """,
                repo_id=repo_id,
                qn=qn,
            )
            return [dict(r) for r in result]

    def get_file_dependencies(self, repo_id: str, file_path: str) -> dict:
        with self.driver.session() as s:
            imports_result = s.run(
                """
                MATCH (f:File {repo_id: $repo_id, path: $file_path})-[:DEFINES]->(fn:Function)
                OPTIONAL MATCH (fn)-[:CALLS]->(callee:Function)
                RETURN DISTINCT callee.qualified_name AS target_qn,
                       callee.name AS target_name,
                       "function" AS target_kind
                LIMIT 100
                """,
                repo_id=repo_id,
                file_path=file_path,
            )
            imports = [dict(r) for r in imports_result if r.get("target_qn")]

            imported_by_result = s.run(
                """
                MATCH (f:File {repo_id: $repo_id, path: $file_path})
                MATCH (caller:Function)-[:CALLS]->(callee:Function)
                WHERE callee.file_path = $file_path
                MATCH (caller_file:File)-[:DEFINES]->(caller)
                RETURN DISTINCT caller_file.path AS source_path
                LIMIT 50
                """,
                repo_id=repo_id,
                file_path=file_path,
            )
            imported_by = [r["source_path"] for r in imported_by_result if r.get("source_path")]

        return {"imports": imports, "imported_by": imported_by}

    def list_files(self, repo_id: str) -> list[str]:
        with self.driver.session() as s:
            result = s.run(
                """
                MATCH (f:File {repo_id: $repo_id})
                RETURN f.path AS path
                ORDER BY f.path
                """,
                repo_id=repo_id,
            )
            return [r["path"] for r in result if r.get("path")]

    def wipe_all(self) -> None:
        with self.driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")
