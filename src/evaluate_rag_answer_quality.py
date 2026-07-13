from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import requests


DEFAULT_API_URL = "http://localhost:5094/api/rag/ask"
DEFAULT_MODEL_ALIAS = "qwen2.5-7b"
DEFAULT_TOP_K = 5

FORBIDDEN_TERMS = (
    "güvenlik ve güvenlik",
    "doğal kaza",
    "yarışma",
    "hak ve izinler",
    "rekabet kurma",
    "satın almakistemelerini",
    "olumlu yönde etkileyebilir",
    "microsoft'in",
    "microsoft'e",
    "a w s",
    "p r c",
    "vekârlılığı",
    "telif hakkı ihlallerini koruması",
)

TEST_CASES: Sequence[Dict[str, str]] = (
    {
        "ticker": "AAPL",
        "query": "Apple'ın temel iş riskleri nelerdir?",
    },
    {
        "ticker": "MSFT",
        "query": (
            "Microsoft'un yapay zeka, bulut ve siber güvenlik "
            "riskleri nelerdir?"
        ),
    },
    {
        "ticker": "NVDA",
        "query": (
            "NVIDIA'nın tedarik zinciri, ihracat kontrolleri ve "
            "yapay zeka talebiyle ilgili riskleri nelerdir?"
        ),
    },
    {
        "ticker": "AMZN",
        "query": (
            "Amazon'un AWS, lojistik, operasyonel maliyetler ve "
            "düzenleyici riskleri nelerdir?"
        ),
    },
    {
        "ticker": "GOOGL",
        "query": (
            "Alphabet'in yapay zeka, reklam pazarı, veri gizliliği "
            "ve antitröst riskleri nelerdir?"
        ),
    },
)


@dataclass
class EvaluationResult:
    ticker: str
    query: str
    passed: bool
    http_status: int | None
    source_count: int
    risk_item_count: int
    citation_count: int
    likely_controlled_fallback: bool
    checks: Dict[str, bool]
    errors: List[str]
    answer: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "ASP.NET Core RAG endpointini beş şirket için çağırır ve "
            "cevap kalitesi kontrollerini çalıştırır."
        )
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"RAG endpointi. Varsayılan: {DEFAULT_API_URL}",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=360,
        help="Her istek için saniye cinsinden zaman aşımı. Varsayılan: 360",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="İstenen kaynak sayısı. Varsayılan: 5",
    )
    parser.add_argument(
        "--model-alias",
        default=DEFAULT_MODEL_ALIAS,
        help=f"Foundry Local model alias'ı. Varsayılan: {DEFAULT_MODEL_ALIAS}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Belirtilirse JSON ve CSV raporları bu klasöre yazılır. "
            "Belirtilmezse yalnızca terminal çıktısı üretilir."
        ),
    )
    return parser.parse_args()


def normalize_words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(
            r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+",
            text.casefold(),
        )
        if len(word) >= 4
    }


def extract_risk_items(answer: str) -> List[str]:
    items: List[str] = []

    for line in answer.splitlines():
        stripped = line.strip()

        if re.match(r"^(?:[-•]|\d+[.)])\s+", stripped):
            items.append(stripped)

    return items


def extract_citations(answer: str) -> List[int]:
    return [
        int(value)
        for value in re.findall(
            r"\[Kaynak\s*(\d+)\]",
            answer,
            flags=re.IGNORECASE,
        )
    ]


def has_near_duplicate_items(items: Iterable[str]) -> bool:
    normalized = [normalize_words(item) for item in items]

    for index, first in enumerate(normalized):
        for second in normalized[index + 1 :]:
            union = first | second

            if not union:
                continue

            overlap = len(first & second) / len(union)

            if overlap >= 0.50:
                return True

    return False


def looks_turkish(answer: str) -> bool:
    lowered = answer.casefold()
    markers = (
        "risk",
        "kaynak",
        "olumsuz",
        "etkileyebilir",
        "yükümlülük",
        "düzenleyici",
        "güvenlik",
        "değildir",
    )

    return sum(marker in lowered for marker in markers) >= 3


def evaluate_response(
    *,
    ticker: str,
    query: str,
    http_status: int,
    payload: Dict[str, Any],
) -> EvaluationResult:
    answer = str(payload.get("answer") or "").strip()
    source_count = int(payload.get("sourceCount") or 0)
    risk_items = extract_risk_items(answer)
    citations = extract_citations(answer)
    lowered = answer.casefold()

    citations_in_range = bool(citations) and all(
        1 <= citation <= source_count
        for citation in citations
    )

    every_item_has_citation = bool(risk_items) and all(
        re.search(
            r"\[Kaynak\s+\d+\]",
            item,
            flags=re.IGNORECASE,
        )
        is not None
        for item in risk_items
    )

    checks = {
        "http_200": http_status == 200,
        "answer_present": len(answer) >= 80,
        "source_count_at_least_3": source_count >= 3,
        "risk_item_count_3_to_5": 3 <= len(risk_items) <= 5,
        "every_item_has_citation": every_item_has_citation,
        "citations_in_source_range": citations_in_range,
        "citation_format_exact": (
            re.search(
                r"\[Kaynak\d+\]",
                answer,
                flags=re.IGNORECASE,
            )
            is None
        ),
        "spaced_acronyms_absent": (
            re.search(
                r"\b(?:[A-ZÇĞİÖŞÜ]\s+){2,}[A-ZÇĞİÖŞÜ]\b",
                answer,
            )
            is None
        ),
        "merged_words_absent": not any(
            value in lowered
            for value in (
                "vekârlılığı",
                "vegelir",
                "vebüyüme",
            )
        ),
        "risk_items_concise": bool(risk_items) and all(
            len(item) <= 420
            for item in risk_items
        ),
        "disclaimer_present": (
            "bu çıktı yatırım tavsiyesi değildir." in lowered
        ),
        "forbidden_terms_absent": not any(
            term in lowered
            for term in FORBIDDEN_TERMS
        ),
        "duplicate_items_absent": not has_near_duplicate_items(risk_items),
        "turkish_language_likely": looks_turkish(answer),
        "answer_length_reasonable": 80 <= len(answer) <= 3500,
    }

    errors = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    likely_controlled_fallback = answer.startswith(
        f"{ticker} için SEC kaynaklarında öne çıkan temel riskler:"
    )

    return EvaluationResult(
        ticker=ticker,
        query=query,
        passed=all(checks.values()),
        http_status=http_status,
        source_count=source_count,
        risk_item_count=len(risk_items),
        citation_count=len(citations),
        likely_controlled_fallback=likely_controlled_fallback,
        checks=checks,
        errors=errors,
        answer=answer,
    )


