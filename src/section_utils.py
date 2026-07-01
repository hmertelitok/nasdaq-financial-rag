import re
from typing import Any, Dict


LOW_RELEVANCE_PATTERNS = [
    "table of contents",
    "signature",
    "exhibit index",
    "executive officers",
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


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("ı", "i")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_any(text: str, terms: list[str]) -> bool:
    normalized_text = normalize_text(text)
    return any(term.lower() in normalized_text for term in terms)


def is_low_relevance_text(text: str) -> bool:
    return contains_any(text, LOW_RELEVANCE_PATTERNS)


def polish_section_label(chunk: Dict[str, Any]) -> str:
    original_section = chunk.get("section", "Unknown")
    text = normalize_text(chunk.get("text", ""))

    if contains_any(
        text,
        [
            "cybersecurity",
            "security incident",
            "incident response",
            "audit and finance committee",
            "supplier trust",
            "information security",
        ],
    ):
        return "Cybersecurity"

    if contains_any(
        text,
        [
            "lawsuit",
            "litigation",
            "legal proceedings",
            "court",
            "antitrust",
            "competition law",
            "gdpr",
            "data protection regulation",
            "regulatory authorities",
        ],
    ):
        return "Legal Proceedings"

    if contains_any(
        text,
        [
            "foreign exchange",
            "interest rate",
            "market risk",
            "currency",
            "inflation",
            "tariff",
            "derivative instruments",
        ],
    ):
        return "Market Risk"

    if contains_any(
        text,
        [
            "risk factors",
            "could adversely affect",
            "may adversely affect",
            "material adverse",
            "adversely affect our business",
            "uncertainty",
            "restrictions remain in place",
            "export controls",
            "supply chain",
        ],
    ):
        return "Risk Factors"

    if contains_any(
        text,
        [
            "azure",
            "aws",
            "google cloud",
            "cloud services",
            "artificial intelligence",
            "data center",
            "datacenter",
            "advertising",
            "app store",
            "iphone",
            "gpu",
            "fulfillment",
            "logistics",
            "competition",
            "products and services",
        ],
    ):
        return "Business"

    if original_section in {
        "Risk Factors",
        "Business",
        "Market Risk",
        "Legal Proceedings",
        "Management Discussion and Analysis",
        "Financial Statements",
        "Cybersecurity",
    }:
        return original_section

    return original_section