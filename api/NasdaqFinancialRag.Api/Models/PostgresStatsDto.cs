namespace NasdaqFinancialRag.Api.Models;

public sealed record PostgresStatsDto(
    int CompanyCount,
    int FilingCount,
    int ChunkCount,
    int QueryCount,
    int SourceCount,
    string RetrievalBackend,
    string Database,
    DateTime CheckedAt
);
