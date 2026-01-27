# Complete Setup Guide - Azure Analysis Services MCP Agent

This guide provides step-by-step instructions to set up the Azure Analysis Services MCP Agent from scratch. Follow each section in order.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Azure Environment Setup](#phase-1-azure-environment-setup)
3. [Phase 2: Deploy Azure Function](#phase-2-deploy-azure-function)
4. [Phase 3: Configure MCP Server](#phase-3-configure-mcp-server)
5. [Phase 4: Test the Solution](#phase-4-test-the-solution)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

Install the following on your local machine:

#### 1. **Azure CLI**
```bash
# Download and install from:
# https://learn.microsoft.com/cli/azure/install-azure-cli

# Verify installation:
az --version
```

#### 2. **.NET 8.0 SDK**
```bash
# Download and install from:
# https://dotnet.microsoft.com/download/dotnet/8.0

# Verify installation:
dotnet --version
```

#### 3. **Azure Functions Core Tools v4**
```bash
# Download and install from:
# https://learn.microsoft.com/azure/azure-functions/functions-run-local

# Verify installation:
func --version
```

#### 4. **Python 3.10 or newer**
```bash
# Download and install from:
# https://www.python.org/downloads/

# Verify installation:
python --version
```

#### 5. **Git** (optional, for cloning)
```bash
# Download from: https://git-scm.com/downloads
git --version
```

### Required Azure Resources

You must have:

- ✅ **Azure subscription** with Contributor access
- ✅ **Azure Analysis Services** instance already deployed
- ✅ **Tabular model** deployed to AAS (e.g., AdventureWorks)
- ✅ **Azure OpenAI** resource (for the AI agent)

### Required Information

Before starting, gather this information:

```plaintext
Azure Analysis Services:
- Region Host: ________________ (e.g., aspaaseastus2.asazure.windows.net)
- Server Name: ________________ (e.g., myaasserver)
- Database/Model: _____________ (e.g., adventureworks)

Azure Subscription:
- Subscription ID: ____________
- Resource Group: _____________ (existing or new)
- Location: ___________________ (e.g., eastus)

Azure OpenAI:
- API Key: ____________________
- Endpoint: ___________________
```

---

## Phase 1: Azure Environment Setup

### Step 1.1: Login to Azure

```bash
# Login to your Azure account
az login

# Set your subscription (if you have multiple)
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Verify you're in the correct subscription
az account show --query "{Name:name, ID:id, TenantID:tenantId}" -o table
```

### Step 1.2: Create a Resource Group (or use existing)

```bash
# Create a new resource group
az group create \
  --name rg-aas-mcp-agent \
  --location eastus

# Or list existing resource groups
az group list --query "[].{Name:name, Location:location}" -o table
```

### Step 1.3: Create Azure Function App

Create a storage account and Function App:

```bash
# Variables (customize these)
RESOURCE_GROUP="rg-aas-mcp-agent"
LOCATION="eastus"
STORAGE_NAME="staasmcp$(date +%s)"  # Must be globally unique, lowercase, no hyphens
FUNCTION_NAME="func-aas-query"      # Must be globally unique

# Create storage account
az storage account create \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --allow-blob-public-access false

# Create Function App (FlexConsumption)
az functionapp create \
  --name $FUNCTION_NAME \
  --resource-group $RESOURCE_GROUP \
  --storage-account $STORAGE_NAME \
  --runtime dotnet-isolated \
  --runtime-version 8 \
  --functions-version 4 \
  --os-type Linux

# Enable managed identity (RECOMMENDED)
az functionapp identity assign \
  --name $FUNCTION_NAME \
  --resource-group $RESOURCE_GROUP

# Save the principal ID (you'll need this)
PRINCIPAL_ID=$(az functionapp identity show \
  --name $FUNCTION_NAME \
  --resource-group $RESOURCE_GROUP \
  --query principalId -o tsv)

echo "Function App Managed Identity Principal ID: $PRINCIPAL_ID"
```

**⚠️ Important:** Save the `PRINCIPAL_ID` - you'll need it in Step 1.4!

### Step 1.4: Configure Azure Analysis Services Access

Grant the Function App's managed identity access to Azure Analysis Services.

**Option A: Using Azure Portal (Easier)**

1. Open **SQL Server Management Studio (SSMS)** or **Azure Data Studio**
2. Connect to your Azure Analysis Services:
   - Server: `asazure://your-region.asazure.windows.net/your-server`
   - Authentication: **Azure Active Directory - Universal with MFA**
3. Right-click on the database → **Roles** → **New Role**
4. Role name: `FunctionAppReader`
5. Permissions: Select **Read**
6. Members → Add:
   - Click **Add**
   - Enter: `func-aas-query` (your Function App name)
   - Select the managed identity from the list
7. Click **OK**

**Option B: Using PowerShell (Advanced)**

```powershell
# Install required module
Install-Module -Name Az.AnalysisServices -Force

# Connect to AAS
$aasServer = "asazure://your-region.asazure.windows.net/your-server"
$database = "your-database"

# Add managed identity to admin role
Add-AzAnalysisServicesAccount -RolloutEnvironment "your-region.asazure.windows.net"

# Use the PRINCIPAL_ID from Step 1.3
$principalId = "your-principal-id-from-step-1.3"

# Note: This requires AAS admin permissions
# You may need to use SSMS instead for easier setup
```

**Verification:**

```bash
# Check that managed identity is enabled
az functionapp identity show \
  --name $FUNCTION_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "{PrincipalId:principalId, Type:type}" -o table
```

### Step 1.5: Configure Function App Settings

Set environment variables in the Function App:

```bash
# Set Azure Analysis Services configuration
az functionapp config appsettings set \
  --name $FUNCTION_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    AAS_REGION_HOST="aspaaseastus2.asazure.windows.net" \
    AAS_SERVER_NAME="your-server-name" \
    AAS_DATABASE="adventureworks"

# For Managed Identity (RECOMMENDED - no secrets!)
az functionapp config appsettings set \
  --name $FUNCTION_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    USE_MANAGED_IDENTITY="true"
```

**Alternative: Using Service Principal (if you can't use Managed Identity)**

If your organization requires service principal instead:

<details>
<summary>Click to expand Service Principal setup</summary>

```bash
# Create service principal
SP_NAME="sp-aas-mcp-agent"

SP_OUTPUT=$(az ad sp create-for-rbac \
  --name $SP_NAME \
  --role Reader \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID)

# Extract values
TENANT_ID=$(echo $SP_OUTPUT | jq -r '.tenant')
CLIENT_ID=$(echo $SP_OUTPUT | jq -r '.appId')
CLIENT_SECRET=$(echo $SP_OUTPUT | jq -r '.password')

echo "Tenant ID: $TENANT_ID"
echo "Client ID: $CLIENT_ID"
echo "Client Secret: $CLIENT_SECRET"

# Configure Function App with service principal
az functionapp config appsettings set \
  --name $FUNCTION_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    TENANT_ID="$TENANT_ID" \
    CLIENT_ID="$CLIENT_ID" \
    CLIENT_SECRET="$CLIENT_SECRET"

# Then grant this service principal access to AAS using SSMS (similar to Step 1.4)
```

</details>

**Verify settings:**

```bash
az functionapp config appsettings list \
  --name $FUNCTION_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "[?name=='AAS_REGION_HOST' || name=='AAS_SERVER_NAME' || name=='AAS_DATABASE'].{Name:name, Value:value}" -o table
```

---

## Phase 2: Deploy Azure Function

### Step 2.1: Get the Code

```bash
# Clone the repository (or download ZIP)
git clone https://github.com/your-org/azure-aas-mcp-agent.git
cd azure-aas-mcp-agent

# Or if you have a ZIP file:
# unzip azure-aas-mcp-agent.zip
# cd azure-aas-mcp-agent
```

### Step 2.2: Build the Function

```bash
# Navigate to the Azure Function folder
cd azure-function

# Restore dependencies
dotnet restore

# Build the project
dotnet build --configuration Release
```

**Expected output:**
```
Build succeeded.
    0 Warning(s)
    0 Error(s)
```

### Step 2.3: Deploy to Azure

```bash
# Deploy the function
func azure functionapp publish $FUNCTION_NAME

# Or if func is not in PATH, use full path:
# "C:\Program Files\Microsoft\Azure Functions Core Tools\func.exe" azure functionapp publish $FUNCTION_NAME
```

**Expected output:**
```
Getting site publishing info...
Creating archive for current directory...
Uploading 2.34 MB [###############################################]
Upload completed successfully.
Deployment successful.
Functions in func-aas-query:
    queryAas - [httpTrigger]
        Invoke url: https://func-aas-query.azurewebsites.net/api/query
```

**⚠️ Important:** Save the `Invoke url` - you'll need it in Phase 3!

### Step 2.4: Verify Deployment

```bash
# Check function status
az functionapp show \
  --name $FUNCTION_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "{Name:name, State:state, DefaultHostName:defaultHostName}" -o table

# Test the function endpoint
FUNCTION_URL="https://$FUNCTION_NAME.azurewebsites.net/api/query"

curl -X POST $FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{"query": "EVALUATE TOPN(5, '\''Customer'\'')"}'
```

**Expected response:**
```json
{
  "rows": [
    {"CustomerKey": 1, "FirstName": "Jon", "LastName": "Yang"},
    {"CustomerKey": 2, "FirstName": "Eugene", "LastName": "Huang"},
    ...
  ]
}
```

**If you get an error**, see [Troubleshooting](#troubleshooting) section.

---

## Phase 3: Configure MCP Server

### Step 3.1: Set Up Python Environment

```bash
# Navigate to MCP server folder
cd ../mcp-server

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed mcp-1.0.0 httpx-0.27.0 openai-1.0.0
```

### Step 3.2: Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your values
# On Windows: notepad .env
# On macOS/Linux: nano .env
```

**Edit `.env` and set these values:**

```bash
# Azure Function URL (from Step 2.3)
AZURE_FUNCTION_URL=https://func-aas-query.azurewebsites.net/api/query

# Azure OpenAI credentials
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2024-05-01-preview
```

Save and close the file.

### Step 3.3: Test MCP Server

Test that the MCP server can communicate with the Azure Function:

```bash
# Run the MCP server in test mode
python server.py
```

**Expected output:**
```
MCP Server initialized
Tools available: query_analysis_services
Listening on stdio...
```

Press `Ctrl+C` to stop.

---

## Phase 4: Test the Solution

### Step 4.1: Test with Simple Queries

Create a test script:

```bash
# Create test_query.py
cat > test_query.py << 'EOF'
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("AZURE_FUNCTION_URL")

# Test query
response = httpx.post(
    url,
    json={"query": "EVALUATE TOPN(10, 'Customer')"},
    timeout=30.0
)

print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
EOF

# Run the test
python test_query.py
```

**Expected output:**
```
Status: 200
{
  "rows": [
    {"CustomerKey": 1, "FirstName": "Jon", ...},
    ...
  ]
}
```

### Step 4.2: Test with AI Agent

Run the AI agent:

```bash
python simple_agent.py
```

**Example conversation:**
```
You: How many customers do we have?
Agent: [Querying Analysis Services...]
Agent: According to the data, there are 18,484 customers in the database.

You: Show me the top 5 products by sales amount
Agent: [Querying Analysis Services...]
Agent: Here are the top 5 products by sales:
1. Mountain-200 Black, 46 - $1,234,567
2. Road-250 Red, 48 - $987,654
...
```

### Step 4.3: Verify End-to-End Flow

Test the complete flow:

```bash
# 1. Azure Function is running
az functionapp show --name $FUNCTION_NAME --resource-group $RESOURCE_GROUP --query "state" -o tsv

# 2. MCP Server can connect to Function
python -c "
import httpx
import os
from dotenv import load_dotenv
load_dotenv()
r = httpx.post(os.getenv('AZURE_FUNCTION_URL'), json={'query': 'EVALUATE {1}'}, timeout=10)
print('✅ Connection successful!' if r.status_code == 200 else f'❌ Failed: {r.status_code}')
"

# 3. AI Agent can use MCP Server
# Run simple_agent.py and ask: "What tables are available?"
```

---

## Troubleshooting

### Issue: "Authentication failed" from Azure Function

**Symptoms:**
```json
{"error": "Authentication failed"}
```

**Solutions:**

1. **Verify Managed Identity is enabled:**
   ```bash
   az functionapp identity show --name $FUNCTION_NAME --resource-group $RESOURCE_GROUP
   ```

2. **Check AAS permissions:**
   - Connect to AAS with SSMS
   - Verify the Function App managed identity is in a role with Read permissions

3. **Check environment variables:**
   ```bash
   az functionapp config appsettings list --name $FUNCTION_NAME --resource-group $RESOURCE_GROUP
   ```

### Issue: "Connection timeout" or "Cannot connect to AAS"

**Solutions:**

1. **Check AAS firewall settings:**
   - Azure Portal → Analysis Services → Firewall
   - Ensure "Allow access from Azure services" is enabled
   - Or add the Function App's outbound IP addresses

2. **Verify AAS server name:**
   ```bash
   # Should be just the server name, not the full URL
   # ✅ Correct: myserver
   # ❌ Wrong: asazure://region.asazure.windows.net/myserver
   ```

### Issue: "Function deployment failed"

**Solutions:**

1. **Check .NET version:**
   ```bash
   dotnet --version  # Should be 8.x
   ```

2. **Verify Function App runtime:**
   ```bash
   az functionapp config show --name $FUNCTION_NAME --resource-group $RESOURCE_GROUP --query "linuxFxVersion"
   ```

3. **Check build errors:**
   ```bash
   cd azure-function
   dotnet build --configuration Release -v detailed
   ```

### Issue: "Module not found" in Python

**Solutions:**

```bash
# Ensure virtual environment is activated
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify installations
pip list
```

### Issue: "OpenAI API key invalid"

**Solutions:**

1. **Verify .env file:**
   ```bash
   cat .env  # Check AZURE_OPENAI_API_KEY is set
   ```

2. **Test OpenAI connection:**
   ```python
   import os
   from dotenv import load_dotenv
   load_dotenv()
   print(f"API Key: {os.getenv('AZURE_OPENAI_API_KEY')[:10]}...")
   ```

### Issue: Function returns empty results

**Solutions:**

1. **Verify DAX query syntax:**
   ```bash
   # Test query directly
   curl -X POST https://your-function.azurewebsites.net/api/query \
     -H "Content-Type: application/json" \
     -d '{"query": "EVALUATE TOPN(1, INFO.TABLES())"}'
   ```

2. **Check AAS model has data:**
   - Connect with SSMS
   - Run: `EVALUATE TOPN(10, 'YourTable')`

---

## Getting Help

- **Azure Function Logs:**
  ```bash
  az functionapp log tail --name $FUNCTION_NAME --resource-group $RESOURCE_GROUP
  ```

- **Function App Diagnostics:**
  - Azure Portal → Function App → Diagnose and solve problems

- **AAS Documentation:**
  - [Azure Analysis Services Overview](https://learn.microsoft.com/azure/analysis-services/)

---

## Next Steps

- ✅ **Phase 1 Complete**: Manual setup working
- ⏭️ **Phase 2**: Automate with Terraform/Bicep (coming soon)

Once everything is working, you can:
- Customize the AI agent prompts in `simple_agent.py`
- Add more MCP tools in `server.py`
- Set up CI/CD for automatic deployments
- Configure monitoring and alerts

---

## Security Best Practices

- ✅ Always use **Managed Identity** instead of service principals when possible
- ✅ Store **secrets in Azure Key Vault**, not in environment variables
- ✅ Enable **Application Insights** for monitoring
- ✅ Configure **firewall rules** on AAS to restrict access
- ✅ Use **RBAC** to limit who can manage the Function App
- ✅ Enable **HTTPS only** on the Function App
- ✅ Regularly **rotate credentials** if using service principals

---

**Questions or issues?** Open an issue in the GitHub repository or contact your Azure administrator.
