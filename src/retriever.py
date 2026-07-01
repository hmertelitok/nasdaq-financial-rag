import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from section_utils import polish_section_label


PROJECT_ROOT = Path(__file__).resolve().parents[1]

VECTOR_STORE_PATH = PROJECT_ROOT / "data" / "embeddings" / "vector_store.pkl"

TOP_CANDIDATE_POOL_SIZE = 35
EXCERPT_CHAR_LIMIT = 500

_MODEL_CACHE = {}


TURKISH_QUERY_EXPANSIONS = {
    "yapay zeka": [
        "artificial intelligence",
        "AI",
        "machine learning",
        "accelerated computing",
        "generative AI",
        "AI infrastructure",
    ],
    "bulut": [
        "cloud",
        "cloud services",
        "cloud infrastructure",
        "Azure",
        "AWS",
        "Google Cloud",
    ],
    "veri merkezi": [
        "data center",
        "datacenter",
        "infrastructure",
        "capacity",
        "compute capacity",
    ],
    "tedarik zinciri": [
        "supply chain",
        "supplier",
        "suppliers",
        "manufacturing",
        "inventory",
        "purchase obligations",
        "non-cancellable",
        "non-returnable",
    ],
    "regülasyon": [
        "regulation",
        "regulatory",
        "compliance",
        "legal proceedings",
        "antitrust",
        "privacy",
        "data protection",
    ],
    "düzenleyici": [
        "regulatory",
        "regulation",
        "compliance",
        "legal",
        "privacy",
        "antitrust",
    ],
    "rekabet": [
        "competition",
        "competitive",
        "competitors",
        "market share",
        "pricing pressure",
    ],
    "çin": [
        "China",
        "Chinese",
        "export controls",
        "restrictions",
        "geopolitical",
    ],
    "ihracat": [
        "export controls",
        "export restrictions",
        "trade restrictions",
        "government restrictions",
    ],
    "gizlilik": [
        "privacy",
        "data privacy",
        "data protection",
        "security",
        "cybersecurity",
    ],
    "siber güvenlik": [
        "cybersecurity",
        "security",
        "data security",
        "security incident",
    ],
    "lojistik": [
        "logistics",
        "fulfillment",
        "transportation",
        "delivery",
        "operations",
    ],
    "reklam": [
        "advertising",
        "ads",
        "search advertising",
        "YouTube",
    ],
    "antitröst": [
        "antitrust",
        "competition law",
        "legal proceedings",
        "regulatory scrutiny",
    ],
}


COMPANY_FOCUS_TERMS = {
    "AAPL": [
        "iphone",
        "ipad",
        "mac",
        "wearables",
        "services",
        "app store",
        "supply",
        "supplier",
        "manufacturing",
        "china",
        "privacy",
        "competition",
        "product",
    ],
    "MSFT": [
        "azure",
        "cloud",
        "artificial intelligence",
        "ai",
        "data center",
        "datacenter",
        "cybersecurity",
        "security",
        "privacy",
        "regulatory",
        "competition",
    ],
    "NVDA": [
        "artificial intelligence",
        "accelerated computing",
        "gpu",
        "data center",
        "datacenter",
        "blackwell",
        "export controls",
        "china",
        "supply",
        "purchase obligations",
        "competition",
    ],
    "AMZN": [
        "aws",
        "cloud",
        "fulfillment",
        "logistics",
        "transportation",
        "delivery",
        "labor",
        "inventory",
        "supply",
        "regulatory",
        "competition",
        "privacy",
    ],
    "GOOGL": [
        "advertising",
        "ads",
        "search",
        "youtube",
        "artificial intelligence",
        "ai",
        "cloud",
        "privacy",
        "data protection",
        "antitrust",
        "competition",
        "legal proceedings",
    ],
}


RISK_QUERY_TERMS = [
    "risk",
    "risks",
    "risk factors",
    "adversely affect",
    "material adverse",
    "uncertainty",
    "regulatory",
    "competition",
    "supply chain",
    "restrictions",
    "litigation",
]


RISK_SIGNALS = [
    "risk",
    "risks",
    "risk factors",
    "adversely affect",
    "adverse effect",
    "material adverse",
    "could adversely",
    "may adversely",
    "uncertainty",
    "uncertain",
    "regulatory",
    "regulation",
    "litigation",
    "legal proceedings",
    "competition",
    "competitive",
    "supply chain",
    "export controls",
    "restrictions",
    "privacy",
    "security",
]


AI_SIGNALS = [
    "artificial intelligence",
    "modern ai",
    "generative ai",
    "machine learning",
    "accelerated computing",
    "data center",
    "datacenter",
    "cloud",
    "gpu",
    "blackwell",
    "azure",
    "aws",
]


