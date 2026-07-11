import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field


CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

from pgvector_rag_answer import DEFAULT_MODEL_ALIAS, answer_question
from pgvector_search import EMBEDDING_MODEL_NAME, semantic_search


app = FastAPI(
    title="NASDAQ Financial RAG pgvector Service",
    description=(
        "PostgreSQL + pgvector semantic search and Foundry Local "
        "source-grounded answer service."
    ),
    version="1.1.0",
)


class AskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(min_length=3)
    ticker: Optional[str] = None
    section: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20, alias="topK")
    model_alias: str = Field(default=DEFAULT_MODEL_ALIAS, alias="modelAlias")


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
        "service": "pgvector-rag-service",
        "embeddingModel": EMBEDDING_MODEL_NAME,
        "generationModel": DEFAULT_MODEL_ALIAS,
        "searchEndpoint": "/search",
        "answerEndpoint": "/ask",
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


@app.post("/ask")
def ask(request: AskRequest) -> Dict[str, Any]:
    try:
        return answer_question(
            query=request.query,
            ticker=request.ticker,
            section=request.section,
            top_k=request.top_k,
            model_alias=request.model_alias,
        )

    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail=str(exception),
        ) from exception
