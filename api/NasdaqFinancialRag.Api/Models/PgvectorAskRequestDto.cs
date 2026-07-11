using System.Text.Json.Serialization;

namespace NasdaqFinancialRag.Api.Models;

public sealed record PgvectorAskRequestDto
{
    [JsonPropertyName("query")]
    public string Query { get; init; } = string.Empty;

    [JsonPropertyName("ticker")]
    public string? Ticker { get; init; }

    [JsonPropertyName("section")]
    public string? Section { get; init; }

    [JsonPropertyName("topK")]
    public int TopK { get; init; } = 5;

    [JsonPropertyName("modelAlias")]
    public string ModelAlias { get; init; } = "qwen2.5-7b";
}
