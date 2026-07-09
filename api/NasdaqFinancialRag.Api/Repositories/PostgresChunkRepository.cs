using System.Text;
using NasdaqFinancialRag.Api.Data;
using NasdaqFinancialRag.Api.Models;
using Npgsql;
using NpgsqlTypes;

namespace NasdaqFinancialRag.Api.Repositories;

public sealed class PostgresChunkRepository
{
    private readonly PostgresConnectionFactory _connectionFactory;

    public PostgresChunkRepository(PostgresConnectionFactory connectionFactory)
    {
        _connectionFactory = connectionFactory;
    }

    public async Task<IReadOnlyList<PostgresChunkDto>> GetChunksAsync(
        string? ticker = null,
        string? section = null,
        int limit = 50,
        CancellationToken cancellationToken = default
    )
    {
        var sqlBuilder = new StringBuilder(
            """
            SELECT
                id,
                filing_id,
                chunk_id,
                chunk_index,
                ticker,
                filing_type,
                filing_date,
                section,
                raw_section,
                chunk_text,
                token_count,
                embedding_model,
                source_document_url,
                created_at
            FROM document_chunks
            """
        );

        var conditions = new List<string>();

        var normalizedTicker = string.IsNullOrWhiteSpace(ticker)
            ? null
            : ticker.Trim().ToUpperInvariant();

        var normalizedSection = string.IsNullOrWhiteSpace(section)
            ? null
            : section.Trim();

        if (normalizedTicker is not null)
        {
            conditions.Add("ticker = @ticker");
        }

        if (normalizedSection is not null)
        {
            conditions.Add("section ILIKE @section");
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
            ORDER BY ticker ASC, chunk_index ASC, id ASC
            LIMIT @limit;
            """
        );

        var chunks = new List<PostgresChunkDto>();

        await using var connection = _connectionFactory.CreateConnection();
        await connection.OpenAsync(cancellationToken);

        await using var command = new NpgsqlCommand(sqlBuilder.ToString(), connection);

        if (normalizedTicker is not null)
        {
            command.Parameters.Add("ticker", NpgsqlDbType.Text).Value = normalizedTicker;
        }

        if (normalizedSection is not null)
        {
            command.Parameters.Add("section", NpgsqlDbType.Text).Value = $"%{normalizedSection}%";
        }

        command.Parameters.Add("limit", NpgsqlDbType.Integer).Value = limit;

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);

        while (await reader.ReadAsync(cancellationToken))
        {
            chunks.Add(
                new PostgresChunkDto(
                    Id: GetInt(reader, "id"),
                    FilingId: GetNullableInt(reader, "filing_id"),
                    ChunkId: GetString(reader, "chunk_id"),
                    ChunkIndex: GetInt(reader, "chunk_index"),
                    Ticker: GetNullableString(reader, "ticker"),
                    FilingType: GetNullableString(reader, "filing_type"),
                    FilingDate: GetNullableString(reader, "filing_date"),
                    Section: GetNullableString(reader, "section"),
                    RawSection: GetNullableString(reader, "raw_section"),
                    ChunkText: GetString(reader, "chunk_text"),
                    TokenCount: GetInt(reader, "token_count"),
                    EmbeddingModel: GetNullableString(reader, "embedding_model"),
                    SourceDocumentUrl: GetNullableString(reader, "source_document_url"),
                    CreatedAt: GetNullableString(reader, "created_at")
                )
            );
        }

        return chunks;
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

    private static int? GetNullableInt(NpgsqlDataReader reader, string columnName)
    {
        var value = reader[columnName];

        if (value is null || value == DBNull.Value)
        {
            return null;
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