LOW_VALUE_TERMS = [
    "table of contents",
    "signature",
    "exhibit index",
    "part iv",
    "forward-looking statements",
]


LOW_RELEVANCE_PATTERNS = [
    "executive officers",
    "chief executive officer",
    "chief financial officer",
    "principal accounting officer",
    "stock-based compensation",
    "restricted stock units",
    "derivative instruments",
    "investment securities",
    "income tax contingencies",
    "uncertain income tax positions",
    "fair value on the date of grant",
    "as discussed in part i, item 1a",
    "under the heading risk factors",
]


STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "that",
    "this",
    "are",
    "was",
    "were",
    "has",
    "have",
    "had",
    "its",
    "our",
    "their",
    "about",
    "which",
    "what",
    "how",
    "hangi",
    "konular",
    "öne",
    "çıkıyor",
    "ilgili",
    "son",
    "raporunda",
    "riskleri",
    "risklerle",
    "şirket",
    "şirketinin",
}


def load_vector_store() -> Dict[str, Any]:
    if not VECTOR_STORE_PATH.exists():
        raise FileNotFoundError(
            "vector_store.pkl bulunamadı. Önce src/embedder.py çalıştırılmalı."
        )

    with open(VECTOR_STORE_PATH, "rb") as file:
        vector_store = pickle.load(file)

    if "embeddings" not in vector_store or "chunks" not in vector_store:
        raise ValueError(
            "Vector store semantic embedding formatında değil. src/embedder.py dosyasını yeniden çalıştır."
        )

    return vector_store


def get_embedding_model(model_name: str) -> SentenceTransformer:
    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)

    return _MODEL_CACHE[model_name]


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("ı", "i")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def expand_query(query: str) -> str:
    normalized_query = normalize_text(query)
    expanded_terms = [query]

    for turkish_term, english_terms in TURKISH_QUERY_EXPANSIONS.items():
        if normalize_text(turkish_term) in normalized_query:
            expanded_terms.extend(english_terms)

    if any(term in normalized_query for term in ["risk", "riskler", "tehlike", "olumsuz"]):
        expanded_terms.extend(RISK_QUERY_TERMS)

    return " ".join(expanded_terms)


def embed_query(query: str, model_name: str) -> np.ndarray:
    model = get_embedding_model(model_name)
    expanded_query = expand_query(query)

    query_embedding = model.encode(
        [f"query: {expanded_query}"],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )[0]

    return query_embedding.astype(np.float32)


def filter_indices_by_ticker(
    chunks: List[Dict[str, Any]],
    ticker: Optional[str],
) -> List[int]:
    if ticker is None:
        return list(range(len(chunks)))

    selected_ticker = ticker.upper()

    return [
        index
        for index, chunk in enumerate(chunks)
        if chunk.get("ticker", "").upper() == selected_ticker
    ]


def contains_term(text: str, term: str) -> bool:
    normalized_text = normalize_text(text)
    normalized_term = normalize_text(term)

    if len(normalized_term) <= 3:
        return re.search(rf"\b{re.escape(normalized_term)}\b", normalized_text) is not None

    return normalized_term in normalized_text


def contains_any(text: str, terms: List[str]) -> bool:
    return any(contains_term(text, term) for term in terms)


def count_matching_terms(text: str, terms: List[str]) -> int:
    unique_terms = list(dict.fromkeys(terms))
    return sum(1 for term in unique_terms if contains_term(text, term))


