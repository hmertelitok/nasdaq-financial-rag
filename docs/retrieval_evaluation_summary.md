# Retrieval Evaluation Summary

Generated at: `2026-07-19T01:42:33`

## Current Semantic Hybrid Retrieval Results

| Ticker | Query Count | Avg Precision@5 | Avg MRR | Avg nDCG@5 | Risk Factors Hits | Unknown Hits | Top-1 Sections |
|---|---:|---:|---:|---:|---:|---:|---|
| AAPL | 2 | 0.6 | 0.75 | 0.7853 | 0 | 0 | Business, Business |
| AMZN | 2 | 0.8 | 0.75 | 0.8232 | 0 | 0 | Business, Business |
| GOOGL | 2 | 0.8 | 0.75 | 0.8459 | 1 | 0 | Business, Risk Factors |
| MSFT | 2 | 0.7 | 0.75 | 0.7946 | 0 | 0 | Business, Business |
| NVDA | 2 | 0.7 | 1.0 | 0.816 | 3 | 0 | Business, Business |

## Before / After Retrieval Comparison

Score values are not directly comparable because the legacy system used TF-IDF adjusted scores, while the current system uses semantic embeddings with hybrid reranking.

| Ticker | Legacy Retrieval | Legacy Top-1 Section | Legacy Risk Factors Hits | Legacy Unknown Hits | Current Avg Precision@5 | Current Avg MRR | Current Avg nDCG@5 | Current Unknown Hits |
|---|---|---|---:|---:|---:|---:|---:|---:|
| AAPL | TF-IDF + manual boost | Business | 0 | 0 | 0.6 | 0.75 | 0.7853 | 0 |
| MSFT | TF-IDF + manual boost | Business | 0 | 0 | 0.7 | 0.75 | 0.7946 | 0 |
| NVDA | TF-IDF + manual boost | Risk Factors | 4 | 0 | 0.7 | 1.0 | 0.816 | 0 |
| AMZN | TF-IDF + manual boost | Risk Factors | 1 | 0 | 0.8 | 0.75 | 0.8232 | 0 |
| GOOGL | TF-IDF + manual boost | Risk Factors | 2 | 0 | 0.8 | 0.75 | 0.8459 | 0 |

## Query-Level Results

| Query ID | Ticker | Precision@5 | MRR | nDCG@5 | Highly Relevant | Partial | Not Relevant | Top-1 Section |
|---|---|---:|---:|---:|---:|---:|---:|---|
| AAPL_SUPPLY_REGULATION | AAPL | 0.4 | 0.5 | 0.6241 | 0 | 2 | 3 | Business |
| AAPL_AI_PRIVACY | AAPL | 0.8 | 1.0 | 0.9465 | 1 | 3 | 1 | Business |
| MSFT_AI_CLOUD_SECURITY | MSFT | 0.6 | 1.0 | 0.8855 | 0 | 3 | 2 | Business |
| MSFT_REGULATORY_COMPETITION | MSFT | 0.8 | 0.5 | 0.7038 | 1 | 3 | 1 | Business |
| NVDA_EXPORT_CHINA | NVDA | 0.8 | 1.0 | 0.8382 | 1 | 3 | 1 | Business |
| NVDA_SUPPLY_DATACENTER | NVDA | 0.6 | 1.0 | 0.7939 | 1 | 2 | 2 | Business |
| AMZN_AWS_OPERATIONS | AMZN | 0.8 | 1.0 | 1.0 | 0 | 4 | 1 | Business |
| AMZN_PRIVACY_REGULATION | AMZN | 0.8 | 0.5 | 0.6464 | 1 | 3 | 1 | Business |
| GOOGL_ADS_ANTITRUST | GOOGL | 0.8 | 0.5 | 0.7606 | 0 | 4 | 1 | Business |
| GOOGL_AI_PRIVACY_CLOUD | GOOGL | 0.8 | 1.0 | 0.9312 | 2 | 2 | 1 | Risk Factors |

## Relevance Label Definitions

- `highly_relevant`: source matches expected section and multiple expected risk terms, or is manually labeled relevant.
- `partially_relevant`: source matches at least one expected section or multiple expected terms.
- `not_relevant`: source does not sufficiently match the expected source criteria.
