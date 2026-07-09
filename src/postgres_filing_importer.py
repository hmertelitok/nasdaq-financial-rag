import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "filings_metadata.json"

load_dotenv(PROJECT_ROOT / ".env")


def get_postgres_config() -> Dict[str, Any]:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5433")),
        "dbname": os.getenv("POSTGRES_DB", "nasdaq_financial_rag"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }


def get_connection():
    config = get_postgres_config()
    return psycopg2.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["dbname"],
        user=config["user"],
        password=config["password"],
        cursor_factory=RealDictCursor,
    )


def load_metadata() -> List[Dict[str, Any]]:
    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Metadata dosyası bulunamadı: {METADATA_PATH}")

    with METADATA_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("filings", "metadata", "items", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return value

        if all(isinstance(value, dict) for value in data.values()):
            return list(data.values())

    raise ValueError("filings_metadata.json beklenen list/dict formatında değil.")


def first_value(record: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_ticker(record: Dict[str, Any]) -> Optional[str]:
    ticker = first_value(record, ["ticker", "symbol", "company_ticker"])

    if ticker:
        return str(ticker).strip().upper()

    local_path = first_value(record, ["local_path", "raw_path", "file_path", "saved_path", "html_path"])
    if local_path:
        filename = Path(str(local_path)).name
        if "_" in filename:
            return filename.split("_")[0].upper()

    return None


def normalize_filing(record: Dict[str, Any]) -> Dict[str, Optional[str]]:
    ticker = normalize_ticker(record)

    filing_type = first_value(record, ["filing_type", "form", "form_type", "type"])
    filing_date = first_value(record, ["filing_date", "filed_at", "filed_date", "report_date", "date"])
    accession_number = first_value(record, ["accession_number", "accessionNo", "accession", "accession_no"])
    source_url = first_value(record, ["source_url", "document_url", "filing_url", "url", "primary_doc_url"])
    local_path = first_value(record, ["local_path", "raw_path", "file_path", "saved_path", "html_path"])
    company_name = first_value(record, ["company_name", "name", "company"])
    cik = first_value(record, ["cik", "company_cik"])

    return {
        "ticker": str(ticker).strip().upper() if ticker else None,
        "company_name": str(company_name).strip() if company_name else None,
        "cik": str(cik).zfill(10) if cik else None,
        "filing_type": str(filing_type).strip().upper() if filing_type else "10-K",
        "filing_date": str(filing_date).strip() if filing_date else None,
        "accession_number": str(accession_number).strip() if accession_number else None,
        "source_url": str(source_url).strip() if source_url else None,
        "local_path": str(local_path).strip() if local_path else None,
    }


def get_or_create_company_id(cursor, filing: Dict[str, Optional[str]]) -> int:
    ticker = filing["ticker"]

    if not ticker:
        raise ValueError("Ticker bilgisi boş olduğu için company_id çözülemedi.")

    cursor.execute(
        """
        INSERT INTO companies (ticker, company_name, cik)
        VALUES (%s, %s, %s)
        ON CONFLICT (ticker)
        DO UPDATE SET
            company_name = COALESCE(EXCLUDED.company_name, companies.company_name),
            cik = COALESCE(EXCLUDED.cik, companies.cik)
        RETURNING id;
        """,
        (
            ticker,
            filing["company_name"] or ticker,
            filing["cik"],
        ),
    )

    result = cursor.fetchone()
    return int(result["id"])


def existing_filing_id(cursor, filing: Dict[str, Optional[str]]) -> Optional[int]:
    cursor.execute(
        """
        SELECT id
        FROM filings
        WHERE ticker = %s
          AND filing_type = %s
          AND (
                accession_number = %s
                OR (accession_number IS NULL AND %s IS NULL)
              )
          AND (
                filing_date = %s::date
                OR (filing_date IS NULL AND %s IS NULL)
              )
        LIMIT 1;
        """,
        (
            filing["ticker"],
            filing["filing_type"],
            filing["accession_number"],
            filing["accession_number"],
            filing["filing_date"],
            filing["filing_date"],
        ),
    )

    result = cursor.fetchone()
    return int(result["id"]) if result else None


def upsert_filing(cursor, filing: Dict[str, Optional[str]]) -> str:
    company_id = get_or_create_company_id(cursor, filing)
    existing_id = existing_filing_id(cursor, filing)

    if existing_id:
        cursor.execute(
            """
            UPDATE filings
            SET
                company_id = %s,
                source_url = COALESCE(%s, source_url),
                local_path = COALESCE(%s, local_path)
            WHERE id = %s;
            """,
            (
                company_id,
                filing["source_url"],
                filing["local_path"],
                existing_id,
            ),
        )
        return "updated"

    cursor.execute(
        """
        INSERT INTO filings (
            company_id,
            ticker,
            filing_type,
            filing_date,
            accession_number,
            source_url,
            local_path
        )
        VALUES (%s, %s, %s, %s::date, %s, %s, %s);
        """,
        (
            company_id,
            filing["ticker"],
            filing["filing_type"],
            filing["filing_date"],
            filing["accession_number"],
            filing["source_url"],
            filing["local_path"],
        ),
    )

    return "inserted"


def main() -> None:
    raw_records = load_metadata()

    inserted = 0
    updated = 0
    skipped = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for record in raw_records:
                filing = normalize_filing(record)

                if not filing["ticker"]:
                    skipped += 1
                    print(f"Atlandı: ticker bulunamadı -> {record}")
                    continue

                result = upsert_filing(cursor, filing)

                if result == "inserted":
                    inserted += 1
                else:
                    updated += 1

        connection.commit()

    print("PostgreSQL filing metadata import tamamlandı")
    print(f"Metadata dosyası: {METADATA_PATH}")
    print(f"Eklenen kayıt: {inserted}")
    print(f"Güncellenen kayıt: {updated}")
    print(f"Atlanan kayıt: {skipped}")


if __name__ == "__main__":
    main()
