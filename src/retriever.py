"""
Kullanıcı sorusuna en yakın SEC doküman chunk'larını getiren retrieval modülü.

Bu modülün görevleri:
- data/embeddings/vector_store.pkl dosyasını okumak
- Kullanıcı sorusunu vektöre çevirmek
- Vector search ile en alakalı Top-K chunk'ı bulmak
- Cevap üretiminde kullanılacak kaynak chunk listesini döndürmek

Not:
İlk MVP sürümünde TF-IDF tabanlı local vector search kullanılmaktadır.
Gelişmiş sürümde bu yapı Foundry Local embedding modeliyle değiştirilecektir.
"""

import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

from sklearn.metrics.pairwise import cosine_similarity


PROJECT_ROOT = Path(__file__).resolve().parents[1]

VECTOR_STORE_PATH = PROJECT_ROOT / "data" / "embeddings" / "vector_store.pkl"


TURKISH_QUERY_EXPANSIONS = {
    "yapay zeka": "artificial intelligence AI accelerated computing",
    "risk": "risk risks risk factors uncertainty",
    "riskler": "risk risks risk factors uncertainty",
    "tedarik zinciri": "supply chain suppliers manufacturing shortage disruption",
    "bulut": "cloud azure cloud services",
    "rekabet": "competition competitors competitive market",
    "regülasyon": "regulation regulatory legal compliance",
    "düzenleme": "regulation regulatory compliance",
    "gelir": "revenue sales income",
    "kâr": "profit income earnings",
    "kar": "profit income earnings",
    "veri merkezi": "data center datacenter",
    "pazar": "market demand customer",
    "talep": "demand customer demand",
    "maliyet": "cost expenses operating expenses",
    "operasyon": "operations operating operational",
}


def load_vector_store() -> Dict[str, Any]:
    """Local vector store dosyasını okur."""
    if not VECTOR_STORE_PATH.exists():
        raise FileNotFoundError(
            "vector_store.pkl bulunamadı. "
            "Önce src/embedder.py dosyasını çalıştırmalısın."
        )

    with open(VECTOR_STORE_PATH, "rb") as file:
        return pickle.load(file)


def expand_query(query: str) -> str:
    """
    Türkçe sorular için basit İngilizce anahtar kelime genişletmesi yapar.

    SEC 10-K raporları İngilizce olduğu için Türkçe sorularda retrieval kalitesini
    artırmak amacıyla temel finansal terimler İngilizce karşılıklarıyla desteklenir.
    """
    expanded_query = query
    lower_query = query.lower()

    for turkish_term, english_terms in TURKISH_QUERY_EXPANSIONS.items():
        if turkish_term in lower_query:
            expanded_query += " " + english_terms

    return expanded_query


def filter_chunks_by_ticker(
    chunks: List[Dict[str, Any]],
    ticker: Optional[str],
) -> List[int]:
    """Seçili ticker varsa chunk indekslerini ilgili şirkete göre filtreler."""
    if ticker is None:
        return list(range(len(chunks)))

    ticker = ticker.upper()

    return [
        index
        for index, chunk in enumerate(chunks)
        if chunk.get("ticker", "").upper() == ticker
    ]


def create_excerpt(text: str, max_length: int = 500) -> str:
    """Kaynak gösterimi için kısa metin özeti oluşturur."""
    text = " ".join(text.split())

    if len(text) <= max_length:
        return text

    return text[:max_length].strip() + "..."


def search_relevant_chunks(
    query: str,
    ticker: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Kullanıcı sorusuna en yakın Top-K chunk listesini döndürür.

    Parametreler:
    - query: Kullanıcı sorusu
    - ticker: Opsiyonel şirket kodu, örn. NVDA
    - top_k: Getirilecek kaynak chunk sayısı
    """
    vector_store = load_vector_store()

    vectorizer = vector_store["vectorizer"]
    vector_matrix = vector_store["vector_matrix"]
    chunks = vector_store["chunks"]

    candidate_indices = filter_chunks_by_ticker(chunks, ticker)

    if not candidate_indices:
        return []

    expanded_query = expand_query(query)
    query_vector = vectorizer.transform([expanded_query])

    candidate_matrix = vector_matrix[candidate_indices]
    scores = cosine_similarity(query_vector, candidate_matrix).flatten()

    ranked_results = sorted(
        zip(candidate_indices, scores),
        key=lambda item: item[1],
        reverse=True,
    )

    top_results = ranked_results[:top_k]

    retrieved_chunks = []

    for index, score in top_results:
        chunk = chunks[index]

        retrieved_chunks.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "ticker": chunk.get("ticker"),
                "company_name": chunk.get("company_name"),
                "filing_type": chunk.get("filing_type"),
                "filing_date": chunk.get("filing_date"),
                "section": chunk.get("section"),
                "chunk_index": chunk.get("chunk_index"),
                "score": round(float(score), 4),
                "source_document_url": chunk.get("source_document_url"),
                "excerpt": create_excerpt(chunk.get("text", "")),
                "text": chunk.get("text", ""),
            }
        )

    return retrieved_chunks


def print_retrieval_results(results: List[Dict[str, Any]]) -> None:
    """Retrieval sonuçlarını terminalde okunabilir şekilde gösterir."""
    if not results:
        print("İlgili chunk bulunamadı.")
        return

    for rank, result in enumerate(results, start=1):
        print("=" * 80)
        print(f"Sonuç {rank}")
        print(f"Şirket: {result['ticker']} - {result['company_name']}")
        print(f"Filing: {result['filing_type']} | Tarih: {result['filing_date']}")
        print(f"Bölüm: {result['section']}")
        print(f"Chunk ID: {result['chunk_id']}")
        print(f"Skor: {result['score']}")
        print("-" * 80)
        print(result["excerpt"])


def main() -> None:
    """Retrieval yapısını örnek bir soru ile test eder."""
    query = "NVIDIA son 10-K raporunda yapay zeka ile ilgili hangi risklerden bahsediyor?"

    results = search_relevant_chunks(
        query=query,
        ticker="NVDA",
        top_k=5,
    )

    print_retrieval_results(results)


if __name__ == "__main__":
    main()