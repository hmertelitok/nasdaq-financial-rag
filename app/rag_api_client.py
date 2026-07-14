from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import requests


API_BASE_URL = os.getenv(
    "NASDAQ_RAG_API_BASE_URL",
    "http://localhost:5094",
).rstrip("/")

DEFAULT_MODEL_ALIAS = "qwen2.5-7b"
DEFAULT_TIMEOUT_SECONDS = 360

SUPPORTED_COMPANIES: Dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}

HTTP_SESSION = requests.Session()


class RagApiError(RuntimeError):
    """ASP.NET Core RAG API çağrılarında oluşan hatalar."""


def get_default_query(ticker: Optional[str]) -> str:
    queries = {
        "AAPL": (
            "Apple'ın temel iş, tedarik zinciri, rekabet ve "
            "düzenleyici riskleri nelerdir?"
        ),
        "MSFT": (
            "Microsoft'un yapay zeka, bulut, veri merkezi ve "
            "siber güvenlik riskleri nelerdir?"
        ),
        "NVDA": (
            "NVIDIA'nın tedarik zinciri, ihracat kontrolleri ve "
            "yapay zeka talebiyle ilgili riskleri nelerdir?"
        ),
        "AMZN": (
            "Amazon'un AWS, lojistik, operasyonel maliyetler ve "
            "düzenleyici riskleri nelerdir?"
        ),
        "GOOGL": (
            "Alphabet'in yapay zeka, reklam, veri gizliliği ve "
            "düzenleyici riskleri nelerdir?"
        ),
    }

    if ticker:
        normalized_ticker = ticker.strip().upper()

        if normalized_ticker in queries:
            return queries[normalized_ticker]

    return (
        "AAPL, MSFT, NVDA, AMZN ve GOOGL şirketlerinin SEC 10-K "
        "raporlarında öne çıkan temel iş riskleri nelerdir?"
    )


def _extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        return str(
            payload.get("detail")
            or payload.get("message")
            or payload.get("title")
            or payload
        )

    return str(payload)


def check_api_health(timeout_seconds: int = 5) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/api/health"

    try:
        response = HTTP_SESSION.get(url, timeout=timeout_seconds)
    except requests.RequestException as exception:
        raise RagApiError(
            f"ASP.NET Core API bağlantısı kurulamadı: {exception}"
        ) from exception

    if not response.ok:
        raise RagApiError(
            f"API sağlık kontrolü başarısız oldu. "
            f"HTTP {response.status_code}: {_extract_error_message(response)}"
        )

    payload = response.json()

    if payload.get("status") != "healthy":
        raise RagApiError(
            f"API sağlıklı durumda değil: {payload}"
        )

    return payload


def _safe_score(value: Any) -> float:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return 0.0


def _normalize_source(source: Dict[str, Any]) -> Dict[str, Any]:
    ticker = str(source.get("ticker") or "").strip().upper()

    similarity_value = source.get("similarity")

    if similarity_value is None:
        similarity_value = source.get("score")

    similarity = _safe_score(similarity_value)

    return {
        **source,
        "ticker": ticker or "N/A",
        "company_name": (
            source.get("companyName")
            or source.get("company_name")
            or SUPPORTED_COMPANIES.get(ticker)
            or ticker
            or "N/A"
        ),
        "filing_type": (
            source.get("filingType")
            or source.get("filing_type")
            or "N/A"
        ),
        "filing_date": (
            source.get("filingDate")
            or source.get("filing_date")
            or "N/A"
        ),
        "section": source.get("section") or "N/A",
        "raw_section": (
            source.get("rawSection")
            or source.get("raw_section")
            or source.get("section")
            or "N/A"
        ),
        "chunk_id": (
            source.get("chunkId")
            or source.get("chunk_id")
            or "N/A"
        ),
        "score": similarity,
        "original_score": similarity,
        "retrieval_type": (
            source.get("retrievalType")
            or source.get("retrieval_type")
            or "pgvector-semantic"
        ),
        "embedding_model": (
            source.get("embeddingModel")
            or source.get("embedding_model")
            or "intfloat/multilingual-e5-small"
        ),
        "source_document_url": (
            source.get("sourceDocumentUrl")
            or source.get("source_document_url")
            or ""
        ),
        "excerpt": source.get("excerpt") or "",
    }

