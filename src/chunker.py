import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]

METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "filings_metadata.json"
CHUNKS_OUTPUT_PATH = PROJECT_ROOT / "data" / "chunks" / "filing_chunks.json"

CHUNK_SIZE_WORDS = 800
CHUNK_OVERLAP_WORDS = 120


SECTION_MARKER_PATTERNS = {
    "Business": [
        r"\bitem\s+1[\.\:\-]?\s+business\b",
    ],
    "Risk Factors": [
        r"\bitem\s+1a[\.\:\-]?\s+risk\s+factors\b",
        r"\bitem\s+1a\s+risk\s+factors\b",
    ],
    "Unresolved Staff Comments": [
        r"\bitem\s+1b[\.\:\-]?\s+unresolved\s+staff\s+comments\b",
    ],
    "Properties": [
        r"\bitem\s+2[\.\:\-]?\s+properties\b",
    ],
    "Legal Proceedings": [
        r"\bitem\s+3[\.\:\-]?\s+legal\s+proceedings\b",
    ],
    "Mine Safety Disclosures": [
        r"\bitem\s+4[\.\:\-]?\s+mine\s+safety\s+disclosures\b",
    ],
    "Market for Registrant Common Equity": [
        r"\bitem\s+5[\.\:\-]?\s+market\s+for\s+registrant",
    ],
    "Selected Financial Data": [
        r"\bitem\s+6[\.\:\-]?\s+selected\s+financial\s+data\b",
    ],
    "Management Discussion and Analysis": [
        r"\bitem\s+7[\.\:\-]?\s+management[’']?s\s+discussion\s+and\s+analysis\b",
        r"\bitem\s+7[\.\:\-]?\s+management\s+discussion\s+and\s+analysis\b",
    ],
    "Market Risk": [
        r"\bitem\s+7a[\.\:\-]?\s+quantitative\s+and\s+qualitative\s+disclosures\s+about\s+market\s+risk\b",
    ],
    "Financial Statements": [
        r"\bitem\s+8[\.\:\-]?\s+financial\s+statements\b",
        r"\bitem\s+8[\.\:\-]?\s+financial\s+statements\s+and\s+supplementary\s+data\b",
    ],
    "Accounting Changes": [
        r"\bitem\s+9[\.\:\-]?\s+changes\s+in\s+and\s+disagreements\s+with\s+accountants\b",
    ],
    "Controls and Procedures": [
        r"\bitem\s+9a[\.\:\-]?\s+controls\s+and\s+procedures\b",
    ],
    "Other Information": [
        r"\bitem\s+9b[\.\:\-]?\s+other\s+information\b",
    ],
    "Directors and Governance": [
        r"\bitem\s+10[\.\:\-]?\s+directors\b",
    ],
    "Executive Compensation": [
        r"\bitem\s+11[\.\:\-]?\s+executive\s+compensation\b",
    ],
    "Security Ownership": [
        r"\bitem\s+12[\.\:\-]?\s+security\s+ownership\b",
    ],
    "Certain Relationships": [
        r"\bitem\s+13[\.\:\-]?\s+certain\s+relationships\b",
    ],
    "Principal Accountant Fees": [
        r"\bitem\s+14[\.\:\-]?\s+principal\s+accountant\s+fees\b",
    ],
    "Exhibits": [
        r"\bitem\s+15[\.\:\-]?\s+exhibits\b",
    ],
}

SECTION_FALLBACK_PATTERNS = {
    "Business": [
        r"\bbusiness overview\b",
        r"\bour business\b",
        r"\bproducts and services\b",
    ],
    "Risk Factors": [
        r"\brisk factors\b",
        r"\brisks related to\b",
        r"\bmay adversely affect\b",
        r"\bcould adversely affect\b",
        r"\bmaterially adversely affect\b",
    ],
    "Legal Proceedings": [
        r"\blegal proceedings\b",
        r"\blitigation\b",
        r"\bregulatory proceedings\b",
    ],
    "Management Discussion and Analysis": [
        r"\bmanagement[’']?s discussion and analysis\b",
        r"\bresults of operations\b",
        r"\bliquidity and capital resources\b",
    ],
    "Market Risk": [
        r"\bmarket risk\b",
        r"\binterest rate risk\b",
        r"\bforeign currency risk\b",
    ],
    "Financial Statements": [
        r"\bconsolidated statements\b",
        r"\bconsolidated balance sheets\b",
        r"\bnotes to consolidated financial statements\b",
    ],
}

