# Deploying the Azure Function

This guide covers deploying the Azure Analysis Services Query Function to Azure.

## Prerequisites

- Completed [Service Principal Setup](setup-service-principal.md)
- .NET 8.0 SDK installed
- Azure CLI installed
- Azure Functions Core Tools v4
- An Azure subscription

## Deployment Options

Choose one of the following deployment methods:

1. [Azure CLI (Recommended)](#option-1-azure-cli-deployment)
2. [Visual Studio Code](#option-2-visual-studio-code)
3. [Visual Studio](#option-3-visual-studio)
4. [GitHub Actions](#option-4-github-actions-cicd)

---

## Option 1: Azure CLI Deployment

### Step 1: Login to Azure

```bash
az login
az account set --subscription "your-subscription-name-or-id"
```

### Step 2: Create Resource Group

```bash
# Set variables
RESOURCE_GROUP="rg-aas-function"
LOCATION="eastus2"
FUNC_APP_NAME="func-aas-query-$RANDOM"
STORAGE_NAME="staasfunc$RANDOM"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### Step 3: Create Storage Account

```bash
az storage account create \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --allow-shared-key-access true \
  --public-network-access Enabled
```

### Step 4: Create Function App

```bash
az functionapp create \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --storage-account $STORAGE_NAME \
  --runtime dotnet-isolated \
  --runtime-version 8 \
  --functions-version 4 \
  --os-type Linux \
  --consumption-plan-location $LOCATION
```

### Step 5: Configure Application Settings

```bash
az functionapp config appsettings set \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    AAS_REGION_HOST="your-region.asazure.windows.net" \
    AAS_SERVER_NAME="your-server-name" \
    AAS_DATABASE="your-database-name" \
    TENANT_ID="your-tenant-id" \
    CLIENT_ID="your-client-id" \
    CLIENT_SECRET="your-client-secret"
```

### Step 6: Deploy the Function

```bash
cd azure-function

# Build and publish
func azure functionapp publish $FUNC_APP_NAME
```

### Step 7: Verify Deployment

```bash
# Get function URL
FUNC_URL=$(az functionapp function show \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --function-name queryAas \
  --query invokeUrlTemplate -o tsv)

# Test the function
curl -X POST "$FUNC_URL" \
  -H "Content-Type: application/json" \
  -d '{"query": "EVALUATE ROW(\"Test\", 1)"}'
```

Expected response:
```json
{
  "rows": [
    {
      "[Test]": 1
    }
  ]
}
```

---

## Option 2: Visual Studio Code

### Step 1: Install Extensions

- Azure Functions extension
- Azure Account extension

### Step 2: Build Project

1. Open `azure-function` folder in VS Code
2. Press `F5` to build and run locally
3. Test locally at `http://localhost:7204/api/query`

### Step 3: Deploy

1. Click Azure icon in sidebar
2. Sign in to Azure
3. Right-click on **Function App** > **Create Function App in Azure**
4. Follow prompts:
   - Name: `func-aas-query-yourname`
   - Runtime: **.NET 8 Isolated**
   - Region: Select your region

5. Right-click the new function app > **Deploy to Function App**
6. Select the `azure-function` folder

### Step 4: Configure Settings

1. Right-click function app > **Application Settings**
2. Add each setting:
   - `AAS_REGION_HOST`
   - `AAS_SERVER_NAME`
   - `AAS_DATABASE`
   - `TENANT_ID`
   - `CLIENT_ID`
   - `CLIENT_SECRET`

---

## Option 3: Visual Studio

### Step 1: Open Solution

1. Open `azure-function.sln` in Visual Studio
2. Right-click project > **Publish**

### Step 2: Configure Publish Profile

1. Select **Azure** > **Next**
2. Select **Azure Function App (Linux)** > **Next**
3. Select or create a Function App
4. Click **Finish**

### Step 3: Publish

1. Click **Publish** button
2. Wait for deployment to complete

### Step 4: Configure Settings

1. In Publish profile, click **Manage Azure App Service settings**
2. Add application settings from service principal setup

---

## Option 4: GitHub Actions CI/CD

### Step 1: Get Publish Profile

```bash
az functionapp deployment list-publishing-profiles \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --xml > publish-profile.xml
```

### Step 2: Add GitHub Secret

1. Go to your GitHub repository
2. Settings > Secrets and variables > Actions
3. New repository secret:
   - Name: `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`
   - Value: Contents of `publish-profile.xml`

### Step 3: Create Workflow

Create `.github/workflows/deploy-function.yml`:

```yaml
name: Deploy Azure Function

on:
  push:
    branches: [ main ]
    paths:
      - 'azure-function/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: '8.0.x'
    
    - name: Build
      run: |
        cd azure-function
        dotnet build --configuration Release
    
    - name: Publish
      run: |
        cd azure-function
        dotnet publish --configuration Release --output ./output
    
    - name: Deploy to Azure
      uses: Azure/functions-action@v1
      with:
        app-name: 'your-function-app-name'
        package: './azure-function/output'
        publish-profile: ${{ secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE }}
```

---

## Post-Deployment Configuration

### Enable Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app func-aas-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app func-aas-insights \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey -o tsv)

# Configure Function App
az functionapp config appsettings set \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY
```

### Configure CORS (Optional)

```bash
az functionapp cors add \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --allowed-origins "https://yourdomain.com"
```

### Enable Authentication (Production)

```bash
# Enable Azure AD authentication
az functionapp auth update \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --enabled true \
  --action LoginWithAzureActiveDirectory
```

---

## Monitoring and Diagnostics

### View Logs

```bash
# Stream logs
az functionapp log tail \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP
```

### Check Function Status

```bash
az functionapp show \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query state
```

### View Metrics in Portal

1. Navigate to Function App in Azure Portal
2. **Monitoring** > **Metrics**
3. View execution count, errors, duration

---

## Troubleshooting

### Common Deployment Issues

**Error: "Storage account does not allow shared key access"**

```bash
az storage account update \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP \
  --allow-shared-key-access true
```

**Error: "Public network access disabled"**

```bash
az storage account update \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP \
  --public-network-access Enabled
```

**Error: "Function runtime is unable to start"**

Check application settings:
```bash
az functionapp config appsettings list \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP
```

### Testing the Deployed Function

Create a test script `test_function.sh`:

```bash
#!/bin/bash

FUNC_URL="https://your-function-app.azurewebsites.net/api/query"

# Test 1: Simple query
echo "Test 1: Simple query"
curl -X POST "$FUNC_URL" \
  -H "Content-Type: application/json" \
  -d '{"query": "EVALUATE ROW(\"Test\", 1)"}'

echo -e "\n\nTest 2: Product query"
curl -X POST "$FUNC_URL" \
  -H "Content-Type: application/json" \
  -d '{"query": "EVALUATE TOPN(5, '\''Product'\'')"}'
```

---

## Production Checklist

Before going to production:

- [ ] Enable Azure AD authentication on Function App
- [ ] Store secrets in Azure Key Vault
- [ ] Enable Application Insights
- [ ] Configure alerting and monitoring
- [ ] Set up CORS restrictions
- [ ] Configure scaling limits
- [ ] Enable diagnostic logging
- [ ] Test failover scenarios
- [ ] Document runbook procedures
- [ ] Set up backup and disaster recovery

---

## Cost Optimization

### Consumption Plan

- Pay only for execution time
- Automatic scaling
- Best for variable workloads

### Premium Plan

- Pre-warmed instances
- VNet connectivity
- Longer execution times
- Better for production workloads

### Dedicated Plan

- Predictable pricing
- Full control over resources
- Best for high-volume scenarios

---

## Updating the Function

### Quick Update

```bash
cd azure-function
func azure functionapp publish $FUNC_APP_NAME
```

### Zero-Downtime Deployment

Use deployment slots:

```bash
# Create staging slot
az functionapp deployment slot create \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --slot staging

# Deploy to staging
func azure functionapp publish $FUNC_APP_NAME --slot staging

# Swap to production
az functionapp deployment slot swap \
  --name $FUNC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --slot staging
```

---

## Next Steps

1. [Deploy MCP Server](deploy-mcp-server.md)
2. Update MCP Server configuration with Function URL
3. Test end-to-end integration

## Additional Resources

- [Azure Functions Documentation](https://learn.microsoft.com/azure/azure-functions/)
- [Azure CLI Reference](https://learn.microsoft.com/cli/azure/functionapp)
- [Function App Best Practices](https://learn.microsoft.com/azure/azure-functions/functions-best-practices)
