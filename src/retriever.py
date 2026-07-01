import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from sklearn.metrics.pairwise import cosine_similarity


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VECTOR_STORE_PATH = PROJECT_ROOT / "data" / "embeddings" / "vector_store.pkl"


TURKISH_QUERY_EXPANSIONS = {
    "yapay zeka": "artificial intelligence AI accelerated computing generative AI data center GPU GPUs",
    "risk": "risk risks risk factors uncertainty adverse impact adversely affect may adversely could harm",
    "riskler": "risk risks risk factors uncertainty adverse impact adversely affect may adversely could harm",
    "tehdit": "risk risks threat uncertainty adverse impact",
    "belirsizlik": "uncertainty uncertain risk risks",
    "tedarik zinciri": "supply chain suppliers manufacturing shortage disruption supply constraints",
    "bulut": "cloud azure cloud services hyperscalers",
    "rekabet": "competition competitors competitive market",
    "regülasyon": "regulation regulatory legal compliance export controls restrictions",
    "düzenleme": "regulation regulatory compliance export controls restrictions",
    "ihracat": "export controls restrictions regulation regulatory",
    "gelir": "revenue sales income net sales",
    "kâr": "profit income earnings net income",
    "kar": "profit income earnings net income",
    "veri merkezi": "data center datacenter accelerated computing",
    "pazar": "market demand customer",
    "talep": "demand customer demand fluctuations",
    "maliyet": "cost expenses operating expenses",
    "operasyon": "operations operating operational results of operations",
}


RISK_QUERY_TERMS = [
    "risk",
    "riskler",
    "tehdit",
    "belirsizlik",
    "zarar",
    "regülasyon",
    "düzenleme",
    "ihracat",
]

AI_QUERY_TERMS = [
    "yapay zeka",
    "ai",
    "artificial intelligence",
    "gpu",
    "data center",
    "veri merkezi",
    "accelerated computing",
]

RISK_SIGNALS = [
    "risk",
    "risks",
    "risk factor",
    "risk factors",
    "adversely affect",
    "adverse impact",
    "negatively impact",
    "uncertainty",
    "uncertain",
    "subject to",
    "could harm",
    "could adversely",
    "may adversely",
    "export controls",
    "export control",
    "restrictions",
    "supply constraints",
    "supply constraint",
    "demand fluctuations",
    "macroeconomic",
    "geopolitical",
    "competition",
    "competitive",
    "regulatory",
    "regulation",
]

AI_SIGNALS = [
    "artificial intelligence",
    "generative ai",
    "accelerated computing",
    "data center",
    "datacenter",
    "gpu",
    "gpus",
    "hyperscaler",
    "hyperscalers",
    "blackwell",
    "nvlink",
    "hpc",
]

LOW_VALUE_TERMS = [
    "available information",
    "investor relations website",
    "annual reports on form 10-k",
    "quarterly reports on form 10-q",
    "current reports on form 8-k",
    "public conference calls",
    "webcasts",
]


def load_vector_store() -> Dict[str, Any]:
    if not VECTOR_STORE_PATH.exists():
        raise FileNotFoundError(
            "vector_store.pkl bulunamadı. Önce src/embedder.py dosyasını çalıştırmalısın."
        )

    with open(VECTOR_STORE_PATH, "rb") as file:
        return pickle.load(file)


def expand_query(query: str) -> str:
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
    if ticker is None:
        return list(range(len(chunks)))

    ticker = ticker.upper()

    return [
        index
        for index, chunk in enumerate(chunks)
        if chunk.get("ticker", "").upper() == ticker
    ]


def create_excerpt(text: str, max_length: int = 500) -> str:
    text = " ".join(text.split())

    if len(text) <= max_length:
        return text

    return text[:max_length].strip() + "..."


def contains_ai_term(text: str) -> bool:
    return (
        "artificial intelligence" in text
        or "generative ai" in text
        or "accelerated computing" in text
        or "data center" in text
        or "datacenter" in text
        or "gpu" in text
        or "gpus" in text
        or re.search(r"\bai\b", text) is not None
    )


def calculate_adjusted_score(
    query: str,
    chunk: Dict[str, Any],
    original_score: float,
) -> float:
    lower_query = query.lower()
    section = chunk.get("section", "")
    text = chunk.get("text", "").lower()

    adjusted_score = float(original_score)

    is_risk_query = any(term in lower_query for term in RISK_QUERY_TERMS)
    is_ai_query = any(term in lower_query for term in AI_QUERY_TERMS)

    has_risk_signal = any(signal in text for signal in RISK_SIGNALS)
    has_ai_signal = contains_ai_term(text) or any(signal in text for signal in AI_SIGNALS)
    is_low_value = any(term in text for term in LOW_VALUE_TERMS)

    if is_risk_query:
        if section == "Risk Factors":
            adjusted_score *= 1.90

        if has_risk_signal:
            adjusted_score *= 1.75
        else:
            adjusted_score *= 0.35

    if is_ai_query:
        if has_ai_signal:
            adjusted_score *= 1.25
        else:
            adjusted_score *= 0.75

    if is_risk_query and is_ai_query:
        if has_risk_signal and has_ai_signal:
            adjusted_score *= 1.60

        if has_ai_signal and not has_risk_signal:
            adjusted_score *= 0.55

    if section == "Business" and not is_risk_query:
        adjusted_score *= 1.05

    if section == "Business" and is_risk_query and not has_risk_signal:
        adjusted_score *= 0.50

    if section == "Unknown" and is_risk_query and not has_risk_signal:
        adjusted_score *= 0.60

    if is_low_value:
        adjusted_score *= 0.30

    return adjusted_score


def search_relevant_chunks(
    query: str,
    ticker: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
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

    boosted_results = []

    for candidate_index, score in zip(candidate_indices, scores):
        chunk = chunks[candidate_index]
        adjusted_score = calculate_adjusted_score(
            query=query,
            chunk=chunk,
            original_score=float(score),
        )

        boosted_results.append(
            {
                "index": candidate_index,
                "score": adjusted_score,
                "original_score": float(score),
            }
        )

    ranked_results = sorted(
        boosted_results,
        key=lambda item: item["score"],
        reverse=True,
    )

    top_results = ranked_results[:top_k]
    retrieved_chunks = []

    for result in top_results:
        chunk = chunks[result["index"]]

        retrieved_chunks.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "ticker": chunk.get("ticker"),
                "company_name": chunk.get("company_name"),
                "filing_type": chunk.get("filing_type"),
                "filing_date": chunk.get("filing_date"),
                "section": chunk.get("section"),
                "chunk_index": chunk.get("chunk_index"),
                "score": round(float(result["score"]), 4),
                "original_score": round(float(result["original_score"]), 4),
                "source_document_url": chunk.get("source_document_url"),
                "excerpt": create_excerpt(chunk.get("text", "")),
                "text": chunk.get("text", ""),
            }
        )

    return retrieved_chunks


def print_retrieval_results(results: List[Dict[str, Any]]) -> None:
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
        print(f"Ham Skor: {result['original_score']}")
        print("-" * 80)
        print(result["excerpt"])


def main() -> None:
    query = "NVIDIA son 10-K raporunda yapay zeka ile ilgili hangi risklerden bahsediyor?"

    results = search_relevant_chunks(
        query=query,
        ticker="NVDA",
        top_k=5,
    )

    print_retrieval_results(results)


if __name__ == "__main__":
    main()