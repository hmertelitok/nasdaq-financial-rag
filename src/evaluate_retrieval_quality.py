import csv
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from retriever import search_relevant_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GOLDEN_QUERIES_PATH = PROJECT_ROOT / "evaluation" / "golden_queries.json"
REPORT_CSV_PATH = PROJECT_ROOT / "data" / "evaluation" / "retrieval_quality_report.csv"
SOURCE_LABELS_CSV_PATH = PROJECT_ROOT / "data" / "evaluation" / "source_relevance_labels.csv"
README_TABLE_PATH = PROJECT_ROOT / "docs" / "retrieval_evaluation_summary.md"

TOP_K = 5


LEGACY_TFIDF_BASELINE = {
    "AAPL": {
        "retrieval_type": "TF-IDF + manual boost",
        "top_1_section": "Business",
        "risk_factor_hits": 0,
        "unknown_hits": 0,
        "avg_top_5_score": 0.1809,
    },
    "MSFT": {
        "retrieval_type": "TF-IDF + manual boost",
        "top_1_section": "Business",
        "risk_factor_hits": 0,
        "unknown_hits": 0,
        "avg_top_5_score": 0.3975,
    },
    "NVDA": {
        "retrieval_type": "TF-IDF + manual boost",
        "top_1_section": "Risk Factors",
        "risk_factor_hits": 4,
        "unknown_hits": 0,
        "avg_top_5_score": 0.7696,
    },
    "AMZN": {
        "retrieval_type": "TF-IDF + manual boost",
        "top_1_section": "Risk Factors",
        "risk_factor_hits": 1,
        "unknown_hits": 0,
        "avg_top_5_score": 0.1791,
    },
    "GOOGL": {
        "retrieval_type": "TF-IDF + manual boost",
        "top_1_section": "Risk Factors",
        "risk_factor_hits": 2,
        "unknown_hits": 0,
        "avg_top_5_score": 0.3308,
    },
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("ı", "i")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_term(text: str, term: str) -> bool:
    normalized_text = normalize_text(text)
    normalized_term = normalize_text(term)

    if len(normalized_term) <= 3:
        return re.search(rf"\b{re.escape(normalized_term)}\b", normalized_text) is not None

    return normalized_term in normalized_text


def count_matches(text: str, terms: List[str]) -> int:
    return sum(1 for term in terms if contains_term(text, term))


def load_golden_queries() -> List[Dict[str, Any]]:
    if not GOLDEN_QUERIES_PATH.exists():
        raise FileNotFoundError("evaluation/golden_queries.json bulunamadı.")

    with open(GOLDEN_QUERIES_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def assign_relevance_label(result: Dict[str, Any], query_case: Dict[str, Any]) -> int:
    chunk_id = result.get("chunk_id", "")

    if chunk_id in query_case.get("manual_relevant_chunk_ids", []):
        return 2

    if chunk_id in query_case.get("manual_partially_relevant_chunk_ids", []):
        return 1

    if chunk_id in query_case.get("manual_irrelevant_chunk_ids", []):
        return 0

    text = " ".join(
        [
            result.get("text", ""),
            result.get("excerpt", ""),
            result.get("section", ""),
        ]
    )

    expected_terms = query_case.get("expected_terms", [])
    expected_sections = query_case.get("expected_sections", [])

    matched_terms = count_matches(text, expected_terms)
    section_match = result.get("section") in expected_sections

    if section_match and matched_terms >= 3:
        return 2

    if matched_terms >= 4:
        return 2

    if section_match and matched_terms >= 1:
        return 1

    if matched_terms >= 2:
        return 1

    return 0


def label_to_text(label: int) -> str:
    if label == 2:
        return "highly_relevant"

    if label == 1:
        return "partially_relevant"

    return "not_relevant"


def precision_at_k(labels: List[int], k: int) -> float:
    top_labels = labels[:k]

    if not top_labels:
        return 0.0

    relevant_count = sum(1 for label in top_labels if label > 0)

    return relevant_count / len(top_labels)


def mrr_score(labels: List[int]) -> float:
    for index, label in enumerate(labels, start=1):
        if label > 0:
            return 1 / index

    return 0.0


def dcg_score(labels: List[int], k: int) -> float:
    dcg = 0.0

    for index, label in enumerate(labels[:k], start=1):
        gain = (2**label) - 1
        discount = math.log2(index + 1)
        dcg += gain / discount

    return dcg


def ndcg_at_k(labels: List[int], k: int) -> float:
    actual_dcg = dcg_score(labels, k)
    ideal_labels = sorted(labels, reverse=True)
    ideal_dcg = dcg_score(ideal_labels, k)

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg


def evaluate_query(query_case: Dict[str, Any]) -> Dict[str, Any]:
    results = search_relevant_chunks(
        query=query_case["query"],
        ticker=query_case["ticker"],
        top_k=TOP_K,
    )

    source_rows = []
    labels = []

    for rank, result in enumerate(results, start=1):
        label = assign_relevance_label(result, query_case)
        labels.append(label)

        source_rows.append(
            {
                "query_id": query_case["query_id"],
                "ticker": query_case["ticker"],
                "rank": rank,
                "chunk_id": result.get("chunk_id"),
                "section": result.get("section"),
                "raw_section": result.get("raw_section", result.get("section")),
                "score": result.get("score"),
                "original_score": result.get("original_score"),
                "retrieval_type": result.get("retrieval_type"),
                "relevance_label": label,
                "relevance_text": label_to_text(label),
                "url": result.get("source_document_url"),
                "excerpt": result.get("excerpt"),
            }
        )

    top_1 = results[0] if results else {}

    query_metrics = {
        "query_id": query_case["query_id"],
        "ticker": query_case["ticker"],
        "query": query_case["query"],
        "precision_at_5": round(precision_at_k(labels, TOP_K), 4),
        "mrr": round(mrr_score(labels), 4),
        "ndcg_at_5": round(ndcg_at_k(labels, TOP_K), 4),
        "highly_relevant_hits": sum(1 for label in labels if label == 2),
        "partially_relevant_hits": sum(1 for label in labels if label == 1),
        "not_relevant_hits": sum(1 for label in labels if label == 0),
        "risk_factor_hits": sum(1 for result in results if result.get("section") == "Risk Factors"),
        "unknown_hits": sum(1 for result in results if result.get("section") == "Unknown"),
        "result_count": len(results),
        "top_1_section": top_1.get("section"),
        "top_1_chunk_id": top_1.get("chunk_id"),
        "top_1_score": top_1.get("score"),
        "retrieval_type": top_1.get("retrieval_type"),
        "embedding_model": top_1.get("embedding_model"),
    }

    return {
        "query_metrics": query_metrics,
        "source_rows": source_rows,
    }


def save_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        return

    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def aggregate_by_ticker(query_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups = defaultdict(list)

    for row in query_rows:
        groups[row["ticker"]].append(row)

    aggregate_rows = []

    for ticker, rows in groups.items():
        aggregate_rows.append(
            {
                "ticker": ticker,
                "query_count": len(rows),
                "avg_precision_at_5": round(sum(row["precision_at_5"] for row in rows) / len(rows), 4),
                "avg_mrr": round(sum(row["mrr"] for row in rows) / len(rows), 4),
                "avg_ndcg_at_5": round(sum(row["ndcg_at_5"] for row in rows) / len(rows), 4),
                "total_risk_factor_hits": sum(row["risk_factor_hits"] for row in rows),
                "total_unknown_hits": sum(row["unknown_hits"] for row in rows),
                "top_1_sections": ", ".join(row["top_1_section"] or "N/A" for row in rows),
            }
        )

    return sorted(aggregate_rows, key=lambda item: item["ticker"])


def build_markdown_report(query_rows: List[Dict[str, Any]], aggregate_rows: List[Dict[str, Any]]) -> str:
    created_at = datetime.now().isoformat(timespec="seconds")

    lines = [
        "# Retrieval Evaluation Summary",
        "",
        f"Generated at: `{created_at}`",
        "",
        "## Current Semantic Hybrid Retrieval Results",
        "",
        "| Ticker | Query Count | Avg Precision@5 | Avg MRR | Avg nDCG@5 | Risk Factors Hits | Unknown Hits | Top-1 Sections |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for row in aggregate_rows:
        lines.append(
            f"| {row['ticker']} | {row['query_count']} | {row['avg_precision_at_5']} | "
            f"{row['avg_mrr']} | {row['avg_ndcg_at_5']} | {row['total_risk_factor_hits']} | "
            f"{row['total_unknown_hits']} | {row['top_1_sections']} |"
        )

    lines.extend(
        [
            "",
            "## Before / After Retrieval Comparison",
            "",
            "Score values are not directly comparable because the legacy system used TF-IDF adjusted scores, while the current system uses semantic embeddings with hybrid reranking.",
            "",
            "| Ticker | Legacy Retrieval | Legacy Top-1 Section | Legacy Risk Factors Hits | Legacy Unknown Hits | Current Avg Precision@5 | Current Avg MRR | Current Avg nDCG@5 | Current Unknown Hits |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )

    aggregate_by_ticker_map = {row["ticker"]: row for row in aggregate_rows}

    for ticker, baseline in LEGACY_TFIDF_BASELINE.items():
        current = aggregate_by_ticker_map.get(ticker, {})

        lines.append(
            f"| {ticker} | {baseline['retrieval_type']} | {baseline['top_1_section']} | "
            f"{baseline['risk_factor_hits']} | {baseline['unknown_hits']} | "
            f"{current.get('avg_precision_at_5', 'N/A')} | {current.get('avg_mrr', 'N/A')} | "
            f"{current.get('avg_ndcg_at_5', 'N/A')} | {current.get('total_unknown_hits', 'N/A')} |"
        )

    lines.extend(
        [
            "",
            "## Query-Level Results",
            "",
            "| Query ID | Ticker | Precision@5 | MRR | nDCG@5 | Highly Relevant | Partial | Not Relevant | Top-1 Section |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )

    for row in query_rows:
        lines.append(
            f"| {row['query_id']} | {row['ticker']} | {row['precision_at_5']} | "
            f"{row['mrr']} | {row['ndcg_at_5']} | {row['highly_relevant_hits']} | "
            f"{row['partially_relevant_hits']} | {row['not_relevant_hits']} | {row['top_1_section']} |"
        )

    lines.extend(
        [
            "",
            "## Relevance Label Definitions",
            "",
            "- `highly_relevant`: source matches expected section and multiple expected risk terms, or is manually labeled relevant.",
            "- `partially_relevant`: source matches at least one expected section or multiple expected terms.",
            "- `not_relevant`: source does not sufficiently match the expected source criteria.",
            "",
        ]
    )

    return "\n".join(lines)


def save_markdown_report(markdown_text: str) -> None:
    README_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(README_TABLE_PATH, "w", encoding="utf-8") as file:
        file.write(markdown_text)


def main() -> None:
    golden_queries = load_golden_queries()

    query_rows = []
    source_rows = []

    for query_case in golden_queries:
        print("=" * 80)
        print(f"{query_case['query_id']} değerlendiriliyor...")
        print(f"Ticker: {query_case['ticker']}")
        print("=" * 80)

        evaluation_result = evaluate_query(query_case)

        query_metrics = evaluation_result["query_metrics"]
        query_rows.append(query_metrics)
        source_rows.extend(evaluation_result["source_rows"])

        print(f"Precision@5: {query_metrics['precision_at_5']}")
        print(f"MRR: {query_metrics['mrr']}")
        print(f"nDCG@5: {query_metrics['ndcg_at_5']}")
        print(f"Top-1 Section: {query_metrics['top_1_section']}")
        print(f"Unknown Hits: {query_metrics['unknown_hits']}")

    aggregate_rows = aggregate_by_ticker(query_rows)
    markdown_report = build_markdown_report(query_rows, aggregate_rows)

    save_csv(REPORT_CSV_PATH, query_rows)
    save_csv(SOURCE_LABELS_CSV_PATH, source_rows)
    save_markdown_report(markdown_report)

    print("\n" + "=" * 80)
    print("RETRIEVAL QUALITY ÖZETİ")
    print("=" * 80)

    for row in aggregate_rows:
        print(
            f"{row['ticker']} | P@5: {row['avg_precision_at_5']} | "
            f"MRR: {row['avg_mrr']} | nDCG@5: {row['avg_ndcg_at_5']} | "
            f"Unknown: {row['total_unknown_hits']}"
        )

    print("=" * 80)
    print(f"Query report CSV: {REPORT_CSV_PATH}")
    print(f"Source labels CSV: {SOURCE_LABELS_CSV_PATH}")
    print(f"README markdown table: {README_TABLE_PATH}")


if __name__ == "__main__":
    main()