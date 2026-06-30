"""
SEC 10-K raporları için metin temizleme modülü.

Bu modülün görevleri:
- data/processed/filings_metadata.json dosyasını okumak
- data/raw klasörüne indirilen SEC 10-K HTML dokümanlarını açmak
- HTML etiketlerini temizleyerek okunabilir düz metin çıkarmak
- Temizlenmiş metinleri data/processed klasörüne kaydetmek

Not:
data/raw ve data/processed klasörleri .gitignore içinde olduğu için GitHub'a yüklenmez.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]

METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "filings_metadata.json"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def load_metadata() -> List[Dict[str, Any]]:
    """SEC filing metadata dosyasını okur."""
    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            "filings_metadata.json bulunamadı. "
            "Önce src/sec_downloader.py dosyasını çalıştırmalısın."
        )

    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def read_html_file(file_path: str) -> str:
    """İndirilen SEC HTML dosyasını okur."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"HTML dosyası bulunamadı: {path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()


def extract_text_from_html(html_content: str) -> str:
    """HTML içeriğinden görünür metni çıkarır."""
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    return text


def normalize_text(text: str) -> str:
    """Ham metni RAG için daha okunabilir hale getirir."""
    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        line = re.sub(r"\s+", " ", line)

        if len(line) < 3:
            continue

        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines)

    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return cleaned_text


def build_processed_file_path(ticker: str, filing_type: str, filing_date: str) -> Path:
    """Temizlenmiş metin dosyası için çıktı yolunu oluşturur."""
    file_name = f"{ticker.lower()}_{filing_type.lower()}_{filing_date}_clean.txt"
    return PROCESSED_DATA_DIR / file_name


def clean_single_filing(filing: Dict[str, Any]) -> Dict[str, Any]:
    """Tek bir SEC filing dokümanını temizler ve kaydeder."""
    ticker = filing["ticker"]
    filing_type = filing["filing_type"]
    filing_date = filing["filing_date"]
    local_path = filing["local_path"]

    print(f"{ticker} için {filing_type} raporu temizleniyor...")

    html_content = read_html_file(local_path)
    raw_text = extract_text_from_html(html_content)
    cleaned_text = normalize_text(raw_text)

    output_path = build_processed_file_path(
        ticker=ticker,
        filing_type=filing_type,
        filing_date=filing_date
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(cleaned_text)

    print(f"Temiz metin kaydedildi: {output_path}")

    updated_filing = filing.copy()
    updated_filing["processed_text_path"] = str(output_path)
    updated_filing["cleaned_character_count"] = len(cleaned_text)

    return updated_filing


def save_updated_metadata(metadata: List[Dict[str, Any]]) -> None:
    """Temizlenmiş dosya yollarını metadata dosyasına ekleyerek kaydeder."""
    with open(METADATA_PATH, "w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    print(f"Güncellenmiş metadata kaydedildi: {METADATA_PATH}")


def clean_all_filings() -> None:
    """Tüm indirilen 10-K raporları için metin temizleme sürecini çalıştırır."""
    metadata = load_metadata()
    updated_metadata = []

    for filing in metadata:
        cleaned_filing = clean_single_filing(filing)
        updated_metadata.append(cleaned_filing)

    save_updated_metadata(updated_metadata)


def main() -> None:
    """Metin temizleme sürecini çalıştırır."""
    clean_all_filings()


if __name__ == "__main__":
    main()