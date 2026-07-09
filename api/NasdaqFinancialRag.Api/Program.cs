using NasdaqFinancialRag.Api.Data;
using NasdaqFinancialRag.Api.Options;
using NasdaqFinancialRag.Api.Repositories;
using Microsoft.Data.Sqlite;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenApi();

builder.Services.Configure<PostgresOptions>(
    builder.Configuration.GetSection(PostgresOptions.SectionName)
);

builder.Services.AddSingleton<PostgresConnectionFactory>();
builder.Services.AddScoped<CompanyRepository>();
builder.Services.AddScoped<PostgresStatsRepository>();
builder.Services.AddScoped<PostgresFilingRepository>();
builder.Services.AddScoped<PostgresChunkRepository>();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

// Local geliÅŸtirme iÃ§in HTTPS yÃ¶nlendirmesini kapalÄ± tutuyoruz.
// app.UseHttpsRedirection();

var databasePath = Path.GetFullPath(
    Path.Combine(
        app.Environment.ContentRootPath,
        "..",
        "..",
        "data",
        "database",
        "nasdaq_financial_rag.db"
    )
);

var connectionString = new SqliteConnectionStringBuilder
{
    DataSource = databasePath
}.ToString();

app.MapGet("/", () =>
{
    return Results.Ok(new
    {
        name = "NASDAQ Financial RAG API",
        status = "running",
        databasePath,
        databaseExists = File.Exists(databasePath),
        endpoints = new[]
        {
            "GET /api/health",
            "GET /api/companies",
            "GET /api/postgres/companies",
            "GET /api/postgres/stats/summary",
            "GET /api/postgres/filings",
            "GET /api/postgres/chunks",
            "GET /api/queries",
            "GET /api/queries/{id}",
            "GET /api/queries/{id}/sources",
            "GET /api/stats/summary"
        }
    });
});

app.MapGet("/api/health", () =>
{
    return Results.Ok(new
    {
        status = "healthy",
        sqliteDatabaseExists = File.Exists(databasePath),
        sqliteDatabasePath = databasePath,
        postgresCompaniesEndpoint = "/api/postgres/companies",
        postgresStatsEndpoint = "/api/postgres/stats/summary",
        postgresFilingsEndpoint = "/api/postgres/filings",
        postgresChunksEndpoint = "/api/postgres/chunks",
        checkedAt = DateTime.UtcNow
    });
});

app.MapGet("/api/companies", () =>
{
    if (!File.Exists(databasePath))
    {
        return Results.Problem(
            title: "SQLite database not found",
            detail: $"Database path: {databasePath}",
            statusCode: StatusCodes.Status500InternalServerError
        );
    }

    using var connection = OpenConnection(connectionString);
    using var command = connection.CreateCommand();

    command.CommandText = """
        SELECT
            ticker,
            company_name,
            exchange,
            created_at
        FROM companies
        ORDER BY ticker;
        """;

    using var reader = command.ExecuteReader();

    var companies = new List<CompanyDto>();

    while (reader.Read())
    {
        companies.Add(new CompanyDto(
            Ticker: GetString(reader, "ticker"),
            CompanyName: GetString(reader, "company_name"),
            Exchange: GetNullableString(reader, "exchange"),
            CreatedAt: GetNullableString(reader, "created_at")
        ));
    }

    return Results.Ok(companies);
});

app.MapGet(
    "/api/postgres/companies",
    async (
        CompanyRepository companyRepository,
        CancellationToken cancellationToken
    ) =>
    {
        var companies = await companyRepository.GetCompaniesAsync(cancellationToken);

        return Results.Ok(companies);
    }
)
.WithName("GetPostgresCompanies")
.WithTags("PostgreSQL");

app.MapGet(
    "/api/postgres/stats/summary",
    async (
        PostgresStatsRepository statsRepository,
        CancellationToken cancellationToken
    ) =>
    {
        var summary = await statsRepository.GetSummaryAsync(cancellationToken);

        return Results.Ok(summary);
    }
)
.WithName("GetPostgresStatsSummary")
.WithTags("PostgreSQL");

app.MapGet(
    "/api/postgres/filings",
    async (
        PostgresFilingRepository filingRepository,
        string? ticker,
        string? filingType,
        int? limit,
        CancellationToken cancellationToken
    ) =>
    {
        var safeLimit = Math.Clamp(limit ?? 50, 1, 200);

        var filings = await filingRepository.GetFilingsAsync(
            ticker: ticker,
            filingType: filingType,
            limit: safeLimit,
            cancellationToken: cancellationToken
        );

        return Results.Ok(filings);
    }
)
.WithName("GetPostgresFilings")
.WithTags("PostgreSQL");

