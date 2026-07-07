namespace NasdaqFinancialRag.Api.Models;

public sealed record PostgresCompanyDto(
    int Id,
    string Ticker,
    string CompanyName,
    string? Cik,
    DateTime CreatedAt
);