RISK_CONTENT_SIGNALS = [
    "risk",
    "risks",
    "risk factors",
    "adversely affect",
    "adverse effect",
    "adverse impact",
    "material adverse",
    "negatively impact",
    "could harm",
    "could adversely",
    "may adversely",
    "uncertainty",
    "uncertain",
    "subject to",
    "litigation",
    "regulatory",
    "regulation",
    "competition",
    "competitive",
    "supply chain",
    "restrictions",
    "export controls",
]


def load_metadata() -> List[Dict[str, Any]]:
    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            "filings_metadata.json bulunamadı. Önce src/sec_downloader.py ve src/text_cleaner.py dosyalarını çalıştırmalısın."
        )

    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def read_processed_text(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Temizlenmiş metin dosyası bulunamadı: {path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()


def normalize_text(text: str) -> str:
    text = text.replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_section_markers(text: str) -> List[Dict[str, Any]]:
    normalized_text = normalize_text(text)
    markers = []

    for section_name, patterns in SECTION_MARKER_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
                markers.append(
                    {
                        "section": section_name,
                        "start": match.start(),
                        "match": match.group(0),
                    }
                )

    markers = sorted(markers, key=lambda item: item["start"])
    deduplicated_markers = []

    for marker in markers:
        if not deduplicated_markers:
            deduplicated_markers.append(marker)
            continue

        previous_marker = deduplicated_markers[-1]

        if (
            marker["section"] == previous_marker["section"]
            and abs(marker["start"] - previous_marker["start"]) <= 30
        ):
            continue

        deduplicated_markers.append(marker)

    return deduplicated_markers


def detect_section_from_position(
    start_char: int,
    section_markers: List[Dict[str, Any]],
) -> str:
    current_section = "Unknown"

    for marker in section_markers:
        if marker["start"] <= start_char:
            current_section = marker["section"]
        else:
            break

    return current_section


def detect_section_from_text(text: str) -> str:
    normalized_text = normalize_text(text[:5000])

    for section_name, patterns in SECTION_MARKER_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized_text, flags=re.IGNORECASE):
                return section_name

    for section_name, patterns in SECTION_FALLBACK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized_text, flags=re.IGNORECASE):
                return section_name

    return "Unknown"


def infer_section_from_content(text: str) -> str:
    normalized_text = normalize_text(text)
    signal_count = sum(1 for signal in RISK_CONTENT_SIGNALS if signal in normalized_text)

    if signal_count >= 4:
        return "Risk Factors"

    if "results of operations" in normalized_text or "liquidity and capital resources" in normalized_text:
        return "Management Discussion and Analysis"

    if "consolidated statements" in normalized_text or "consolidated balance sheets" in normalized_text:
        return "Financial Statements"

    return "Unknown"


def detect_section(
    chunk_text: str,
    start_char: int,
    section_markers: List[Dict[str, Any]],
) -> str:
    direct_section = detect_section_from_text(chunk_text)

    if direct_section != "Unknown":
        return direct_section

    positioned_section = detect_section_from_position(start_char, section_markers)

    if positioned_section != "Unknown":
        return positioned_section

    inferred_section = infer_section_from_content(chunk_text)

    if inferred_section != "Unknown":
        return inferred_section

    return "Unknown"


def get_word_spans(text: str) -> List[Tuple[str, int, int]]:
    return [(match.group(0), match.start(), match.end()) for match in re.finditer(r"\S+", text)]