app.MapGet(
    "/api/postgres/chunks",
    async (
        PostgresChunkRepository chunkRepository,
        string? ticker,
        string? section,
        int? limit,
        CancellationToken cancellationToken
    ) =>
    {
        var safeLimit = Math.Clamp(limit ?? 50, 1, 200);

        var chunks = await chunkRepository.GetChunksAsync(
            ticker: ticker,
            section: section,
            limit: safeLimit,
            cancellationToken: cancellationToken
        );

        return Results.Ok(chunks);
    }
)
.WithName("GetPostgresChunks")
.WithTags("PostgreSQL");
app.MapGet("/api/queries", (int? limit) =>
{
    if (!File.Exists(databasePath))
    {
        return Results.Problem(
            title: "SQLite database not found",
            detail: $"Database path: {databasePath}",
            statusCode: StatusCodes.Status500InternalServerError
        );
    }

    var safeLimit = Math.Clamp(limit ?? 20, 1, 100);

    using var connection = OpenConnection(connectionString);
    using var command = connection.CreateCommand();

    command.CommandText = """
        SELECT
            query_id,
            ticker,
            query_text,
            source_count,
            avg_score,
            use_foundry_local,
            retrieval_type,
            embedding_model,
            created_at
        FROM rag_queries
        ORDER BY query_id DESC
        LIMIT $limit;
        """;

    command.Parameters.AddWithValue("$limit", safeLimit);

    using var reader = command.ExecuteReader();

    var queries = new List<QuerySummaryDto>();

    while (reader.Read())
    {
        queries.Add(new QuerySummaryDto(
            QueryId: GetInt(reader, "query_id"),
            Ticker: GetNullableString(reader, "ticker"),
            QueryText: GetString(reader, "query_text"),
            SourceCount: GetInt(reader, "source_count"),
            AvgScore: GetDouble(reader, "avg_score"),
            UseFoundryLocal: GetInt(reader, "use_foundry_local") == 1,
            RetrievalType: GetNullableString(reader, "retrieval_type"),
            EmbeddingModel: GetNullableString(reader, "embedding_model"),
            CreatedAt: GetNullableString(reader, "created_at")
        ));
    }

    return Results.Ok(queries);
});

app.MapGet("/api/queries/{id:int}", (int id) =>
{
    if (!File.Exists(databasePath))
    {
        return Results.Problem(
            title: "SQLite database not found",
            detail: $"Database path: {databasePath}",
            statusCode: StatusCodes.Status500InternalServerError
        );
    }

    using var connection = OpenConnection(connectionString);
    using var command = connection.CreateCommand();

    command.CommandText = """
        SELECT
            query_id,
            ticker,
            query_text,
            answer,
            top_k,
            use_foundry_local,
            retrieval_type,
            embedding_model,
            source_count,
            avg_score,
            created_at
        FROM rag_queries
        WHERE query_id = $id;
        """;

    command.Parameters.AddWithValue("$id", id);

    using var reader = command.ExecuteReader();

    if (!reader.Read())
    {
        return Results.NotFound(new
        {
            message = $"Query not found. Query ID: {id}"
        });
    }

    var query = new QueryDetailDto(
        QueryId: GetInt(reader, "query_id"),
        Ticker: GetNullableString(reader, "ticker"),
        QueryText: GetString(reader, "query_text"),
        Answer: GetString(reader, "answer"),
        TopK: GetInt(reader, "top_k"),
        UseFoundryLocal: GetInt(reader, "use_foundry_local") == 1,
        RetrievalType: GetNullableString(reader, "retrieval_type"),
        EmbeddingModel: GetNullableString(reader, "embedding_model"),
        SourceCount: GetInt(reader, "source_count"),
        AvgScore: GetDouble(reader, "avg_score"),
        CreatedAt: GetNullableString(reader, "created_at")
    );

    return Results.Ok(query);
});

app.MapGet("/api/queries/{id:int}/sources", (int id) =>
{
    if (!File.Exists(databasePath))
    {
        return Results.Problem(
            title: "SQLite database not found",
            detail: $"Database path: {databasePath}",
            statusCode: StatusCodes.Status500InternalServerError
        );
    }

    using var connection = OpenConnection(connectionString);
    using var command = connection.CreateCommand();

    command.CommandText = """
        SELECT
            source_id,
            query_id,
            source_rank,
            ticker,
            company_name,
            filing_type,
            filing_date,
            section,
            raw_section,
            chunk_id,
            score,
            original_score,
            retrieval_type,
            embedding_model,
            source_document_url,
            excerpt,
            created_at
        FROM rag_sources
        WHERE query_id = $id
        ORDER BY source_rank ASC;
        """;

    command.Parameters.AddWithValue("$id", id);

    using var reader = command.ExecuteReader();

    var sources = new List<RagSourceDto>();

    while (reader.Read())
    {
        sources.Add(new RagSourceDto(
            SourceId: GetInt(reader, "source_id"),
            QueryId: GetInt(reader, "query_id"),
            SourceRank: GetInt(reader, "source_rank"),
            Ticker: GetNullableString(reader, "ticker"),
            CompanyName: GetNullableString(reader, "company_name"),
            FilingType: GetNullableString(reader, "filing_type"),
            FilingDate: GetNullableString(reader, "filing_date"),
            Section: GetNullableString(reader, "section"),
            RawSection: GetNullableString(reader, "raw_section"),
            ChunkId: GetNullableString(reader, "chunk_id"),
            Score: GetNullableDouble(reader, "score"),
            OriginalScore: GetNullableDouble(reader, "original_score"),
            RetrievalType: GetNullableString(reader, "retrieval_type"),
            EmbeddingModel: GetNullableString(reader, "embedding_model"),
            SourceDocumentUrl: GetNullableString(reader, "source_document_url"),
            Excerpt: GetNullableString(reader, "excerpt"),
            CreatedAt: GetNullableString(reader, "created_at")
        ));
    }

    return Results.Ok(sources);
});

