using NasdaqFinancialRag.Api.Data;
using NasdaqFinancialRag.Api.Models;
using Npgsql;

namespace NasdaqFinancialRag.Api.Repositories;

public sealed class CompanyRepository
{
    private readonly PostgresConnectionFactory _connectionFactory;

    public CompanyRepository(PostgresConnectionFactory connectionFactory)
    {
        _connectionFactory = connectionFactory;
    }

    public async Task<IReadOnlyList<PostgresCompanyDto>> GetCompaniesAsync(
        CancellationToken cancellationToken = default
    )
    {
        const string sql = """
            SELECT
                id,
                ticker,
                company_name,
                cik,
                created_at
            FROM companies
            ORDER BY ticker;
            """;

        var companies = new List<PostgresCompanyDto>();

        await using var connection = _connectionFactory.CreateConnection();
        await connection.OpenAsync(cancellationToken);

        await using var command = new NpgsqlCommand(sql, connection);
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);

        var idOrdinal = reader.GetOrdinal("id");
        var tickerOrdinal = reader.GetOrdinal("ticker");
        var companyNameOrdinal = reader.GetOrdinal("company_name");
        var cikOrdinal = reader.GetOrdinal("cik");
        var createdAtOrdinal = reader.GetOrdinal("created_at");

        while (await reader.ReadAsync(cancellationToken))
        {
            var company = new PostgresCompanyDto(
                reader.GetInt32(idOrdinal),
                reader.GetString(tickerOrdinal),
                reader.GetString(companyNameOrdinal),
                reader.IsDBNull(cikOrdinal) ? null : reader.GetString(cikOrdinal),
                reader.GetDateTime(createdAtOrdinal)
            );

            companies.Add(company);
        }

        return companies;
    }
}