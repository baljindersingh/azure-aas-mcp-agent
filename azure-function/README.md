# Azure Function - Analysis Services Query API

This Azure Function provides a secure HTTP endpoint for querying Azure Analysis Services using DAX or MDX queries.

## Features

- ✅ OAuth2 authentication with Azure AD service principal
- ✅ ADOMD.NET for native Analysis Services connectivity
- ✅ Supports both DAX and MDX queries
- ✅ JSON request/response format
- ✅ Automatic token management and caching
- ✅ Application Insights integration

## Local Development

### Prerequisites

- .NET 8.0 SDK
- Azure Functions Core Tools v4
- Azure Analysis Services instance
- Azure AD service principal with Analysis Services access

### Setup

1. **Restore NuGet packages**:
   ```bash
   dotnet restore
   ```

2. **Configure local settings**:
   ```bash
   cp local.settings.json.example local.settings.json
   ```
   
   Edit `local.settings.json` and fill in your values:
   - `AAS_REGION_HOST`: Your AAS region (e.g., `aspaaseastus2.asazure.windows.net`)
   - `AAS_SERVER_NAME`: Your AAS server name
   - `AAS_DATABASE`: Your database/model name
   - `TENANT_ID`: Your Azure AD tenant ID
   - `CLIENT_ID`: Service principal application ID
   - `CLIENT_SECRET`: Service principal secret

3. **Build the project**:
   ```bash
   dotnet build
   ```

4. **Run locally**:
   ```bash
   func start
   ```

The function will be available at: `http://localhost:7204/api/query`

### Testing Locally

```bash
curl -X POST http://localhost:7204/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "queryType": "DAX",
    "query": "EVALUATE TOPN(5, '\''Product'\'')"
  }'
```

## Deployment

See [Deploy Azure Function Guide](../docs/deploy-azure-function.md) for detailed deployment instructions.

### Quick Deploy

```bash
# Login to Azure
az login

# Create resource group
az group create --name rg-aas-function --location eastus2

# Create storage account
az storage account create \
  --name staasfunc$(date +%s) \
  --resource-group rg-aas-function \
  --location eastus2 \
  --sku Standard_LRS

# Create function app
az functionapp create \
  --name func-aas-query-$(date +%s) \
  --resource-group rg-aas-function \
  --storage-account staasfunc \
  --runtime dotnet-isolated \
  --runtime-version 8 \
  --functions-version 4 \
  --os-type Linux

# Deploy the function
func azure functionapp publish func-aas-query-yourname
```

### Configure Application Settings

After deployment, set the required environment variables:

```bash
az functionapp config appsettings set \
  --name func-aas-query-yourname \
  --resource-group rg-aas-function \
  --settings \
    AAS_REGION_HOST="your-region.asazure.windows.net" \
    AAS_SERVER_NAME="your-server" \
    AAS_DATABASE="your-database" \
    TENANT_ID="your-tenant-id" \
    CLIENT_ID="your-client-id" \
    CLIENT_SECRET="your-client-secret"
```

## API Reference

### POST /api/query

Execute a DAX or MDX query against Azure Analysis Services.

**Request Body**:
```json
{
  "queryType": "DAX",  // Optional: "DAX" or "MDX", defaults to "DAX"
  "query": "EVALUATE TOPN(10, 'Product')"
}
```

**Success Response (200)**:
```json
{
  "rows": [
    {
      "Product[Product Id]": 1,
      "Product[Product Name]": "Product A",
      ...
    },
    ...
  ]
}
```

**Error Response (400)**:
```json
{
  "error": "Error message here"
}
```

## Architecture

```
HTTP POST Request
    ↓
QueryAasFunction
    ↓
AcquireAasAccessTokenAsync() → MSAL → Azure AD
    ↓
ExecuteQueryAsync()
    ↓
AdomdConnection (with OAuth token)
    ↓
Azure Analysis Services
    ↓
Return JSON Results
```

## Security Considerations

- **Authorization Level**: Currently set to `Anonymous` for testing. For production, use `Function` level and secure with API keys or Azure AD authentication.
- **Service Principal**: Ensure the service principal has minimal required permissions
- **Secrets**: Use Azure Key Vault references for `CLIENT_SECRET` in production
- **Network**: Consider VNet integration and private endpoints for production
- **Monitoring**: Application Insights is enabled for request tracking and diagnostics

## Troubleshooting

### Common Errors

**"Unauthorized" or "Access Denied"**
- Verify service principal is added as Analysis Services administrator
- Check the format: `app:{CLIENT_ID}@{TENANT_ID}`

**"Connection timeout"**
- Check Analysis Services firewall settings
- Ensure "Allow access from Azure services" is enabled

**"Invalid query syntax"**
- Verify DAX/MDX syntax is correct
- Check table and column names match your model

**"Environment variable not set"**
- Ensure all required settings are configured in Function App settings
- For local development, check `local.settings.json`

### Enable Verbose Logging

Update `host.json`:
```json
{
  "version": "2.0",
  "logging": {
    "logLevel": {
      "default": "Information",
      "Function": "Information"
    }
  }
}
```

## Performance Optimization

- **Token Caching**: MSAL automatically caches access tokens
- **Connection Pooling**: ADOMD.NET manages connection pooling automatically
- **Query Optimization**: Use appropriate DAX/MDX query patterns
- **Function App Scaling**: Configure appropriate plan (Consumption, Premium, or Dedicated)

## Dependencies

- `Microsoft.Azure.Functions.Worker` - Azure Functions isolated worker
- `Microsoft.AnalysisServices.AdomdClient.NetCore` - Analysis Services client library
- `Microsoft.Identity.Client` - MSAL for OAuth2 authentication
- `Microsoft.ApplicationInsights.WorkerService` - Application monitoring

## Additional Resources

- [Azure Functions Documentation](https://learn.microsoft.com/azure/azure-functions/)
- [ADOMD.NET Documentation](https://learn.microsoft.com/analysis-services/adomd/developing-with-adomd-net)
- [DAX Reference](https://learn.microsoft.com/dax/)
- [Azure Analysis Services](https://learn.microsoft.com/azure/analysis-services/)
