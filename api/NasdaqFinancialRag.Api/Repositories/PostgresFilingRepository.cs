using System.Text;
using NasdaqFinancialRag.Api.Data;
using NasdaqFinancialRag.Api.Models;
using Npgsql;
using NpgsqlTypes;

namespace NasdaqFinancialRag.Api.Repositories;

public sealed class PostgresFilingRepository
{
    private readonly PostgresConnectionFactory _connectionFactory;

    public PostgresFilingRepository(PostgresConnectionFactory connectionFactory)
    {
        _connectionFactory = connectionFactory;
    }

    public async Task<IReadOnlyList<PostgresFilingDto>> GetFilingsAsync(
        string? ticker = null,
        string? filingType = null,
        int limit = 50,
        CancellationToken cancellationToken = default
    )
    {
        var sqlBuilder = new StringBuilder(
            """
            SELECT
                id,
                company_id,
                ticker,
                filing_type,
                filing_date,
                accession_number,
                source_url,
                local_path,
                created_at
            FROM filings
            """
        );

        var conditions = new List<string>();

        var normalizedTicker = string.IsNullOrWhiteSpace(ticker)
            ? null
            : ticker.Trim().ToUpperInvariant();

        var normalizedFilingType = string.IsNullOrWhiteSpace(filingType)
            ? null
            : filingType.Trim().ToUpperInvariant();

        if (normalizedTicker is not null)
        {
            conditions.Add("ticker = @ticker");
        }

        if (normalizedFilingType is not null)
        {
            conditions.Add("filing_type = @filing_type");
        }

        if (conditions.Count > 0)
        {
            sqlBuilder.AppendLine();
            sqlBuilder.Append("WHERE ");
            sqlBuilder.Append(string.Join(" AND ", conditions));
        }

        sqlBuilder.AppendLine();
        sqlBuilder.Append(
            """
            ORDER BY filing_date DESC NULLS LAST, id DESC
            LIMIT @limit;
            """
        );

        var filings = new List<PostgresFilingDto>();

        await using var connection = _connectionFactory.CreateConnection();
        await connection.OpenAsync(cancellationToken);

        await using var command = new NpgsqlCommand(sqlBuilder.ToString(), connection);

        if (normalizedTicker is not null)
        {
            command.Parameters.Add("ticker", NpgsqlDbType.Text).Value = normalizedTicker;
        }

        if (normalizedFilingType is not null)
        {
            command.Parameters.Add("filing_type", NpgsqlDbType.Text).Value = normalizedFilingType;
        }

        command.Parameters.Add("limit", NpgsqlDbType.Integer).Value = limit;

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);

        while (await reader.ReadAsync(cancellationToken))
        {
            filings.Add(
                new PostgresFilingDto(
                    Id: GetInt(reader, "id"),
                    CompanyId: GetInt(reader, "company_id"),
                    Ticker: GetString(reader, "ticker"),
                    FilingType: GetString(reader, "filing_type"),
                    FilingDate: GetNullableString(reader, "filing_date"),
                    AccessionNumber: GetNullableString(reader, "accession_number"),
                    SourceUrl: GetNullableString(reader, "source_url"),
                    LocalPath: GetNullableString(reader, "local_path"),
                    CreatedAt: GetNullableString(reader, "created_at")
                )
            );
        }

        return filings;
    }

    private static int GetInt(NpgsqlDataReader reader, string columnName)
    {
        var value = reader[columnName];

        if (value is null || value == DBNull.Value)
        {
            return 0;
        }

        return Convert.ToInt32(value);
    }

    private static string GetString(NpgsqlDataReader reader, string columnName)
    {
        var value = reader[columnName];

        if (value is null || value == DBNull.Value)
        {
            return string.Empty;
        }

        return Convert.ToString(value) ?? string.Empty;
    }

    private static string? GetNullableString(NpgsqlDataReader reader, string columnName)
    {
        var value = reader[columnName];

        if (value is null || value == DBNull.Value)
        {
            return null;
        }

        return Convert.ToString(value);
    }
}
