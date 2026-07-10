namespace NasdaqFinancialRag.Api.Options;

public sealed class PgvectorSearchServiceOptions
{
    public const string SectionName = "PgvectorSearchService";

    public string BaseUrl { get; init; } = "http://127.0.0.1:8001";
    public int TimeoutSeconds { get; init; } = 120;
}
