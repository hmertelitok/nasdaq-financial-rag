import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query


CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

from pgvector_search import EMBEDDING_MODEL_NAME, semantic_search


app = FastAPI(
    title="NASDAQ Financial RAG pgvector Search Service",
    description="Local semantic search service for PostgreSQL + pgvector document chunks.",
    version="1.0.0",
)


def to_json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    return value


def serialize_result(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: to_json_safe(value)
        for key, value in row.items()
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "pgvector-search-service",
        "embeddingModel": EMBEDDING_MODEL_NAME,
    }


@app.get("/search")
def search(
    query: str = Query(..., min_length=3),
    ticker: Optional[str] = Query(default=None),
    section: Optional[str] = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
) -> Dict[str, Any]:
    try:
        results = semantic_search(
            query=query,
            ticker=ticker,
            section=section,
            limit=limit,
        )

        return {
            "query": query,
            "ticker": ticker.strip().upper() if ticker else None,
            "section": section,
            "limit": limit,
            "embeddingModel": EMBEDDING_MODEL_NAME,
            "resultCount": len(results),
            "results": [serialize_result(result) for result in results],
        }

    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail=str(exception),
        ) from exception