def evaluate_case(
    *,
    api_url: str,
    timeout: int,
    top_k: int,
    model_alias: str,
    ticker: str,
    query: str,
) -> EvaluationResult:
    request_body = {
        "query": query,
        "ticker": ticker,
        "section": None,
        "topK": top_k,
        "modelAlias": model_alias,
    }

    try:
        response = requests.post(
            api_url,
            json=request_body,
            timeout=timeout,
        )
    except requests.RequestException as exception:
        return EvaluationResult(
            ticker=ticker,
            query=query,
            passed=False,
            http_status=None,
            source_count=0,
            risk_item_count=0,
            citation_count=0,
            likely_controlled_fallback=False,
            checks={"request_completed": False},
            errors=[f"request_error: {exception}"],
            answer="",
        )

    try:
        payload = response.json()
    except ValueError:
        return EvaluationResult(
            ticker=ticker,
            query=query,
            passed=False,
            http_status=response.status_code,
            source_count=0,
            risk_item_count=0,
            citation_count=0,
            likely_controlled_fallback=False,
            checks={"json_response": False},
            errors=["response_is_not_json"],
            answer=response.text[:1000],
        )

    if response.status_code != 200:
        return EvaluationResult(
            ticker=ticker,
            query=query,
            passed=False,
            http_status=response.status_code,
            source_count=0,
            risk_item_count=0,
            citation_count=0,
            likely_controlled_fallback=False,
            checks={"http_200": False},
            errors=[f"http_{response.status_code}"],
            answer=json.dumps(payload, ensure_ascii=False),
        )

    return evaluate_response(
        ticker=ticker,
        query=query,
        http_status=response.status_code,
        payload=payload,
    )


def print_result(result: EvaluationResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    mode = (
        "controlled-fallback"
        if result.likely_controlled_fallback
        else "model-answer"
    )

    print()
    print("=" * 80)
    print(f"{result.ticker} | {status} | {mode}")
    print("=" * 80)
    print(
        f"HTTP: {result.http_status} | "
        f"Kaynak: {result.source_count} | "
        f"Risk maddesi: {result.risk_item_count} | "
        f"Atıf: {result.citation_count}"
    )

    if result.errors:
        print("Başarısız kontroller:")
        for error in result.errors:
            print(f"  - {error}")

    print()
    print(result.answer)


def write_reports(
    output_dir: Path,
    results: Sequence[EvaluationResult],
) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "rag_quality_evaluation.json"
    csv_path = output_dir / "rag_quality_evaluation.csv"

    generated_at = datetime.now(timezone.utc).isoformat()

    json_payload = {
        "generatedAt": generated_at,
        "passed": all(result.passed for result in results),
        "total": len(results),
        "passedCount": sum(result.passed for result in results),
        "failedCount": sum(not result.passed for result in results),
        "results": [asdict(result) for result in results],
    }

    json_path.write_text(
        json.dumps(
            json_payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "ticker",
                "passed",
                "http_status",
                "source_count",
                "risk_item_count",
                "citation_count",
                "likely_controlled_fallback",
                "errors",
            ],
        )
        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    "ticker": result.ticker,
                    "passed": result.passed,
                    "http_status": result.http_status,
                    "source_count": result.source_count,
                    "risk_item_count": result.risk_item_count,
                    "citation_count": result.citation_count,
                    "likely_controlled_fallback": (
                        result.likely_controlled_fallback
                    ),
                    "errors": "; ".join(result.errors),
                }
            )

    return json_path, csv_path


def main() -> int:
    args = parse_args()

    results: List[EvaluationResult] = []

    for test_case in TEST_CASES:
        result = evaluate_case(
            api_url=args.api_url,
            timeout=args.timeout,
            top_k=args.top_k,
            model_alias=args.model_alias,
            ticker=test_case["ticker"],
            query=test_case["query"],
        )
        results.append(result)
        print_result(result)

    passed_count = sum(result.passed for result in results)
    failed_count = len(results) - passed_count

    print()
    print("#" * 80)
    print("GENEL SONUÇ")
    print("#" * 80)
    print(
        f"Toplam: {len(results)} | "
        f"Başarılı: {passed_count} | "
        f"Başarısız: {failed_count}"
    )

    if args.output_dir is not None:
        json_path, csv_path = write_reports(
            output_dir=args.output_dir,
            results=results,
        )
        print(f"JSON raporu: {json_path}")
        print(f"CSV raporu: {csv_path}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