def _normalize_answer(answer: Any) -> str:
    normalized = str(answer or "Cevap üretilemedi.")

    normalized = (
        normalized
        .replace("\u200b", "")
        .replace("\ufeff", "")
        .replace("\u00a0", " ")
    )

    normalized = re.sub(
        r"\[\s*Kaynak[\s\u200b\u00a0]*(\d+)\s*\]",
        r"[Kaynak \1]",
        normalized,
        flags=re.IGNORECASE,
    )

    return normalized

def _normalize_result(
    payload: Dict[str, Any],
    requested_query: str,
    requested_ticker: Optional[str],
) -> Dict[str, Any]:
    sources = payload.get("sources") or []

    if not isinstance(sources, list):
        sources = []

    normalized_sources = [
        _normalize_source(source)
        for source in sources
        if isinstance(source, dict)
    ]

    return {
        "query": payload.get("query") or requested_query,
        "ticker": payload.get("ticker") or requested_ticker,
        "section": payload.get("section"),
        "top_k": payload.get("topK"),
        "embedding_model": payload.get("embeddingModel"),
        "generation_model": payload.get("generationModel"),
        "answer": _normalize_answer(payload.get("answer")),
        "source_count": payload.get(
            "sourceCount",
            len(normalized_sources),
        ),
        "sources": normalized_sources,
    }


def ask_company(
    query: str,
    ticker: str,
    top_k: int = 5,
    section: Optional[str] = None,
    model_alias: str = DEFAULT_MODEL_ALIAS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    normalized_query = query.strip()
    normalized_ticker = ticker.strip().upper()

    if not normalized_query:
        raise ValueError("Soru boş olamaz.")

    if normalized_ticker not in SUPPORTED_COMPANIES:
        raise ValueError(
            f"Desteklenmeyen ticker: {normalized_ticker}"
        )

    payload = {
        "query": normalized_query,
        "ticker": normalized_ticker,
        "section": section,
        "topK": max(1, min(int(top_k), 20)),
        "modelAlias": model_alias,
    }

    url = f"{API_BASE_URL}/api/rag/ask"

    try:
        response = HTTP_SESSION.post(
            url,
            json=payload,
            timeout=timeout_seconds,
        )
    except requests.Timeout as exception:
        raise RagApiError(
            "RAG API isteği zaman aşımına uğradı."
        ) from exception
    except requests.RequestException as exception:
        raise RagApiError(
            f"RAG API bağlantısı kurulamadı: {exception}"
        ) from exception

    if not response.ok:
        raise RagApiError(
            f"RAG API isteği başarısız oldu. "
            f"HTTP {response.status_code}: {_extract_error_message(response)}"
        )

    response_payload = response.json()

    if not isinstance(response_payload, dict):
        raise RagApiError(
            "RAG API beklenmeyen yanıt biçimi döndürdü."
        )

    return _normalize_result(
        payload=response_payload,
        requested_query=normalized_query,
        requested_ticker=normalized_ticker,
    )


def ask_all_companies(
    query: Optional[str] = None,
    top_k: int = 5,
    model_alias: str = DEFAULT_MODEL_ALIAS,
) -> List[Dict[str, Any]]:
    custom_query = query.strip() if query and query.strip() else None

    results: List[Dict[str, Any]] = []

    for ticker in SUPPORTED_COMPANIES:
        ticker_query = custom_query or get_default_query(ticker)

        result = ask_company(
            query=ticker_query,
            ticker=ticker,
            top_k=top_k,
            model_alias=model_alias,
        )

        results.append(result)

    return results