namespace NasdaqFinancialRag.Api.Models;

public sealed record PostgresChunkDto(
    int Id,
    int? FilingId,
    string ChunkId,
    int ChunkIndex,
    string? Ticker,
    string? FilingType,
    string? FilingDate,
    string? Section,
    string? RawSection,
    string ChunkText,
    int TokenCount,
    string? EmbeddingModel,
    string? SourceDocumentUrl,
    string? CreatedAt
);
