import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VECTOR_STORE_PATH = PROJECT_ROOT / "data" / "embeddings" / "vector_store.pkl"

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


def load_vector_store() -> Any:
    if not VECTOR_STORE_PATH.exists():
        raise FileNotFoundError(f"Vector store bulunamadı: {VECTOR_STORE_PATH}")

    with VECTOR_STORE_PATH.open("rb") as file:
        return pickle.load(file)


def first_value(record: Dict[str, Any], keys: Sequence[str]) -> Optional[Any]:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_embedding(embedding: Any) -> Optional[List[float]]:
    if embedding is None:
        return None

    if isinstance(embedding, np.ndarray):
        embedding = embedding.tolist()

    if isinstance(embedding, tuple):
        embedding = list(embedding)

    if not isinstance(embedding, list):
        return None

    if not embedding:
        return None

    return [float(value) for value in embedding]


def embedding_to_pgvector(embedding: Optional[List[float]]) -> Optional[str]:
    if embedding is None:
        return None

    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"


def as_dict_chunk(chunk: Any) -> Dict[str, Any]:
    if isinstance(chunk, dict):
        return chunk

    return {
        "text": str(chunk),
    }


def extract_chunks_and_embeddings(vector_store: Any) -> Tuple[List[Dict[str, Any]], Optional[Any]]:
    if isinstance(vector_store, dict):
        chunks = None
        for key in ("chunks", "documents", "docs", "items", "records"):
            if key in vector_store and vector_store[key] is not None:
                chunks = vector_store[key]
                break

        embeddings = None
        for key in ("embeddings", "embedding_matrix", "vectors"):
            if key in vector_store and vector_store[key] is not None:
                embeddings = vector_store[key]
                break

        if chunks is None:
            raise ValueError(
                "vector_store.pkl içinde chunks/documents/docs/items/records alanı bulunamadı."
            )

        if isinstance(chunks, np.ndarray):
            chunks = chunks.tolist()

        return [as_dict_chunk(chunk) for chunk in chunks], embeddings

    if isinstance(vector_store, list):
        return [as_dict_chunk(chunk) for chunk in vector_store], None

    raise ValueError(f"Desteklenmeyen vector_store formatı: {type(vector_store)}")


def get_embedding_for_chunk(
    chunk: Dict[str, Any],
    embeddings: Optional[Any],
    index: int,
) -> Optional[List[float]]:
    chunk_embedding = first_value(chunk, ["embedding", "vector", "embedding_vector"])

    if chunk_embedding is not None:
        return normalize_embedding(chunk_embedding)

    if embeddings is None:
        return None

    if isinstance(embeddings, np.ndarray):
        if index >= len(embeddings):
            return None
        return normalize_embedding(embeddings[index])

    if isinstance(embeddings, list):
        if index >= len(embeddings):
            return None
        return normalize_embedding(embeddings[index])

    return None


def normalize_chunk(
    chunk: Dict[str, Any],
    embedding: Optional[List[float]],
    index: int,
) -> Dict[str, Any]:
    text = first_value(chunk, ["text", "content", "chunk_text", "page_content"])

    ticker = first_value(chunk, ["ticker", "symbol", "company_ticker"])
    company_name = first_value(chunk, ["company_name", "company", "name"])
    filing_type = first_value(chunk, ["filing_type", "form", "form_type", "type"]) or "10-K"
    filing_date = first_value(chunk, ["filing_date", "filed_at", "filed_date", "report_date", "date"])
    section = first_value(chunk, ["section", "section_label", "clean_section"])
    raw_section = first_value(chunk, ["raw_section", "section_raw", "original_section"])
    source_document_url = first_value(
        chunk,
        ["source_document_url", "source_url", "document_url", "filing_url", "url"],
    )

    local_path = first_value(chunk, ["local_path", "file_path", "source_path", "raw_path"])
    if not ticker and local_path:
        filename = Path(str(local_path)).name
        if "_" in filename:
            ticker = filename.split("_")[0].upper()

    normalized_ticker = str(ticker).strip().upper() if ticker else None
    normalized_filing_type = str(filing_type).strip().upper() if filing_type else "10-K"

    chunk_id = first_value(chunk, ["chunk_id", "id", "document_chunk_id"])
    if not chunk_id:
        chunk_id = f"{normalized_ticker or 'UNKNOWN'}_{normalized_filing_type}_{index:05d}"

    return {
        "chunk_id": str(chunk_id),
        "chunk_index": int(first_value(chunk, ["chunk_index", "index", "order"]) or index),
        "ticker": normalized_ticker,
        "company_name": str(company_name).strip() if company_name else None,
        "filing_type": normalized_filing_type,
        "filing_date": str(filing_date).strip() if filing_date else None,
        "section": str(section).strip() if section else None,
        "raw_section": str(raw_section).strip() if raw_section else None,
        "text": str(text).strip() if text else "",
        "chunk_text": str(text).strip() if text else "",
        "content": str(text).strip() if text else "",
        "token_count": len(str(text).split()) if text else 0,
        "source_document_url": str(source_document_url).strip() if source_document_url else None,
        "embedding": embedding_to_pgvector(embedding),
        "embedding_model": "intfloat/multilingual-e5-small",
    }


