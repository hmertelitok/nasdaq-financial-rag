namespace NasdaqFinancialRag.Api.Models;

public sealed record PostgresFilingDto(
    int Id,
    int CompanyId,
    string Ticker,
    string FilingType,
    string? FilingDate,
    string? AccessionNumber,
    string? SourceUrl,
    string? LocalPath,
    string? CreatedAt
);
