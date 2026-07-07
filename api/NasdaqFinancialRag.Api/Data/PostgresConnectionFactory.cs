using Microsoft.Extensions.Options;
using NasdaqFinancialRag.Api.Options;
using Npgsql;

namespace NasdaqFinancialRag.Api.Data;

public sealed class PostgresConnectionFactory
{
    private readonly string _connectionString;

    public PostgresConnectionFactory(IOptions<PostgresOptions> options)
    {
        _connectionString = options.Value.ToConnectionString();
    }

    public NpgsqlConnection CreateConnection()
    {
        return new NpgsqlConnection(_connectionString);
    }
}