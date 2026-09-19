import sys
import traceback
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from app.core.settings import settings
from app.infrastructure.neo4j_client import Neo4jClient
from app.services.ingest_service import ingest_repo


def main():
    if len(sys.argv) < 3:
        print("Usage: python test_ingest.py <repo_id> <source_path>")
        sys.exit(1)

    repo_id = sys.argv[1]
    source = sys.argv[2]

    print(f"Ingesting {source} as repo '{repo_id}'...")

    neo4j = Neo4jClient.from_settings()
    try:
        result = ingest_repo(
            neo4j=neo4j,
            repo_id=repo_id,
            source=source,
        )
        print(f"Files indexed: {result.files_indexed}")
        print(f"Symbols indexed: {result.symbols_indexed}")
        print("Done.")
    except Exception as e:
        print("ERROR:")
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
