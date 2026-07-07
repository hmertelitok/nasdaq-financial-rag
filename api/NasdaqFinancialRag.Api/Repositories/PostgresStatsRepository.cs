using NasdaqFinancialRag.Api.Data;
using NasdaqFinancialRag.Api.Models;
using Npgsql;

namespace NasdaqFinancialRag.Api.Repositories;

public sealed class PostgresStatsRepository
{
    private readonly PostgresConnectionFactory _connectionFactory;

    public PostgresStatsRepository(PostgresConnectionFactory connectionFactory)
    {
        _connectionFactory = connectionFactory;
    }

    public async Task<PostgresStatsDto> GetSummaryAsync(
        CancellationToken cancellationToken = default
    )
    {
        const string sql = """
            SELECT
                (SELECT COUNT(*) FROM companies) AS company_count,
                (SELECT COUNT(*) FROM filings) AS filing_count,
                (SELECT COUNT(*) FROM document_chunks) AS chunk_count,
                (SELECT COUNT(*) FROM rag_queries) AS query_count,
                (SELECT COUNT(*) FROM rag_sources) AS source_count;
            """;

        await using var connection = _connectionFactory.CreateConnection();
        await connection.OpenAsync(cancellationToken);

        await using var command = new NpgsqlCommand(sql, connection);
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);

        if (!await reader.ReadAsync(cancellationToken))
        {
            return new PostgresStatsDto(
                CompanyCount: 0,
                FilingCount: 0,
                ChunkCount: 0,
                QueryCount: 0,
                SourceCount: 0,
                RetrievalBackend: "postgres-pgvector",
                Database: "nasdaq_financial_rag",
                CheckedAt: DateTime.UtcNow
            );
        }

        return new PostgresStatsDto(
            CompanyCount: GetCount(reader, "company_count"),
            FilingCount: GetCount(reader, "filing_count"),
            ChunkCount: GetCount(reader, "chunk_count"),
            QueryCount: GetCount(reader, "query_count"),
            SourceCount: GetCount(reader, "source_count"),
            RetrievalBackend: "postgres-pgvector",
            Database: "nasdaq_financial_rag",
            CheckedAt: DateTime.UtcNow
        );
    }

    private static int GetCount(NpgsqlDataReader reader, string columnName)
    {
        var value = reader[columnName];

        if (value is null || value == DBNull.Value)
        {
            return 0;
        }

        return Convert.ToInt32(value);
    }
}