def create_chunks_from_text(
    text: str,
    chunk_size: int = CHUNK_SIZE_WORDS,
    overlap: int = CHUNK_OVERLAP_WORDS,
) -> List[Dict[str, Any]]:
    word_spans = get_word_spans(text)

    if not word_spans:
        return []

    chunks = []
    start_word_index = 0

    while start_word_index < len(word_spans):
        end_word_index = min(start_word_index + chunk_size, len(word_spans))
        selected_words = word_spans[start_word_index:end_word_index]

        chunk_text = " ".join(word for word, _, _ in selected_words)
        start_char = selected_words[0][1]
        end_char = selected_words[-1][2]

        chunks.append(
            {
                "text": chunk_text,
                "start_word_index": start_word_index,
                "end_word_index": end_word_index,
                "start_char": start_char,
                "end_char": end_char,
            }
        )

        if end_word_index >= len(word_spans):
            break

        start_word_index = max(end_word_index - overlap, start_word_index + 1)

    return chunks


def build_chunk_id(ticker: str, filing_type: str, filing_date: str, index: int) -> str:
    safe_filing_type = filing_type.lower().replace("-", "")
    safe_date = filing_date.replace("-", "")
    return f"{ticker.lower()}_{safe_filing_type}_{safe_date}_{index:04d}"


def create_chunk_records_for_filing(filing: Dict[str, Any]) -> List[Dict[str, Any]]:
    ticker = filing["ticker"]
    company_name = filing["company_name"]
    filing_type = filing["filing_type"]
    filing_date = filing["filing_date"]
    processed_text_path = filing.get("processed_text_path")

    if not processed_text_path:
        raise ValueError(
            f"{ticker} için processed_text_path bulunamadı. Önce src/text_cleaner.py çalıştırılmalı."
        )

    print(f"{ticker} için chunk üretimi başlıyor...")

    text = read_processed_text(processed_text_path)
    section_markers = find_section_markers(text)
    chunk_items = create_chunks_from_text(text)

    print(f"{ticker} için {len(section_markers)} section marker bulundu.")

    chunk_records = []

    for index, chunk_item in enumerate(chunk_items, start=1):
        chunk_text = chunk_item["text"]
        chunk_id = build_chunk_id(
            ticker=ticker,
            filing_type=filing_type,
            filing_date=filing_date,
            index=index,
        )

        section = detect_section(
            chunk_text=chunk_text,
            start_char=chunk_item["start_char"],
            section_markers=section_markers,
        )

        chunk_records.append(
            {
                "chunk_id": chunk_id,
                "ticker": ticker,
                "company_name": company_name,
                "sector": filing.get("sector"),
                "filing_type": filing_type,
                "filing_date": filing_date,
                "section": section,
                "chunk_index": index,
                "word_count": len(chunk_text.split()),
                "start_word_index": chunk_item["start_word_index"],
                "end_word_index": chunk_item["end_word_index"],
                "start_char": chunk_item["start_char"],
                "end_char": chunk_item["end_char"],
                "source_document_url": filing.get("document_url"),
                "source_local_path": processed_text_path,
                "text": chunk_text,
            }
        )

    print(f"{ticker} için {len(chunk_records)} chunk üretildi.")

    return chunk_records


def save_chunks(chunks: List[Dict[str, Any]]) -> None:
    CHUNKS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(CHUNKS_OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(chunks, file, ensure_ascii=False, indent=2)

    print(f"Chunk verileri kaydedildi: {CHUNKS_OUTPUT_PATH}")
    print(f"Toplam chunk sayısı: {len(chunks)}")


def chunk_all_filings() -> None:
    metadata = load_metadata()
    all_chunks = []

    for filing in metadata:
        filing_chunks = create_chunk_records_for_filing(filing)
        all_chunks.extend(filing_chunks)

    save_chunks(all_chunks)


def main() -> None:
    chunk_all_filings()


if __name__ == "__main__":
    main()