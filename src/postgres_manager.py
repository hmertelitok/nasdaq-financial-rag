import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "database" / "postgres_schema.sql"

load_dotenv(PROJECT_ROOT / ".env")


SUPPORTED_COMPANIES = [
    {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "cik": "0000320193",
    },
    {
        "ticker": "MSFT",
        "company_name": "Microsoft Corporation",
        "cik": "0000789019",
    },
    {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "cik": "0001045810",
    },
    {
        "ticker": "AMZN",
        "company_name": "Amazon.com, Inc.",
        "cik": "0001018724",
    },
    {
        "ticker": "GOOGL",
        "company_name": "Alphabet Inc.",
        "cik": "0001652044",
    },
]


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


def execute_sql_file(sql_path: Path = SCHEMA_PATH) -> None:
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL dosyası bulunamadı: {sql_path}")

    sql_script = sql_path.read_text(encoding="utf-8")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_script)

        connection.commit()


def seed_companies() -> None:
    query = """
    INSERT INTO companies (ticker, company_name, cik)
    VALUES (%s, %s, %s)
    ON CONFLICT (ticker)
    DO UPDATE SET
        company_name = EXCLUDED.company_name,
        cik = EXCLUDED.cik;
    """

    company_rows = [
        (
            company["ticker"],
            company["company_name"],
            company["cik"],
        )
        for company in SUPPORTED_COMPANIES
    ]

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(query, company_rows)

        connection.commit()


def get_companies() -> List[Dict[str, Any]]:
    query = """
    SELECT ticker, company_name, cik, created_at
    FROM companies
    ORDER BY ticker;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    return [dict(row) for row in rows]


def check_pgvector_extension() -> Optional[Dict[str, Any]]:
    query = """
    SELECT extname, extversion
    FROM pg_extension
    WHERE extname = 'vector';
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchone()

    return dict(result) if result else None


def get_table_counts() -> List[Dict[str, Any]]:
    query = """
    SELECT
        table_name,
        (
            xpath(
                '/row/c/text()',
                query_to_xml(
                    format('SELECT count(*) AS c FROM %I', table_name),
                    false,
                    true,
                    ''
                )
            )
        )[1]::text::int AS row_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    return [dict(row) for row in rows]


def print_postgres_status() -> None:
    config = get_postgres_config()

    print("PostgreSQL bağlantı bilgisi")
    print(f"Host: {config['host']}")
    print(f"Port: {config['port']}")
    print(f"Database: {config['dbname']}")
    print(f"User: {config['user']}")
    print()

    extension = check_pgvector_extension()

    if extension:
        print(f"pgvector aktif: {extension['extname']} {extension['extversion']}")
    else:
        print("pgvector aktif değil")

    print()
    print("Kayıtlı şirketler")

    for company in get_companies():
        print(
            f"- {company['ticker']}: "
            f"{company['company_name']} "
            f"(CIK: {company['cik']})"
        )

    print()
    print("Tablo kayıt sayıları")

    for table in get_table_counts():
        print(f"- {table['table_name']}: {table['row_count']}")


def main() -> None:
    execute_sql_file()
    seed_companies()
    print_postgres_status()


if __name__ == "__main__":
    main()