"""
Chunk metinleri için local vector store oluşturma modülü.

Bu modülün görevleri:
- data/chunks/filing_chunks.json dosyasını okumak
- Chunk metinlerini vektör temsiline dönüştürmek
- Vectorizer, vektör matrisi ve chunk metadata bilgilerini local olarak kaydetmek

Not:
İlk MVP sürümünde hızlı geliştirme için TF-IDF tabanlı local vector search kullanılmaktadır.
Gelişmiş sürümde bu yapı Foundry Local embedding modeliyle değiştirilecektir.
"""

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List

from sklearn.feature_extraction.text import TfidfVectorizer


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks" / "filing_chunks.json"
VECTOR_STORE_PATH = PROJECT_ROOT / "data" / "embeddings" / "vector_store.pkl"


def load_chunks() -> List[Dict[str, Any]]:
    """Chunk verilerini JSON dosyasından okur."""
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            "filing_chunks.json bulunamadı. "
            "Önce src/chunker.py dosyasını çalıştırmalısın."
        )

    with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def build_corpus(chunks: List[Dict[str, Any]]) -> List[str]:
    """
    Vector search için kullanılacak metin listesini hazırlar.

    Metadata bilgilerini de metne eklemek, arama kalitesini artırır.
    """
    corpus = []

    for chunk in chunks:
        metadata_text = (
            f"{chunk.get('ticker', '')} "
            f"{chunk.get('company_name', '')} "
            f"{chunk.get('filing_type', '')} "
            f"{chunk.get('section', '')} "
        )

        full_text = metadata_text + " " + chunk.get("text", "")
        corpus.append(full_text)

    return corpus


def create_vector_store() -> None:
    """Chunk metinlerinden local vector store oluşturur."""
    chunks = load_chunks()
    corpus = build_corpus(chunks)

    print(f"Toplam chunk sayısı: {len(chunks)}")
    print("Local vector store oluşturuluyor...")

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        max_features=50000,
        ngram_range=(1, 2)
    )

    vector_matrix = vectorizer.fit_transform(corpus)

    vector_store = {
        "vectorizer": vectorizer,
        "vector_matrix": vector_matrix,
        "chunks": chunks
    }

    VECTOR_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(VECTOR_STORE_PATH, "wb") as file:
        pickle.dump(vector_store, file)

    print(f"Vector store kaydedildi: {VECTOR_STORE_PATH}")
    print(f"Vector matrix boyutu: {vector_matrix.shape}")


def main() -> None:
    """Vector store üretim sürecini çalıştırır."""
    create_vector_store()


if __name__ == "__main__":
    main()