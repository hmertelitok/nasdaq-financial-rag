"""
SEC EDGAR üzerinden seçili NASDAQ şirketleri için 10-K raporlarını alma modülü.

Bu modülün görevleri:
- config/companies.json dosyasından şirketleri okumak
- SEC submissions endpoint üzerinden filing listesini almak
- Her şirket için en güncel 10-K raporunu bulmak
- 10-K metadata bilgisini data/processed/filings_metadata.json dosyasına kaydetmek
- 10-K dokümanlarını data/raw/ klasörüne indirmek

Not:
data/raw ve data/processed klasörleri .gitignore içinde olduğu için GitHub'a yüklenmez.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMPANIES_PATH = PROJECT_ROOT / "config" / "companies.json"
METADATA_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "filings_metadata.json"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"


def load_companies() -> List[Dict[str, Any]]:
    """config/companies.json dosyasından şirket listesini okur."""
    with open(COMPANIES_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_cik(cik: str) -> str:
    """CIK kodunu SEC endpoint formatına uygun şekilde 10 haneli hale getirir."""
    return str(cik).zfill(10)


def get_headers() -> Dict[str, str]:
    """
    SEC istekleri için User-Agent bilgisini hazırlar.

    SEC, otomatik isteklerde User-Agent bilgisinin anlamlı olmasını bekler.
    Gerçek bilgi .env dosyasından okunur.
    """
    load_dotenv()

    user_agent = os.getenv(
        "SEC_USER_AGENT",
        "NASDAQ Financial RAG Assistant contact@example.com"
    )

    return {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate"
    }


def fetch_company_submissions(cik: str) -> Dict[str, Any]:
    """SEC submissions endpoint üzerinden şirket filing verilerini alır."""
    normalized_cik = normalize_cik(cik)
    url = SEC_SUBMISSIONS_URL.format(cik=normalized_cik)

    response = requests.get(url, headers=get_headers(), timeout=30)
    response.raise_for_status()

    return response.json()


def find_latest_10k(submissions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Şirket filing listesi içinden en güncel 10-K raporunu bulur."""
    recent_filings = submissions.get("filings", {}).get("recent", {})

    forms = recent_filings.get("form", [])
    filing_dates = recent_filings.get("filingDate", [])
    accession_numbers = recent_filings.get("accessionNumber", [])
    primary_documents = recent_filings.get("primaryDocument", [])

    for index, form_type in enumerate(forms):
        if form_type == "10-K":
            return {
                "filing_type": form_type,
                "filing_date": filing_dates[index],
                "accession_number": accession_numbers[index],
                "primary_document": primary_documents[index]
            }

    return None


def build_document_url(cik: str, accession_number: str, primary_document: str) -> str:
    """SEC doküman URL'sini oluşturur."""
    cik_without_leading_zeros = str(int(cik))
    accession_clean = accession_number.replace("-", "")

    return (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_without_leading_zeros}/{accession_clean}/{primary_document}"
    )


def build_local_file_path(ticker: str, filing_type: str, filing_date: str, primary_document: str) -> Path:
    """İndirilecek SEC dokümanı için lokal dosya yolunu oluşturur."""
    extension = Path(primary_document).suffix or ".html"
    file_name = f"{ticker.lower()}_{filing_type.lower()}_{filing_date}{extension}"

    return RAW_DATA_DIR / file_name


def collect_latest_10k_metadata() -> List[Dict[str, Any]]:
    """Tüm seçili şirketler için en güncel 10-K metadata bilgisini toplar."""
    companies = load_companies()
    results = []

    for company in companies:
        ticker = company["ticker"]
        cik = company["cik"]

        print(f"{ticker} için SEC 10-K metadata bilgisi alınıyor...")

        submissions = fetch_company_submissions(cik)
        latest_10k = find_latest_10k(submissions)

        if latest_10k is None:
            print(f"{ticker} için 10-K raporu bulunamadı.")
            continue

        document_url = build_document_url(
            cik=cik,
            accession_number=latest_10k["accession_number"],
            primary_document=latest_10k["primary_document"]
        )

        local_file_path = build_local_file_path(
            ticker=ticker,
            filing_type=latest_10k["filing_type"],
            filing_date=latest_10k["filing_date"],
            primary_document=latest_10k["primary_document"]
        )

        results.append({
            "ticker": ticker,
            "company_name": company["company_name"],
            "cik": cik,
            "sector": company.get("sector"),
            "filing_type": latest_10k["filing_type"],
            "filing_date": latest_10k["filing_date"],
            "accession_number": latest_10k["accession_number"],
            "primary_document": latest_10k["primary_document"],
            "document_url": document_url,
            "local_path": str(local_file_path)
        })

        time.sleep(0.2)

    return results


def save_metadata(metadata: List[Dict[str, Any]]) -> None:
    """Toplanan metadata bilgisini JSON dosyasına kaydeder."""
    METADATA_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(METADATA_OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    print(f"Metadata kaydedildi: {METADATA_OUTPUT_PATH}")


def download_filing_document(document_url: str, local_path: str) -> None:
    """SEC 10-K dokümanını indirir ve lokal dosyaya kaydeder."""
    output_path = Path(local_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(document_url, headers=get_headers(), timeout=60)
    response.raise_for_status()

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(response.text)

    print(f"Doküman indirildi: {output_path}")


def download_all_filings(metadata: List[Dict[str, Any]]) -> None:
    """Metadata listesindeki tüm 10-K dokümanlarını indirir."""
    for item in metadata:
        ticker = item["ticker"]
        document_url = item["document_url"]
        local_path = item["local_path"]

        print(f"{ticker} için 10-K dokümanı indiriliyor...")
        download_filing_document(document_url, local_path)

        time.sleep(0.2)


def main() -> None:
    """SEC 10-K metadata alma ve doküman indirme sürecini çalıştırır."""
    metadata = collect_latest_10k_metadata()
    save_metadata(metadata)
    download_all_filings(metadata)


if __name__ == "__main__":
    main()