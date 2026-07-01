# Retrieval Evaluation Summary

Generated at: `2026-07-01T06:33:00`

## Current Semantic Hybrid Retrieval Results

| Ticker | Query Count | Avg Precision@5 | Avg MRR | Avg nDCG@5 | Risk Factors Hits | Unknown Hits | Top-1 Sections |
|---|---:|---:|---:|---:|---:|---:|---|
| AAPL | 2 | 1.0 | 1.0 | 1.0 | 2 | 0 | Risk Factors, Risk Factors |
| AMZN | 2 | 1.0 | 1.0 | 1.0 | 3 | 0 | Risk Factors, Legal Proceedings |
| GOOGL | 2 | 1.0 | 1.0 | 0.9764 | 2 | 0 | Legal Proceedings, Cybersecurity |
| MSFT | 2 | 1.0 | 1.0 | 0.9698 | 6 | 0 | Risk Factors, Risk Factors |
| NVDA | 2 | 0.9 | 1.0 | 0.885 | 6 | 0 | Risk Factors, Risk Factors |

## Before / After Retrieval Comparison

Score values are not directly comparable because the legacy system used TF-IDF adjusted scores, while the current system uses semantic embeddings with hybrid reranking.

| Ticker | Legacy Retrieval | Legacy Top-1 Section | Legacy Risk Factors Hits | Legacy Unknown Hits | Current Avg Precision@5 | Current Avg MRR | Current Avg nDCG@5 | Current Unknown Hits |
|---|---|---|---:|---:|---:|---:|---:|---:|
| AAPL | TF-IDF + manual boost | Business | 0 | 0 | 1.0 | 1.0 | 1.0 | 0 |
| MSFT | TF-IDF + manual boost | Business | 0 | 0 | 1.0 | 1.0 | 0.9698 | 0 |
| NVDA | TF-IDF + manual boost | Risk Factors | 4 | 0 | 0.9 | 1.0 | 0.885 | 0 |
| AMZN | TF-IDF + manual boost | Risk Factors | 1 | 0 | 1.0 | 1.0 | 1.0 | 0 |
| GOOGL | TF-IDF + manual boost | Risk Factors | 2 | 0 | 1.0 | 1.0 | 0.9764 | 0 |

## Query-Level Results

| Query ID | Ticker | Precision@5 | MRR | nDCG@5 | Highly Relevant | Partial | Not Relevant | Top-1 Section |
|---|---|---:|---:|---:|---:|---:|---:|---|
| AAPL_SUPPLY_REGULATION | AAPL | 1.0 | 1.0 | 1.0 | 5 | 0 | 0 | Risk Factors |
| AAPL_AI_PRIVACY | AAPL | 1.0 | 1.0 | 1.0 | 4 | 1 | 0 | Risk Factors |
| MSFT_AI_CLOUD_SECURITY | MSFT | 1.0 | 1.0 | 0.9395 | 4 | 1 | 0 | Risk Factors |
| MSFT_REGULATORY_COMPETITION | MSFT | 1.0 | 1.0 | 1.0 | 5 | 0 | 0 | Risk Factors |
| NVDA_EXPORT_CHINA | NVDA | 1.0 | 1.0 | 1.0 | 4 | 1 | 0 | Risk Factors |
| NVDA_SUPPLY_DATACENTER | NVDA | 0.8 | 1.0 | 0.77 | 2 | 2 | 1 | Risk Factors |
| AMZN_AWS_OPERATIONS | AMZN | 1.0 | 1.0 | 1.0 | 5 | 0 | 0 | Risk Factors |
| AMZN_PRIVACY_REGULATION | AMZN | 1.0 | 1.0 | 1.0 | 5 | 0 | 0 | Legal Proceedings |
| GOOGL_ADS_ANTITRUST | GOOGL | 1.0 | 1.0 | 0.972 | 4 | 1 | 0 | Legal Proceedings |
| GOOGL_AI_PRIVACY_CLOUD | GOOGL | 1.0 | 1.0 | 0.9808 | 3 | 2 | 0 | Cybersecurity |

## Relevance Label Definitions

- `highly_relevant`: source matches expected section and multiple expected risk terms, or is manually labeled relevant.
- `partially_relevant`: source matches at least one expected section or multiple expected terms.
- `not_relevant`: source does not sufficiently match the expected source criteria.
