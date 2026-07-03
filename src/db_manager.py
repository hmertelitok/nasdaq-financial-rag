import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = PROJECT_ROOT / "data" / "database"
DB_PATH = DATABASE_DIR / "nasdaq_financial_rag.db"
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"


SUPPORTED_COMPANIES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}


def get_connection() -> sqlite3.Connection:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")

    return connection


def initialize_database() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema dosyası bulunamadı: {SCHEMA_PATH}")

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        connection.executescript(schema_sql)
        seed_companies(connection)
        connection.commit()

    print(f"SQLite veritabanı hazır: {DB_PATH}")


def seed_companies(connection: sqlite3.Connection) -> None:
    for ticker, company_name in SUPPORTED_COMPANIES.items():
        connection.execute(
            """
            INSERT OR IGNORE INTO companies (ticker, company_name, exchange)
            VALUES (?, ?, ?)
            """,
            (ticker, company_name, "NASDAQ"),
        )


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_average_score(sources: List[Dict[str, Any]]) -> float:
    scores = []

    for source in sources:
        score = safe_float(source.get("score"))

        if score is not None:
            scores.append(score)

    if not scores:
        return 0.0

    return round(sum(scores) / len(scores), 6)


def save_rag_result(
    query_text: str,
    result: Dict[str, Any],
    ticker: Optional[str],
    top_k: int,
    use_foundry_local: bool,
) -> int:
    """
    RAG cevabını ve kullanılan kaynakları SQLite veritabanına kaydeder.
    """
    sources = result.get("sources", [])
    answer = result.get("answer", "")

    retrieval_type = sources[0].get("retrieval_type") if sources else None
    embedding_model = sources[0].get("embedding_model") if sources else None
    avg_score = calculate_average_score(sources)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO rag_queries (
                query_text,
                ticker,
                answer,
                top_k,
                use_foundry_local,
                retrieval_type,
                embedding_model,
                source_count,
                avg_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query_text,
                ticker,
                answer,
                top_k,
                1 if use_foundry_local else 0,
                retrieval_type,
                embedding_model,
                len(sources),
                avg_score,
            ),
        )

        query_id = int(cursor.lastrowid)

        for index, source in enumerate(sources, start=1):
            connection.execute(
                """
                INSERT INTO rag_sources (
                    query_id,
                    source_rank,
                    ticker,
                    company_name,
                    filing_type,
                    filing_date,
                    section,
                    raw_section,
                    chunk_id,
                    score,
                    original_score,
                    retrieval_type,
                    embedding_model,
                    source_document_url,
                    excerpt
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    index,
                    source.get("ticker"),
                    source.get("company_name"),
                    source.get("filing_type"),
                    source.get("filing_date"),
                    source.get("section"),
                    source.get("raw_section"),
                    source.get("chunk_id"),
                    safe_float(source.get("score")),
                    safe_float(source.get("original_score")),
                    source.get("retrieval_type"),
                    source.get("embedding_model"),
                    source.get("source_document_url"),
                    source.get("excerpt"),
                ),
            )

        connection.commit()

    return query_id


def list_recent_queries(limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                query_id,
                ticker,
                query_text,
                source_count,
                avg_score,
                use_foundry_local,
                created_at
            FROM rag_queries
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_query_with_sources(query_id: int) -> Dict[str, Any]:
    with get_connection() as connection:
        query_row = connection.execute(
            """
            SELECT *
            FROM rag_queries
            WHERE query_id = ?
            """,
            (query_id,),
        ).fetchone()

        if query_row is None:
            raise ValueError(f"Query bulunamadı: {query_id}")

        source_rows = connection.execute(
            """
            SELECT *
            FROM rag_sources
            WHERE query_id = ?
            ORDER BY source_rank ASC
            """,
            (query_id,),
        ).fetchall()

    return {
        "query": dict(query_row),
        "sources": [dict(row) for row in source_rows],
    }


def print_recent_queries(limit: int = 10) -> None:
    recent_queries = list_recent_queries(limit=limit)

    if not recent_queries:
        print("Kayıtlı RAG sorgusu bulunamadı.")
        return

    for query in recent_queries:
        print(
            f"{query['query_id']} | "
            f"{query['ticker']} | "
            f"Kaynak: {query['source_count']} | "
            f"Skor: {query['avg_score']} | "
            f"Foundry Local: {query['use_foundry_local']} | "
            f"Tarih: {query['created_at']}"
        )
        print(f"Soru: {query['query_text']}")
        print("-" * 80)


def main() -> None:
    initialize_database()
    print_recent_queries(limit=5)


if __name__ == "__main__":
    main()