namespace NasdaqFinancialRag.Api.Options;

public sealed class PostgresOptions
{
    public const string SectionName = "Postgres";

    public string Host { get; init; } = "localhost";

    public int Port { get; init; } = 5433;

    public string Database { get; init; } = "nasdaq_financial_rag";

    public string Username { get; init; } = "postgres";

    public string Password { get; init; } = "postgres";

    public string ToConnectionString()
    {
        return
            $"Host={Host};" +
            $"Port={Port};" +
            $"Database={Database};" +
            $"Username={Username};" +
            $"Password={Password};" +
            "Include Error Detail=true";
    }
}