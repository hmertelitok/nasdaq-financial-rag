using NasdaqFinancialRag.Api.Models;
using NasdaqFinancialRag.Api.Data;
using NasdaqFinancialRag.Api.Options;
using NasdaqFinancialRag.Api.Repositories;
using NasdaqFinancialRag.Api.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenApi();

builder.Services.Configure<PostgresOptions>(
    builder.Configuration.GetSection(PostgresOptions.SectionName)
);

builder.Services.Configure<PgvectorSearchServiceOptions>(
    builder.Configuration.GetSection(
        PgvectorSearchServiceOptions.SectionName
    )
);

builder.Services.AddSingleton<PostgresConnectionFactory>();
builder.Services.AddScoped<CompanyRepository>();
builder.Services.AddScoped<PostgresStatsRepository>();
builder.Services.AddScoped<PostgresFilingRepository>();
builder.Services.AddScoped<PostgresChunkRepository>();

builder.Services.AddHttpClient<PgvectorSearchClient>(
    (serviceProvider, client) =>
    {
        var options = serviceProvider
            .GetRequiredService<
                Microsoft.Extensions.Options.IOptions<
                    PgvectorSearchServiceOptions
                >
            >()
            .Value;

        client.BaseAddress = new Uri(
            options.BaseUrl.TrimEnd('/') + "/"
        );

        client.Timeout = TimeSpan.FromSeconds(
            Math.Clamp(options.TimeoutSeconds, 10, 300)
        );
    }
);

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

// Local geliştirme için HTTPS yönlendirmesini kapalı tutuyoruz.
// app.UseHttpsRedirection();

app.MapGet("/", () =>
{
    return Results.Ok(new
    {
        name = "NASDAQ Financial RAG API",
        status = "running",
        databaseType = "PostgreSQL (pgvector)",
        endpoints = new[]
        {
            "GET /api/health",
            "GET /api/postgres/companies",
            "GET /api/postgres/stats/summary",
            "GET /api/postgres/filings",
            "GET /api/postgres/chunks",
            "GET /api/postgres/search",
            "POST /api/rag/ask"
        }
    });
});

app.MapGet("/api/health", () =>
{
    return Results.Ok(new
    {
        status = "healthy",
        database = "PostgreSQL",
        postgresCompaniesEndpoint = "/api/postgres/companies",
        postgresStatsEndpoint = "/api/postgres/stats/summary",
        postgresFilingsEndpoint = "/api/postgres/filings",
        postgresChunksEndpoint = "/api/postgres/chunks",
        postgresSearchEndpoint = "/api/postgres/search",
        ragAnswerEndpoint = "/api/rag/ask",
        checkedAt = DateTime.UtcNow
    });
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

app.MapGet(
    "/api/postgres/search",
    async (
        string query,
        PgvectorSearchClient searchClient,
        string? ticker,
        string? section,
        int? limit,
        CancellationToken cancellationToken
    ) =>
    {
        if (string.IsNullOrWhiteSpace(query))
        {
            return Results.BadRequest(new { message = "query parametresi zorunludur." });
        }

        var safeLimit = Math.Clamp(limit ?? 5, 1, 20);

        try
        {
            var searchResult = await searchClient.SearchAsync(
                query: query,
                ticker: ticker,
                section: section,
                limit: safeLimit,
                cancellationToken: cancellationToken
            );

            return Results.Ok(searchResult);
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return Results.Problem(
                title: "Semantic search timeout",
                detail: "Python pgvector search servisi zaman aşımına uğradı.",
                statusCode: StatusCodes.Status504GatewayTimeout
            );
        }
        catch (HttpRequestException exception)
        {
            return Results.Problem(
                title: "Python search service unavailable",
                detail: exception.Message,
                statusCode: StatusCodes.Status502BadGateway
            );
        }
    }
)
.WithName("GetPostgresSemanticSearch")
.WithTags("PostgreSQL");

app.MapPost(
    "/api/rag/ask",
    async (
        PgvectorAskRequestDto request,
        PgvectorSearchClient searchClient,
        CancellationToken cancellationToken
    ) =>
    {
        if (string.IsNullOrWhiteSpace(request.Query))
        {
            return Results.BadRequest(new { message = "query alanı zorunludur." });
        }

        var normalizedRequest = request with
        {
            Query = request.Query.Trim(),
            Ticker = string.IsNullOrWhiteSpace(request.Ticker) ? null : request.Ticker.Trim().ToUpperInvariant(),
            Section = string.IsNullOrWhiteSpace(request.Section) ? null : request.Section.Trim(),
            TopK = Math.Clamp(request.TopK, 1, 20),
            ModelAlias = string.IsNullOrWhiteSpace(request.ModelAlias) ? "qwen2.5-7b" : request.ModelAlias.Trim()
        };

        try
        {
            var answerResult = await searchClient.AskAsync(
                normalizedRequest,
                cancellationToken
            );

            return Results.Ok(answerResult);
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return Results.Problem(
                title: "RAG answer timeout",
                detail: "Python RAG cevap servisi zaman aşımına uğradı.",
                statusCode: StatusCodes.Status504GatewayTimeout
            );
        }
        catch (HttpRequestException exception)
        {
            return Results.Problem(
                title: "Python RAG service unavailable",
                detail: exception.Message,
                statusCode: StatusCodes.Status502BadGateway
            );
        }
    }
)
.WithName("PostRagAnswer")
.WithTags("RAG");

app.Run();