import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "database" / "postgres_schema.sql"

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


def execute_sql_file(sql_path: Path = SCHEMA_PATH) -> None:
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL dosyası bulunamadı: {sql_path}")

    sql_script = sql_path.read_text(encoding="utf-8")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_script)

        connection.commit()


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
    print("Tablo kayıt sayıları")

    for table in get_table_counts():
        print(f"- {table['table_name']}: {table['row_count']}")


def main() -> None:
    execute_sql_file()
    print_postgres_status()


if __name__ == "__main__":
    main()