def extract_keyword_terms(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", text)
    terms = []

    for token in tokens:
        normalized_token = normalize_text(token)

        if len(normalized_token) < 4:
            continue

        if normalized_token in STOPWORDS:
            continue

        terms.append(normalized_token)

    return list(dict.fromkeys(terms))


def get_query_terms(query: str) -> List[str]:
    expanded_query = expand_query(query)
    terms = extract_keyword_terms(expanded_query)

    phrase_terms = []

    for turkish_term, english_terms in TURKISH_QUERY_EXPANSIONS.items():
        if normalize_text(turkish_term) in normalize_text(query):
            phrase_terms.extend(english_terms)

    if any(term in normalize_text(query) for term in ["risk", "riskler", "olumsuz"]):
        phrase_terms.extend(RISK_QUERY_TERMS)

    all_terms = phrase_terms + terms

    return list(dict.fromkeys(all_terms))


def get_focus_terms(query: str, ticker: Optional[str]) -> List[str]:
    terms = []

    if ticker:
        terms.extend(COMPANY_FOCUS_TERMS.get(ticker.upper(), []))

    normalized_query = normalize_text(query)

    for turkish_term, english_terms in TURKISH_QUERY_EXPANSIONS.items():
        if normalize_text(turkish_term) in normalized_query:
            terms.extend(english_terms)

    if any(term in normalized_query for term in ["risk", "riskler", "olumsuz"]):
        terms.extend(RISK_QUERY_TERMS)

    return list(dict.fromkeys(terms))


def calculate_coverage_score(text: str, terms: List[str], denominator_limit: int = 14) -> float:
    if not terms:
        return 0.0

    denominator = max(min(len(terms), denominator_limit), 1)
    matched = count_matching_terms(text, terms)

    return min(matched / denominator, 1.0)


def calculate_penalty(
    query: str,
    chunk: Dict[str, Any],
    focus_score: float,
    coverage_score: float,
) -> float:
    text = chunk.get("text", "")
    section = chunk.get("section", "Unknown")
    normalized_query = normalize_text(query)

    penalty = 0.0

    if contains_any(text, LOW_VALUE_TERMS):
        penalty += 0.18

    if contains_any(text, LOW_RELEVANCE_PATTERNS):
        penalty += 0.12

    legal_query = contains_any(
        normalized_query,
        [
            "legal",
            "litigation",
            "regulation",
            "regulatory",
            "antitrust",
            "privacy",
            "gizlilik",
            "regülasyon",
            "düzenleyici",
            "vergi",
            "tax",
        ],
    )

    market_risk_query = contains_any(
        normalized_query,
        [
            "interest rate",
            "foreign exchange",
            "currency",
            "inflation",
            "tariff",
            "faiz",
            "enflasyon",
            "makroekonomik",
        ],
    )

    if section == "Legal Proceedings" and not legal_query:
        penalty += 0.10

    if section == "Market Risk" and not market_risk_query and focus_score < 0.25:
        penalty += 0.08

    if section == "Financial Statements" and focus_score < 0.25:
        penalty += 0.08

    if section in {"Executive Compensation", "Principal Accountant Fees"}:
        penalty += 0.18

    if section == "Properties" and focus_score < 0.25:
        penalty += 0.10

    if focus_score == 0 and coverage_score < 0.15:
        penalty += 0.08

    return penalty


def calculate_section_bonus(
    query: str,
    chunk: Dict[str, Any],
    focus_score: float,
) -> float:
    section = chunk.get("section", "Unknown")
    normalized_query = normalize_text(query)

    risk_query = contains_any(
        normalized_query,
        [
            "risk",
            "riskler",
            "olumsuz",
            "regülasyon",
            "düzenleyici",
            "rekabet",
            "tedarik",
            "gizlilik",
            "antitröst",
        ],
    )

    legal_query = contains_any(
        normalized_query,
        [
            "legal",
            "litigation",
            "regulation",
            "regulatory",
            "antitrust",
            "privacy",
            "regülasyon",
            "düzenleyici",
            "gizlilik",
            "antitröst",
        ],
    )

    market_risk_query = contains_any(
        normalized_query,
        [
            "interest rate",
            "foreign exchange",
            "currency",
            "inflation",
            "tariff",
            "faiz",
            "enflasyon",
            "makroekonomik",
        ],
    )

    if section == "Risk Factors" and risk_query:
        return 0.10

    if section == "Cybersecurity" and contains_any(
        normalized_query,
        ["cybersecurity", "security", "siber güvenlik", "gizlilik", "privacy"],
    ):
        return 0.08

    if section == "Business" and focus_score >= 0.20:
        return 0.06

    if section == "Legal Proceedings" and legal_query:
        return 0.06

    if section == "Market Risk" and market_risk_query:
        return 0.06

    if section == "Unknown":
        return -0.12

    return 0.0


def calculate_adjusted_score(
    query: str,
    chunk: Dict[str, Any],
    semantic_score: float,
) -> float:
    ticker = chunk.get("ticker")
    text = chunk.get("text", "")

    query_terms = get_query_terms(query)
    focus_terms = get_focus_terms(query, ticker)

    coverage_score = calculate_coverage_score(text, query_terms)
    focus_score = calculate_coverage_score(text, focus_terms)
    risk_signal_score = calculate_coverage_score(text, RISK_SIGNALS, denominator_limit=8)
    ai_signal_score = calculate_coverage_score(text, AI_SIGNALS, denominator_limit=7)

    section_bonus = calculate_section_bonus(query, chunk, focus_score)
    penalty = calculate_penalty(query, chunk, focus_score, coverage_score)

    adjusted_score = (
        float(semantic_score)
        + (0.18 * coverage_score)
        + (0.22 * focus_score)
        + (0.10 * risk_signal_score)
        + (0.07 * ai_signal_score)
        + section_bonus
        - penalty
    )

    return round(max(adjusted_score, 0.0), 4)


def create_excerpt(text: str, query: str, max_chars: int = EXCERPT_CHAR_LIMIT) -> str:
    clean_text = " ".join(text.split())

    if len(clean_text) <= max_chars:
        return clean_text

    query_terms = get_query_terms(query)
    focus_terms = get_focus_terms(query, None)
    terms = list(dict.fromkeys(query_terms + focus_terms))

    lower_text = clean_text.lower()
    positions = []

    for term in terms:
        normalized_term = term.lower()

        if len(normalized_term) < 4:
            continue

        position = lower_text.find(normalized_term)

        if position != -1:
            positions.append(position)

    if positions:
        start = max(min(positions) - 150, 0)
        end = min(start + max_chars, len(clean_text))
        return clean_text[start:end].strip() + "..."

    return clean_text[:max_chars].strip() + "..."


def diversify_results(
    candidates: List[Dict[str, Any]],
    top_k: int,
) -> List[Dict[str, Any]]:
    selected = []
    selected_ids = set()
    section_counts = {}

    for candidate in candidates:
        section = candidate.get("section", "Unknown")
        current_count = section_counts.get(section, 0)

        section_limit = 3

        if section == "Risk Factors":
            section_limit = 3

        if section == "Business":
            section_limit = 3

        if section in {"Legal Proceedings", "Market Risk", "Cybersecurity"}:
            section_limit = 2

        if section in {"Properties", "Principal Accountant Fees", "Executive Compensation"}:
            section_limit = 1

        if section == "Unknown":
            section_limit = 1

        if current_count < section_limit:
            selected.append(candidate)
            selected_ids.add(candidate["chunk_id"])
            section_counts[section] = current_count + 1

        if len(selected) >= top_k:
            return selected

    for candidate in candidates:
        if candidate["chunk_id"] not in selected_ids:
            selected.append(candidate)
            selected_ids.add(candidate["chunk_id"])

        if len(selected) >= top_k:
            break

    return selected


def search_relevant_chunks(
    query: str,
    ticker: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    vector_store = load_vector_store()

    chunks = vector_store["chunks"]
    embeddings = vector_store["embeddings"]
    model_name = vector_store.get("embedding_model", "intfloat/multilingual-e5-small")

    selected_indices = filter_indices_by_ticker(chunks, ticker)

    if not selected_indices:
        return []

    query_embedding = embed_query(query, model_name)
    selected_embeddings = embeddings[selected_indices]

    semantic_scores = selected_embeddings @ query_embedding

    candidate_rows = []

    for local_index, global_index in enumerate(selected_indices):
        raw_chunk = chunks[global_index]
        chunk = dict(raw_chunk)

        raw_section = chunk.get("section", "Unknown")
        polished_section = polish_section_label(chunk)

        chunk["raw_section"] = raw_section
        chunk["section"] = polished_section

        original_score = float(semantic_scores[local_index])
        adjusted_score = calculate_adjusted_score(query, chunk, original_score)

        result = dict(chunk)
        result["original_score"] = round(original_score, 4)
        result["score"] = adjusted_score
        result["retrieval_type"] = "semantic_hybrid_rerank"
        result["embedding_model"] = model_name
        result["excerpt"] = create_excerpt(chunk.get("text", ""), query)

        candidate_rows.append(result)

    candidate_rows = sorted(
        candidate_rows,
        key=lambda item: item["score"],
        reverse=True,
    )

    candidate_rows = candidate_rows[: max(TOP_CANDIDATE_POOL_SIZE, top_k)]
    selected_results = diversify_results(candidate_rows, top_k)

    return selected_results


def print_retrieval_results(results: List[Dict[str, Any]]) -> None:
    if not results:
        print("Sonuç bulunamadı.")
        return

    for index, result in enumerate(results, start=1):
        print("=" * 80)
        print(f"{index}. {result.get('ticker')} - {result.get('company_name')}")
        print(f"Section: {result.get('section')}")
        print(f"Raw Section: {result.get('raw_section', result.get('section'))}")
        print(f"Chunk ID: {result.get('chunk_id')}")
        print(f"Semantic Score: {result.get('original_score')}")
        print(f"Hybrid Score: {result.get('score')}")
        print(f"Retrieval Type: {result.get('retrieval_type')}")
        print(f"Embedding Model: {result.get('embedding_model')}")
        print(f"URL: {result.get('source_document_url')}")
        print("-" * 80)
        print(result.get("excerpt"))
        print("=" * 80)


def main() -> None:
    query = "NVIDIA son 10-K raporunda yapay zeka, veri merkezi büyümesi, ihracat kontrolleri ve Çin pazarıyla ilgili hangi riskleri açıklıyor?"

    results = search_relevant_chunks(
        query=query,
        ticker="NVDA",
        top_k=5,
    )

    print_retrieval_results(results)


if __name__ == "__main__":
    main()