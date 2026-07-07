# PostgreSQL + pgvector API Notes

This document summarizes the PostgreSQL and pgvector integration added to the NASDAQ Financial RAG Assistant.

## Purpose

The PostgreSQL layer is introduced as the second-stage persistence and retrieval backend for the project.

The current system uses:

- Python for SEC 10-K processing, chunking, embedding, retrieval and Streamlit UI
- SQLite for local query logging
- PostgreSQL for structured financial document metadata
- pgvector for future semantic vector search
- ASP.NET Core Web API for exposing backend data endpoints

## PostgreSQL Container

Container name: nasdaq-pgvector

Database: nasdaq_financial_rag

Local port: 5433

Docker image: pgvector/pgvector:pg16

## Core Tables

The PostgreSQL schema includes:

- companies
- filings
- document_chunks
- rag_queries
- rag_sources
- evaluation_results

The document_chunks table includes a pgvector embedding column with 384 dimensions. This matches the current multilingual E5 embedding model.

## Current PostgreSQL API Endpoints

GET /api/postgres/companies

GET /api/postgres/stats/summary

GET /api/postgres/filings

GET /api/postgres/filings?ticker=AAPL

GET /api/postgres/filings?ticker=AAPL&filingType=10-K

## Current Status

The PostgreSQL integration currently supports:

- Npgsql database connection
- Company seed data
- Company listing endpoint
- PostgreSQL stats summary endpoint
- Filing metadata endpoint with ticker and filing type filters

The filings table is currently empty until SEC 10-K and 10-Q metadata import is implemented.

## Next Steps

1. Import SEC 10-K filing metadata into PostgreSQL
2. Import document chunks into PostgreSQL
3. Store embeddings in pgvector
4. Add pgvector semantic search from the .NET API
5. Extend the pipeline to support SEC 10-Q filings
