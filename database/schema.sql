PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    exchange TEXT DEFAULT 'NASDAQ',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS filings (
    filing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    filing_type TEXT NOT NULL,
    filing_date TEXT,
    source_document_url TEXT,
    raw_file_path TEXT,
    processed_text_path TEXT,
    char_count INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);

CREATE TABLE IF NOT EXISTS rag_queries (
    query_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    ticker TEXT,
    answer TEXT NOT NULL,
    top_k INTEGER NOT NULL,
    use_foundry_local INTEGER NOT NULL,
    retrieval_type TEXT,
    embedding_model TEXT,
    source_count INTEGER DEFAULT 0,
    avg_score REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rag_sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL,
    source_rank INTEGER NOT NULL,

    ticker TEXT,
    company_name TEXT,
    filing_type TEXT,
    filing_date TEXT,
    section TEXT,
    raw_section TEXT,
    chunk_id TEXT,

    score REAL,
    original_score REAL,
    retrieval_type TEXT,
    embedding_model TEXT,

    source_document_url TEXT,
    excerpt TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (query_id) REFERENCES rag_queries(query_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id_label TEXT,
    ticker TEXT,
    precision_at_5 REAL,
    mrr REAL,
    ndcg_at_5 REAL,
    risk_factor_hits INTEGER,
    unknown_hits INTEGER,
    result_count INTEGER,
    top_1_section TEXT,
    top_1_chunk_id TEXT,
    top_1_score REAL,
    retrieval_type TEXT,
    embedding_model TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_filings_ticker
ON filings(ticker);

CREATE INDEX IF NOT EXISTS idx_rag_queries_ticker
ON rag_queries(ticker);

CREATE INDEX IF NOT EXISTS idx_rag_queries_created_at
ON rag_queries(created_at);

CREATE INDEX IF NOT EXISTS idx_rag_sources_query_id
ON rag_sources(query_id);

CREATE INDEX IF NOT EXISTS idx_rag_sources_ticker
ON rag_sources(ticker);

CREATE INDEX IF NOT EXISTS idx_evaluation_results_ticker
ON evaluation_results(ticker);
