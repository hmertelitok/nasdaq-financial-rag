import argparse
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"

load_dotenv(PROJECT_ROOT / ".env")


def get_postgres_config() -> Dict[str, Any]:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5433")),
        "dbname": os.getenv("POSTGRES_DB", "nasdaq_financial_rag"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }


def get_connection():
    config = get_postgres_config()

    return psycopg2.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["dbname"],
        user=config["user"],
        password=config["password"],
        cursor_factory=RealDictCursor,
    )


def load_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def create_query_embedding(model: SentenceTransformer, query: str) -> List[float]:
    normalized_query = query.strip()

    if not normalized_query:
        raise ValueError("Query boş olamaz.")

    encoded_query = f"query: {normalized_query}"

    embedding = model.encode(
        encoded_query,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return [float(value) for value in embedding.tolist()]


def embedding_to_pgvector(embedding: List[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"


def semantic_search(
    query: str,
    ticker: Optional[str] = None,
    section: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    model = load_embedding_model()
    query_embedding = create_query_embedding(model, query)
    query_vector = embedding_to_pgvector(query_embedding)

    normalized_ticker = ticker.strip().upper() if ticker else None
    normalized_section = section.strip() if section else None

    conditions = ["embedding IS NOT NULL"]
    parameters: List[Any] = [query_vector]

    if normalized_ticker:
        conditions.append("ticker = %s")
        parameters.append(normalized_ticker)

    if normalized_section:
        conditions.append("section ILIKE %s")
        parameters.append(f"%{normalized_section}%")

    parameters.append(limit)

    sql = f"""
        SELECT
            id,
            filing_id,
            chunk_id,
            chunk_index,
            ticker,
            filing_type,
            filing_date,
            section,
            raw_section,
            LEFT(chunk_text, 700) AS excerpt,
            token_count,
            embedding_model,
            source_document_url,
            1 - (embedding <=> %s::vector) AS similarity
        FROM document_chunks
        WHERE {" AND ".join(conditions)}
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """

    # query_vector hem SELECT similarity hem de ORDER BY için kullanılıyor.
    # Parametre sırası:
    # 1. SELECT içindeki query_vector
    # 2. filtre parametreleri
    # 3. ORDER BY içindeki query_vector
    # 4. limit
    select_vector = query_vector
    order_vector = query_vector

    filter_parameters = parameters[1:-1]
    final_parameters = [select_vector] + filter_parameters + [order_vector, limit]

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, final_parameters)
            rows = cursor.fetchall()

    return [dict(row) for row in rows]


def print_results(query: str, results: List[Dict[str, Any]]) -> None:
    print()
    print("pgvector semantic search sonucu")
    print(f"Sorgu: {query}")
    print(f"Sonuç sayısı: {len(results)}")
    print("-" * 80)

    if not results:
        print("Sonuç bulunamadı.")
        return

    for index, result in enumerate(results, start=1):
        similarity = result.get("similarity")
        similarity_text = f"{similarity:.4f}" if similarity is not None else "N/A"

        print(f"{index}. {result.get('ticker')} | {result.get('filing_type')} | {result.get('section')}")
        print(f"   Chunk ID: {result.get('chunk_id')}")
        print(f"   Similarity: {similarity_text}")
        print(f"   Source: {result.get('source_document_url')}")
        print(f"   Excerpt: {result.get('excerpt')}")
        print("-" * 80)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PostgreSQL pgvector üzerinde semantic chunk search yapar."
    )

    parser.add_argument(
        "--query",
        required=True,
        help="Semantic search sorgusu.",
    )

    parser.add_argument(
        "--ticker",
        required=False,
        default=None,
        help="Opsiyonel şirket filtresi. Örn: AAPL, MSFT, NVDA.",
    )

    parser.add_argument(
        "--section",
        required=False,
        default=None,
        help="Opsiyonel section filtresi. Örn: Risk Factors, Business.",
    )

    parser.add_argument(
        "--limit",
        required=False,
        type=int,
        default=5,
        help="Dönecek maksimum sonuç sayısı.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    safe_limit = max(1, min(args.limit, 20))

    results = semantic_search(
        query=args.query,
        ticker=args.ticker,
        section=args.section,
        limit=safe_limit,
    )

    print_results(args.query, results)


if __name__ == "__main__":
    main()
