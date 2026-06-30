"""
SEC 10-K raporlarını RAG yapısına uygun chunk parçalarına ayırma modülü.

Bu modülün görevleri:
- data/processed/filings_metadata.json dosyasını okumak
- Temizlenmiş 10-K metin dosyalarını açmak
- Metinleri belirli boyutlarda chunk parçalarına ayırmak
- Her chunk için ticker, company, filing type, filing date, section ve chunk id bilgisi üretmek
- Chunk verilerini data/chunks/filing_chunks.json dosyasına kaydetmek

Not:
data/chunks klasörü .gitignore içinde olduğu için üretilen chunk çıktıları GitHub'a yüklenmez.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]

METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "filings_metadata.json"
CHUNKS_OUTPUT_PATH = PROJECT_ROOT / "data" / "chunks" / "filing_chunks.json"

CHUNK_SIZE_WORDS = 800
CHUNK_OVERLAP_WORDS = 120


SECTION_PATTERNS = {
    "Business": [
        "item 1. business",
        "item 1 business",
    ],
    "Risk Factors": [
        "item 1a. risk factors",
        "item 1a risk factors",
        "risk factors",
    ],
    "Legal Proceedings": [
        "item 3. legal proceedings",
        "item 3 legal proceedings",
    ],
    "Management Discussion and Analysis": [
        "item 7. management’s discussion and analysis",
        "item 7. management's discussion and analysis",
        "management’s discussion and analysis",
        "management's discussion and analysis",
    ],
    "Market Risk": [
        "item 7a. quantitative and qualitative disclosures about market risk",
        "quantitative and qualitative disclosures about market risk",
    ],
    "Financial Statements": [
        "item 8. financial statements",
        "financial statements and supplementary data",
    ],
}


def load_metadata() -> List[Dict[str, Any]]:
    """SEC filing metadata dosyasını okur."""
    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            "filings_metadata.json bulunamadı. "
            "Önce src/sec_downloader.py ve src/text_cleaner.py dosyalarını çalıştırmalısın."
        )

    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def read_processed_text(file_path: str) -> str:
    """Temizlenmiş metin dosyasını okur."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Temizlenmiş metin dosyası bulunamadı: {path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()


def normalize_for_section_detection(text: str) -> str:
    """Section tespiti için metni sadeleştirir."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_section(text: str) -> str:
    """
    Chunk içeriğine göre yaklaşık section bilgisi tespit eder.

    SEC HTML formatları şirketten şirkete değişebildiği için bu tespit
    basit bir anahtar kelime yaklaşımıyla yapılmaktadır.
    """
    normalized_text = normalize_for_section_detection(text[:2000])

    for section_name, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if pattern in normalized_text:
                return section_name

    return "Unknown"


def split_text_into_words(text: str) -> List[str]:
    """Metni kelimelere ayırır."""
    return text.split()


def create_chunks_from_text(
    text: str,
    chunk_size: int = CHUNK_SIZE_WORDS,
    overlap: int = CHUNK_OVERLAP_WORDS,
) -> List[str]:
    """Metni belirlenen kelime sayısına göre overlap kullanarak chunk parçalarına ayırır."""
    words = split_text_into_words(text)

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        chunks.append(chunk_text)

        if end >= len(words):
            break

        start = end - overlap

    return chunks


def build_chunk_id(ticker: str, filing_type: str, filing_date: str, index: int) -> str:
    """Chunk için benzersiz id üretir."""
    safe_filing_type = filing_type.lower().replace("-", "")
    safe_date = filing_date.replace("-", "")
    return f"{ticker.lower()}_{safe_filing_type}_{safe_date}_{index:04d}"


def create_chunk_records_for_filing(filing: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Tek bir filing için chunk kayıtlarını oluşturur."""
    ticker = filing["ticker"]
    company_name = filing["company_name"]
    filing_type = filing["filing_type"]
    filing_date = filing["filing_date"]
    processed_text_path = filing.get("processed_text_path")

    if not processed_text_path:
        raise ValueError(
            f"{ticker} için processed_text_path bulunamadı. "
            "Önce src/text_cleaner.py çalıştırılmalı."
        )

    print(f"{ticker} için chunk üretimi başlıyor...")

    text = read_processed_text(processed_text_path)
    chunk_texts = create_chunks_from_text(text)

    chunk_records = []

    for index, chunk_text in enumerate(chunk_texts, start=1):
        chunk_id = build_chunk_id(
            ticker=ticker,
            filing_type=filing_type,
            filing_date=filing_date,
            index=index,
        )

        section = detect_section(chunk_text)

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
                "source_document_url": filing.get("document_url"),
                "source_local_path": processed_text_path,
                "text": chunk_text,
            }
        )

    print(f"{ticker} için {len(chunk_records)} chunk üretildi.")

    return chunk_records


def save_chunks(chunks: List[Dict[str, Any]]) -> None:
    """Tüm chunk kayıtlarını JSON dosyasına kaydeder."""
    CHUNKS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(CHUNKS_OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(chunks, file, ensure_ascii=False, indent=2)

    print(f"Chunk verileri kaydedildi: {CHUNKS_OUTPUT_PATH}")
    print(f"Toplam chunk sayısı: {len(chunks)}")


def chunk_all_filings() -> None:
    """Tüm temizlenmiş 10-K raporları için chunk üretimini çalıştırır."""
    metadata = load_metadata()
    all_chunks = []

    for filing in metadata:
        filing_chunks = create_chunk_records_for_filing(filing)
        all_chunks.extend(filing_chunks)

    save_chunks(all_chunks)


def main() -> None:
    """Chunk üretim sürecini çalıştırır."""
    chunk_all_filings()


if __name__ == "__main__":
    main()