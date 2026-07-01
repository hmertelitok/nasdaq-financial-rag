import json
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks" / "filing_chunks.json"
VECTOR_STORE_PATH = PROJECT_ROOT / "data" / "embeddings" / "vector_store.pkl"

DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
EMBEDDING_BATCH_SIZE = 16


def load_chunks() -> List[Dict[str, Any]]:
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            "filing_chunks.json bulunamadı. Önce src/chunker.py çalıştırılmalı."
        )

    with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def build_passage_text(chunk: Dict[str, Any]) -> str:
    ticker = chunk.get("ticker", "")
    company_name = chunk.get("company_name", "")
    section = chunk.get("section", "")
    filing_type = chunk.get("filing_type", "")
    filing_date = chunk.get("filing_date", "")
    text = chunk.get("text", "")

    passage = (
        f"Ticker: {ticker}. "
        f"Company: {company_name}. "
        f"Filing: {filing_type}. "
        f"Filing date: {filing_date}. "
        f"Section: {section}. "
        f"Content: {text}"
    )

    return f"passage: {passage}"


def create_embeddings(
    chunks: List[Dict[str, Any]],
    model_name: str,
) -> np.ndarray:
    model = SentenceTransformer(model_name)
    passages = [build_passage_text(chunk) for chunk in chunks]

    embeddings = model.encode(
        passages,
        batch_size=EMBEDDING_BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return embeddings.astype(np.float32)


def save_vector_store(
    chunks: List[Dict[str, Any]],
    embeddings: np.ndarray,
    model_name: str,
) -> None:
    VECTOR_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    vector_store = {
        "retrieval_type": "semantic_embedding",
        "embedding_provider": "sentence-transformers",
        "embedding_model": model_name,
        "embedding_created_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_shape": embeddings.shape,
        "chunks": chunks,
        "embeddings": embeddings,
    }

    with open(VECTOR_STORE_PATH, "wb") as file:
        pickle.dump(vector_store, file)

    print(f"Vector store kaydedildi: {VECTOR_STORE_PATH}")
    print(f"Embedding matrix boyutu: {embeddings.shape}")
    print(f"Embedding modeli: {model_name}")


def main() -> None:
    model_name = os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_EMBEDDING_MODEL)

    chunks = load_chunks()

    print(f"Toplam chunk sayısı: {len(chunks)}")
    print(f"Semantic embedding modeli yükleniyor: {model_name}")
    print("Embedding üretimi başlıyor...")

    embeddings = create_embeddings(
        chunks=chunks,
        model_name=model_name,
    )

    save_vector_store(
        chunks=chunks,
        embeddings=embeddings,
        model_name=model_name,
    )


if __name__ == "__main__":
    main()