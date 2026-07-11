using System.Globalization;
using System.Net.Http.Json;
using Microsoft.AspNetCore.WebUtilities;
using NasdaqFinancialRag.Api.Models;

namespace NasdaqFinancialRag.Api.Services;

public sealed class PgvectorSearchClient
{
    private readonly HttpClient _httpClient;

    public PgvectorSearchClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public async Task<PgvectorSearchResponseDto> SearchAsync(
        string query,
        string? ticker = null,
        string? section = null,
        int limit = 5,
        CancellationToken cancellationToken = default
    )
    {
        if (string.IsNullOrWhiteSpace(query))
        {
            throw new ArgumentException(
                "Semantic search sorgusu boş olamaz.",
                nameof(query)
            );
        }

        var queryParameters = new Dictionary<string, string?>
        {
            ["query"] = query.Trim(),
            ["limit"] = limit.ToString(CultureInfo.InvariantCulture)
        };

        if (!string.IsNullOrWhiteSpace(ticker))
        {
            queryParameters["ticker"] = ticker.Trim().ToUpperInvariant();
        }

        if (!string.IsNullOrWhiteSpace(section))
        {
            queryParameters["section"] = section.Trim();
        }

        var requestUri = QueryHelpers.AddQueryString(
            "search",
            queryParameters
        );

        using var response = await _httpClient.GetAsync(
            requestUri,
            cancellationToken
        );

        if (!response.IsSuccessStatusCode)
        {
            var responseBody = await response.Content.ReadAsStringAsync(
                cancellationToken
            );

            throw new HttpRequestException(
                $"Python pgvector search servisi başarısız oldu. " +
                $"Status: {(int)response.StatusCode}. Body: {responseBody}",
                inner: null,
                statusCode: response.StatusCode
            );
        }

        var searchResponse =
            await response.Content.ReadFromJsonAsync<PgvectorSearchResponseDto>(
                cancellationToken: cancellationToken
            );

        return searchResponse
            ?? throw new InvalidOperationException(
                "Python pgvector search servisi boş yanıt döndürdü."
            );
    }

    public async Task<PgvectorAskResponseDto> AskAsync(
        PgvectorAskRequestDto request,
        CancellationToken cancellationToken = default
    )
    {
        if (string.IsNullOrWhiteSpace(request.Query))
        {
            throw new ArgumentException(
                "RAG sorusu boş olamaz.",
                nameof(request)
            );
        }

        var normalizedRequest = request with
        {
            Query = request.Query.Trim(),
            Ticker = string.IsNullOrWhiteSpace(request.Ticker)
                ? null
                : request.Ticker.Trim().ToUpperInvariant(),
            Section = string.IsNullOrWhiteSpace(request.Section)
                ? null
                : request.Section.Trim(),
            TopK = Math.Clamp(request.TopK, 1, 20),
            ModelAlias = string.IsNullOrWhiteSpace(request.ModelAlias)
                ? "qwen2.5-7b"
                : request.ModelAlias.Trim()
        };

        using var response = await _httpClient.PostAsJsonAsync(
            "ask",
            normalizedRequest,
            cancellationToken
        );

        if (!response.IsSuccessStatusCode)
        {
            var responseBody = await response.Content.ReadAsStringAsync(
                cancellationToken
            );

            throw new HttpRequestException(
                $"Python RAG cevap servisi başarısız oldu. " +
                $"Status: {(int)response.StatusCode}. Body: {responseBody}",
                inner: null,
                statusCode: response.StatusCode
            );
        }

        var askResponse =
            await response.Content.ReadFromJsonAsync<PgvectorAskResponseDto>(
                cancellationToken: cancellationToken
            );

        return askResponse
            ?? throw new InvalidOperationException(
                "Python RAG cevap servisi boş yanıt döndürdü."
            );
    }
}
