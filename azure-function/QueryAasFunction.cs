
using System.Data;
using System.Net;
using System.Text.Json;
using Microsoft.AnalysisServices.AdomdClient;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Identity.Client;

public class QueryAasFunction
{
    private readonly string _regionHost = Environment.GetEnvironmentVariable("AAS_REGION_HOST")!;
    private readonly string _serverName = Environment.GetEnvironmentVariable("AAS_SERVER_NAME")!;
    private readonly string _database   = Environment.GetEnvironmentVariable("AAS_DATABASE")!;
    private readonly string _tenantId   = Environment.GetEnvironmentVariable("TENANT_ID")!;
    private readonly string _clientId   = Environment.GetEnvironmentVariable("CLIENT_ID")!;
    private readonly string _clientSecret = Environment.GetEnvironmentVariable("CLIENT_SECRET")!;

    // Azure Analysis Services connection string
    private string ConnectionString => $"Data Source=asazure://{_regionHost}/{_serverName};Initial Catalog={_database};";

    [Function("queryAas")]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Anonymous, "post", Route = "query")] HttpRequestData req)
    {
        var body = await new StreamReader(req.Body).ReadToEndAsync();
        QueryRequest? request;
        try
        {
            request = JsonSerializer.Deserialize<QueryRequest>(body,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }
        catch
        {
            var bad = req.CreateResponse(HttpStatusCode.BadRequest);
            await bad.WriteStringAsync("Invalid JSON payload.");
            return bad;
        }

        if (request is null || string.IsNullOrWhiteSpace(request.Query))
        {
            var bad = req.CreateResponse(HttpStatusCode.BadRequest);
            await bad.WriteStringAsync("Request must include 'query'.");
            return bad;
        }

        var queryType = (request.QueryType ?? "DAX").Trim().ToUpperInvariant();
        if (queryType is not ("DAX" or "MDX"))
        {
            var bad = req.CreateResponse(HttpStatusCode.BadRequest);
            await bad.WriteStringAsync("queryType must be 'DAX' or 'MDX'.");
            return bad;
        }

        try
        {
            var token = await AcquireAasAccessTokenAsync();
            var rows = await ExecuteQueryAsync(token, request.Query);

            var ok = req.CreateResponse(HttpStatusCode.OK);
            ok.Headers.Add("Content-Type", "application/json");
            await ok.WriteStringAsync(JsonSerializer.Serialize(new { rows }));
            return ok;
        }
        catch (Exception ex)
        {
            var err = req.CreateResponse(HttpStatusCode.BadRequest);
            err.Headers.Add("Content-Type", "application/json");
            await err.WriteStringAsync(JsonSerializer.Serialize(new { error = ex.Message }));
            return err;
        }
    }

    private async Task<string> AcquireAasAccessTokenAsync()
    {
        // For Azure Analysis Services, the resource is https://*.asazure.windows.net
        var scope = "https://*.asazure.windows.net/.default";

        var app = ConfidentialClientApplicationBuilder
            .Create(_clientId)
            .WithClientSecret(_clientSecret)
            .WithAuthority($"https://login.microsoftonline.com/{_tenantId}")
            .Build();

        var result = await app.AcquireTokenForClient(new[] { scope }).ExecuteAsync();
        return result.AccessToken;
    }

    private Task<List<Dictionary<string, object?>>> ExecuteQueryAsync(string accessToken, string query)
    {
        return Task.Run(() =>
        {
            using var conn = new AdomdConnection(ConnectionString);
            
            // Set the access token for authentication (expires in 1 hour)
            conn.AccessToken = new Microsoft.AnalysisServices.AccessToken(accessToken, DateTimeOffset.UtcNow.AddHours(1), null);
            
            conn.Open();

            using var cmd = new AdomdCommand(query, conn);
            using var reader = cmd.ExecuteReader();

            var rows = new List<Dictionary<string, object?>>();
            
            while (reader.Read())
            {
                var row = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
                for (int i = 0; i < reader.FieldCount; i++)
                {
                    var fieldName = reader.GetName(i);
                    var value = reader.IsDBNull(i) ? null : reader.GetValue(i);
                    row[fieldName] = value;
                }
                rows.Add(row);
            }

            return rows;
        });
    }

    public sealed class QueryRequest
    {
        public string? QueryType { get; set; }  // "DAX" or "MDX"
        public string? Query { get; set; }
    }
}
