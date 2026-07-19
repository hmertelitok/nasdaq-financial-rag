CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    cik VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS filings (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    ticker VARCHAR(10) NOT NULL,
    filing_type VARCHAR(10) NOT NULL,
    filing_date DATE,
    accession_number TEXT,
    source_url TEXT,
    local_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ticker, filing_type, filing_date, source_url)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    filing_id INTEGER NOT NULL REFERENCES filings(id) ON DELETE CASCADE,
    ticker VARCHAR(10) NOT NULL,
    company_name TEXT,
    filing_type VARCHAR(10) NOT NULL,
    filing_date DATE,
    section TEXT,
    raw_section TEXT,
    chunk_id TEXT,
    chunk_index INTEGER,
    chunk_text TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    source_document_url TEXT,
    start_word_index INTEGER,
    end_word_index INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    embedding vector(384),
    embedding_model TEXT DEFAULT 'intfloat/multilingual-e5-small',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rag_queries (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    ticker VARCHAR(10),
    top_k INTEGER,
    use_foundry_local BOOLEAN DEFAULT TRUE,
    answer_text TEXT,
    retrieval_backend TEXT DEFAULT 'pgvector',
    llm_model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rag_sources (
    id SERIAL PRIMARY KEY,
    query_id INTEGER NOT NULL REFERENCES rag_queries(id) ON DELETE CASCADE,
    chunk_db_id INTEGER REFERENCES document_chunks(id) ON DELETE SET NULL,
    ticker VARCHAR(10),
    company_name TEXT,
    filing_type VARCHAR(10),
    filing_date DATE,
    section TEXT,
    raw_section TEXT,
    chunk_id TEXT,
    score DOUBLE PRECISION,
    original_score DOUBLE PRECISION,
    retrieval_type TEXT,
    embedding_model TEXT,
    source_document_url TEXT,
    excerpt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id SERIAL PRIMARY KEY,
    query_id TEXT,
    ticker VARCHAR(10),
    precision_at_5 DOUBLE PRECISION,
    mrr DOUBLE PRECISION,
    ndcg_at_5 DOUBLE PRECISION,
    result_count INTEGER,
    retrieval_backend TEXT DEFAULT 'pgvector',
    embedding_model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_filings_ticker_type
ON filings (ticker, filing_type);

CREATE INDEX IF NOT EXISTS idx_filings_date
ON filings (filing_date);

CREATE INDEX IF NOT EXISTS idx_chunks_ticker
ON document_chunks (ticker);

CREATE INDEX IF NOT EXISTS idx_chunks_filing_type
ON document_chunks (filing_type);

CREATE INDEX IF NOT EXISTS idx_chunks_section
ON document_chunks (section);

CREATE INDEX IF NOT EXISTS idx_rag_queries_ticker
ON rag_queries (ticker);

CREATE INDEX IF NOT EXISTS idx_rag_queries_created_at
ON rag_queries (created_at);

CREATE INDEX IF NOT EXISTS idx_rag_sources_query_id
ON rag_sources (query_id);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops);

