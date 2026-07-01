from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from retriever import search_relevant_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation"
OUTPUT_PATH = OUTPUT_DIR / "retrieval_baseline.csv"


EVALUATION_QUERIES = {
    "AAPL": "Apple son 10-K raporunda teknoloji, tedarik zinciri, rekabet, Çin pazarı ve düzenleyici risklerle ilgili hangi konular öne çıkıyor?",
    "MSFT": "Microsoft son 10-K raporunda yapay zeka, bulut, veri merkezi, siber güvenlik ve düzenleyici risklerle ilgili hangi konular öne çıkıyor?",
    "NVDA": "NVIDIA son 10-K raporunda yapay zeka, veri merkezi büyümesi, ihracat kontrolleri, Çin pazarı ve tedarik riskleriyle ilgili hangi konular öne çıkıyor?",
    "AMZN": "Amazon son 10-K raporunda AWS, lojistik, operasyonel maliyetler, regülasyon ve rekabet riskleriyle ilgili hangi konular öne çıkıyor?",
    "GOOGL": "Alphabet son 10-K raporunda yapay zeka, reklam pazarı, veri gizliliği, antitröst ve düzenleyici risklerle ilgili hangi konular öne çıkıyor?",
}


def calculate_metrics(ticker: str, query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not results:
        return {
            "ticker": ticker,
            "query": query,
            "top_1_score": 0.0,
            "avg_top_5_score": 0.0,
            "risk_factor_hits": 0,
            "unknown_hits": 0,
            "result_count": 0,
            "top_1_section": "N/A",
            "top_1_chunk_id": "N/A",
            "top_1_url": "N/A",
        }

    scores = [float(result.get("score", 0.0)) for result in results]
    sections = [result.get("section", "Unknown") for result in results]

    risk_factor_hits = sum(1 for section in sections if section == "Risk Factors")
    unknown_hits = sum(1 for section in sections if section == "Unknown")

    top_result = results[0]

    return {
        "ticker": ticker,
        "query": query,
        "top_1_score": round(scores[0], 4),
        "avg_top_5_score": round(sum(scores) / len(scores), 4),
        "risk_factor_hits": risk_factor_hits,
        "unknown_hits": unknown_hits,
        "result_count": len(results),
        "top_1_section": top_result.get("section", "Unknown"),
        "top_1_chunk_id": top_result.get("chunk_id", "N/A"),
        "top_1_url": top_result.get("source_document_url", "N/A"),
    }


def print_results(ticker: str, query: str, results: List[Dict[str, Any]]) -> None:
    print("=" * 80)
    print(f"{ticker} RETRIEVAL SONUÇLARI")
    print("=" * 80)
    print(f"Sorgu: {query}")
    print("-" * 80)

    if not results:
        print("Sonuç bulunamadı.")
        return

    for index, result in enumerate(results, start=1):
        print(f"{index}. {result.get('ticker')} - {result.get('company_name')}")
        print(f"   Section: {result.get('section')}")
        print(f"   Chunk ID: {result.get('chunk_id')}")
        print(f"   Score: {result.get('score')}")
        print(f"   Original Score: {result.get('original_score')}")
        print(f"   Excerpt: {result.get('excerpt')}")
        print("-" * 80)


def run_evaluation(top_k: int = 5) -> pd.DataFrame:
    rows = []

    for ticker, query in EVALUATION_QUERIES.items():
        results = search_relevant_chunks(
            query=query,
            ticker=ticker,
            top_k=top_k,
        )

        print_results(ticker, query, results)

        metrics = calculate_metrics(
            ticker=ticker,
            query=query,
            results=results,
        )

        rows.append(metrics)

    return pd.DataFrame(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    evaluation_df = run_evaluation(top_k=5)
    evaluation_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 80)
    print("RETRIEVAL BASELINE ÖZETİ")
    print("=" * 80)
    print(evaluation_df.to_string(index=False))
    print("=" * 80)
    print(f"Sonuç dosyası kaydedildi: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()