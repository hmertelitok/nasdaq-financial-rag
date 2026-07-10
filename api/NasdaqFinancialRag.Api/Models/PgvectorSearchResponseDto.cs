using System.Text.Json.Serialization;

namespace NasdaqFinancialRag.Api.Models;

public sealed class PgvectorSearchResponseDto
{
    public string Query { get; init; } = string.Empty;
    public string? Ticker { get; init; }
    public string? Section { get; init; }
    public int Limit { get; init; }
    public string EmbeddingModel { get; init; } = string.Empty;
    public int ResultCount { get; init; }
    public IReadOnlyList<PgvectorSearchResultDto> Results { get; init; } =
        Array.Empty<PgvectorSearchResultDto>();
}

public sealed class PgvectorSearchResultDto
{
    public int Id { get; init; }

    [JsonPropertyName("filing_id")]
    public int? FilingId { get; init; }

    [JsonPropertyName("chunk_id")]
    public string ChunkId { get; init; } = string.Empty;

    [JsonPropertyName("chunk_index")]
    public int ChunkIndex { get; init; }

    public string? Ticker { get; init; }

    [JsonPropertyName("filing_type")]
    public string? FilingType { get; init; }

    [JsonPropertyName("filing_date")]
    public string? FilingDate { get; init; }

    public string? Section { get; init; }

    [JsonPropertyName("raw_section")]
    public string? RawSection { get; init; }

    public string? Excerpt { get; init; }

    [JsonPropertyName("token_count")]
    public int TokenCount { get; init; }

    [JsonPropertyName("embedding_model")]
    public string? EmbeddingModel { get; init; }

    [JsonPropertyName("source_document_url")]
    public string? SourceDocumentUrl { get; init; }

    public double Similarity { get; init; }
}