app.MapGet("/api/stats/summary", () =>
{
    if (!File.Exists(databasePath))
    {
        return Results.Problem(
            title: "SQLite database not found",
            detail: $"Database path: {databasePath}",
            statusCode: StatusCodes.Status500InternalServerError
        );
    }

    using var connection = OpenConnection(connectionString);

    var companyCount = ExecuteScalarInt(connection, "SELECT COUNT(*) FROM companies;");
    var queryCount = ExecuteScalarInt(connection, "SELECT COUNT(*) FROM rag_queries;");
    var sourceCount = ExecuteScalarInt(connection, "SELECT COUNT(*) FROM rag_sources;");
    var averageScore = ExecuteScalarDouble(connection, "SELECT COALESCE(AVG(avg_score), 0) FROM rag_queries;");
    var lastQueryAt = ExecuteScalarString(connection, "SELECT MAX(created_at) FROM rag_queries;");

    var summary = new StatsSummaryDto(
        CompanyCount: companyCount,
        QueryCount: queryCount,
        SourceCount: sourceCount,
        AverageScore: Math.Round(averageScore, 6),
        LastQueryAt: lastQueryAt
    );

    return Results.Ok(summary);
});

app.Run();


static SqliteConnection OpenConnection(string connectionString)
{
    var connection = new SqliteConnection(connectionString);
    connection.Open();

    return connection;
}


static int ExecuteScalarInt(SqliteConnection connection, string sql)
{
    using var command = connection.CreateCommand();
    command.CommandText = sql;

    var value = command.ExecuteScalar();

    if (value is null || value == DBNull.Value)
    {
        return 0;
    }

    return Convert.ToInt32(value);
}


static double ExecuteScalarDouble(SqliteConnection connection, string sql)
{
    using var command = connection.CreateCommand();
    command.CommandText = sql;

    var value = command.ExecuteScalar();

    if (value is null || value == DBNull.Value)
    {
        return 0;
    }

    return Convert.ToDouble(value);
}


static string? ExecuteScalarString(SqliteConnection connection, string sql)
{
    using var command = connection.CreateCommand();
    command.CommandText = sql;

    var value = command.ExecuteScalar();

    if (value is null || value == DBNull.Value)
    {
        return null;
    }

    return Convert.ToString(value);
}


static string GetString(SqliteDataReader reader, string columnName)
{
    var value = reader[columnName];

    if (value is null || value == DBNull.Value)
    {
        return string.Empty;
    }

    return Convert.ToString(value) ?? string.Empty;
}


static string? GetNullableString(SqliteDataReader reader, string columnName)
{
    var value = reader[columnName];

    if (value is null || value == DBNull.Value)
    {
        return null;
    }

    return Convert.ToString(value);
}


static int GetInt(SqliteDataReader reader, string columnName)
{
    var value = reader[columnName];

    if (value is null || value == DBNull.Value)
    {
        return 0;
    }

    return Convert.ToInt32(value);
}


static double GetDouble(SqliteDataReader reader, string columnName)
{
    var value = reader[columnName];

    if (value is null || value == DBNull.Value)
    {
        return 0;
    }

    return Convert.ToDouble(value);
}


static double? GetNullableDouble(SqliteDataReader reader, string columnName)
{
    var value = reader[columnName];

    if (value is null || value == DBNull.Value)
    {
        return null;
    }

    return Convert.ToDouble(value);
}


record CompanyDto(
    string Ticker,
    string CompanyName,
    string? Exchange,
    string? CreatedAt
);

record QuerySummaryDto(
    int QueryId,
    string? Ticker,
    string QueryText,
    int SourceCount,
    double AvgScore,
    bool UseFoundryLocal,
    string? RetrievalType,
    string? EmbeddingModel,
    string? CreatedAt
);

record QueryDetailDto(
    int QueryId,
    string? Ticker,
    string QueryText,
    string Answer,
    int TopK,
    bool UseFoundryLocal,
    string? RetrievalType,
    string? EmbeddingModel,
    int SourceCount,
    double AvgScore,
    string? CreatedAt
);

record RagSourceDto(
    int SourceId,
    int QueryId,
    int SourceRank,
    string? Ticker,
    string? CompanyName,
    string? FilingType,
    string? FilingDate,
    string? Section,
    string? RawSection,
    string? ChunkId,
    double? Score,
    double? OriginalScore,
    string? RetrievalType,
    string? EmbeddingModel,
    string? SourceDocumentUrl,
    string? Excerpt,
    string? CreatedAt
);

record StatsSummaryDto(
    int CompanyCount,
    int QueryCount,
    int SourceCount,
    double AverageScore,
    string? LastQueryAt
);