def get_table_columns(cursor, table_name: str) -> List[str]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position;
        """,
        (table_name,),
    )

    return [row["column_name"] for row in cursor.fetchall()]


def resolve_filing_id(cursor, ticker: Optional[str], filing_type: Optional[str]) -> Optional[int]:
    if not ticker:
        return None

    cursor.execute(
        """
        SELECT id
        FROM filings
        WHERE ticker = %s
          AND filing_type = COALESCE(%s, filing_type)
        ORDER BY filing_date DESC NULLS LAST, id DESC
        LIMIT 1;
        """,
        (ticker, filing_type),
    )

    result = cursor.fetchone()
    return int(result["id"]) if result else None


def existing_chunk_id(cursor, chunk_id: str) -> Optional[int]:
    cursor.execute(
        """
        SELECT id
        FROM document_chunks
        WHERE chunk_id = %s
        LIMIT 1;
        """,
        (chunk_id,),
    )

    result = cursor.fetchone()
    return int(result["id"]) if result else None


def insert_chunk(cursor, columns: List[str], values: Dict[str, Any]) -> None:
    insert_columns = [column for column in columns if column in values and column != "id"]

    placeholders = ["%s" for _ in insert_columns]
    sql = f"""
        INSERT INTO document_chunks ({", ".join(insert_columns)})
        VALUES ({", ".join(placeholders)});
    """

    cursor.execute(sql, [values[column] for column in insert_columns])


def update_chunk(cursor, columns: List[str], values: Dict[str, Any], row_id: int) -> None:
    update_columns = [
        column
        for column in columns
        if column in values and column not in ("id", "chunk_id")
    ]

    assignments = [f"{column} = %s" for column in update_columns]

    sql = f"""
        UPDATE document_chunks
        SET {", ".join(assignments)}
        WHERE id = %s;
    """

    cursor.execute(sql, [values[column] for column in update_columns] + [row_id])


def main() -> None:
    vector_store = load_vector_store()
    chunks, embeddings = extract_chunks_and_embeddings(vector_store)

    inserted = 0
    updated = 0
    skipped = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            table_columns = get_table_columns(cursor, "document_chunks")

            if "chunk_id" not in table_columns:
                raise ValueError("document_chunks tablosunda chunk_id kolonu bulunamadı.")

            for index, chunk in enumerate(chunks):
                embedding = get_embedding_for_chunk(chunk, embeddings, index)
                normalized = normalize_chunk(chunk, embedding, index)

                if not normalized["ticker"]:
                    skipped += 1
                    continue

                if not normalized["text"]:
                    skipped += 1
                    continue

                if "filing_id" in table_columns:
                    normalized["filing_id"] = resolve_filing_id(
                        cursor,
                        normalized["ticker"],
                        normalized["filing_type"],
                    )

                existing_id = existing_chunk_id(cursor, normalized["chunk_id"])

                if existing_id:
                    update_chunk(cursor, table_columns, normalized, existing_id)
                    updated += 1
                else:
                    insert_chunk(cursor, table_columns, normalized)
                    inserted += 1

        connection.commit()

    print("PostgreSQL document chunk import tamamlandı")
    print(f"Vector store: {VECTOR_STORE_PATH}")
    print(f"Toplam chunk: {len(chunks)}")
    print(f"Eklenen kayıt: {inserted}")
    print(f"Güncellenen kayıt: {updated}")
    print(f"Atlanan kayıt: {skipped}")


if __name__ == "__main__":
    main()

