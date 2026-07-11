using System.Text.Json.Serialization;

namespace NasdaqFinancialRag.Api.Models;

public sealed record PgvectorAskResponseDto
{
    [JsonPropertyName("query")]
    public string Query { get; init; } = string.Empty;

    [JsonPropertyName("ticker")]
    public string? Ticker { get; init; }

    [JsonPropertyName("section")]
    public string? Section { get; init; }

    [JsonPropertyName("topK")]
    public int TopK { get; init; }

    [JsonPropertyName("embeddingModel")]
    public string EmbeddingModel { get; init; } = string.Empty;

    [JsonPropertyName("generationModel")]
    public string GenerationModel { get; init; } = string.Empty;

    [JsonPropertyName("answer")]
    public string Answer { get; init; } = string.Empty;

    [JsonPropertyName("sourceCount")]
    public int SourceCount { get; init; }

    [JsonPropertyName("sources")]
    public IReadOnlyList<PgvectorAskSourceDto> Sources { get; init; } =
        Array.Empty<PgvectorAskSourceDto>();
}

public sealed record PgvectorAskSourceDto
{
    [JsonPropertyName("id")]
    public int Id { get; init; }

    [JsonPropertyName("filing_id")]
    public int FilingId { get; init; }

    [JsonPropertyName("chunk_id")]
    public string ChunkId { get; init; } = string.Empty;

    [JsonPropertyName("chunk_index")]
    public int ChunkIndex { get; init; }

    [JsonPropertyName("ticker")]
    public string? Ticker { get; init; }

    [JsonPropertyName("filing_type")]
    public string? FilingType { get; init; }

    [JsonPropertyName("filing_date")]
    public string? FilingDate { get; init; }

    [JsonPropertyName("section")]
    public string? Section { get; init; }

    [JsonPropertyName("raw_section")]
    public string? RawSection { get; init; }

    [JsonPropertyName("excerpt")]
    public string? Excerpt { get; init; }

    [JsonPropertyName("token_count")]
    public int? TokenCount { get; init; }

    [JsonPropertyName("embedding_model")]
    public string? EmbeddingModel { get; init; }

    [JsonPropertyName("source_document_url")]
    public string? SourceDocumentUrl { get; init; }

    [JsonPropertyName("similarity")]
    public double Similarity { get; init; }
}
