# Setting Up Azure Service Principal

This guide walks you through creating and configuring an Azure AD service principal for accessing Azure Analysis Services.

## Prerequisites

- Azure subscription with appropriate permissions
- Azure CLI installed
- Access to Azure Analysis Services instance

## Step 1: Create Service Principal

### Using Azure CLI

```bash
# Login to Azure
az login

# Create service principal
az ad sp create-for-rbac --name "sp-aas-query" --role Contributor --scopes /subscriptions/{subscription-id}
```

**Save the output** - you'll need these values:
```json
{
  "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "displayName": "sp-aas-query",
  "password": "your-client-secret",
  "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### Using Azure Portal

1. Navigate to **Azure Active Directory** > **App registrations** > **New registration**
2. Name: `sp-aas-query`
3. Click **Register**
4. Note the **Application (client) ID** and **Directory (tenant) ID**
5. Go to **Certificates & secrets** > **New client secret**
6. Add description and set expiration
7. **Copy the secret value immediately** (it won't be shown again)

## Step 2: Configure Analysis Services Permissions

### Method 1: Using Azure Portal

1. Navigate to your **Azure Analysis Services** resource
2. Click **Analysis Services Admins** in the left menu
3. Click **Add**
4. Enter the service principal in this format:
   ```
   app:{CLIENT_ID}@{TENANT_ID}
   ```
   Example: `app:12345678-1234-1234-1234-123456789012@87654321-4321-4321-4321-210987654321`
5. Click **Save**

### Method 2: Using PowerShell

```powershell
# Install Az.AnalysisServices module if not already installed
Install-Module -Name Az.AnalysisServices -Force

# Connect to Azure
Connect-AzAccount

# Add service principal as admin
$serverName = "asazure://yourregion.asazure.windows.net/yourserver"
$spn = "app:{CLIENT_ID}@{TENANT_ID}"

Add-AzAnalysisServicesAccount -ServicePrincipal -Tenant "{TENANT_ID}" -Credential (Get-Credential)
Add-RoleGroupMember -Server $serverName -RoleName "Administrators" -MemberName $spn
```

### Method 3: Using SQL Server Management Studio (SSMS)

1. Connect to your Analysis Services instance
2. Right-click the server name > **Properties**
3. Select **Security** > **Add**
4. Enter: `app:{CLIENT_ID}@{TENANT_ID}`
5. Click **OK**

## Step 3: Configure API Permissions (Optional)

If using additional Azure services, configure API permissions:

1. Go to **Azure Active Directory** > **App registrations**
2. Select your app registration
3. Click **API permissions** > **Add a permission**
4. Select **APIs my organization uses**
5. Search for **Azure Analysis Services**
6. Select appropriate permissions
7. Click **Grant admin consent**

## Step 4: Verify Service Principal

### Test with Azure CLI

```bash
# Login with service principal
az login --service-principal \
  --username {CLIENT_ID} \
  --password {CLIENT_SECRET} \
  --tenant {TENANT_ID}

# Verify access
az resource list --output table
```

### Test Connection Programmatically

Create a test script `test_sp.py`:

```python
from msal import ConfidentialClientApplication

TENANT_ID = "your-tenant-id"
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"

app = ConfidentialClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    client_credential=CLIENT_SECRET,
)

result = app.acquire_token_for_client(
    scopes=["https://*.asazure.windows.net/.default"]
)

if "access_token" in result:
    print("✓ Service principal authentication successful!")
    print(f"Token acquired, expires in {result['expires_in']} seconds")
else:
    print("✗ Authentication failed:")
    print(result.get("error"))
    print(result.get("error_description"))
```

Run the test:
```bash
pip install msal
python test_sp.py
```

## Step 5: Configure Azure Function

Set the service principal credentials as environment variables in your Azure Function:

```bash
az functionapp config appsettings set \
  --name your-function-app-name \
  --resource-group your-resource-group \
  --settings \
    TENANT_ID="{your-tenant-id}" \
    CLIENT_ID="{your-client-id}" \
    CLIENT_SECRET="{your-client-secret}"
```

## Common Issues and Solutions

### Issue: "Unauthorized" or "Access Denied"

**Solution**:
- Verify service principal format is exactly: `app:{CLIENT_ID}@{TENANT_ID}`
- Ensure you're using the correct CLIENT_ID (not Object ID)
- Check that the service principal was added to Analysis Services admins
- Wait a few minutes for permissions to propagate

### Issue: "Invalid client secret"

**Solution**:
- Client secrets expire - check expiration date in Azure Portal
- Create a new secret if expired
- Ensure no extra spaces when copying the secret

### Issue: "AADSTS7000215: Invalid client secret"

**Solution**:
- The secret value was copied incorrectly
- Regenerate a new client secret
- Make sure to copy the secret **value**, not the secret **ID**

### Issue: "Tenant ID not found"

**Solution**:
- Verify you're using the Directory (tenant) ID, not subscription ID
- Check you're connected to the correct Azure AD tenant

## Security Best Practices

1. **Secret Rotation**: Set client secrets to expire and rotate them regularly
2. **Least Privilege**: Only grant necessary permissions
3. **Azure Key Vault**: Store secrets in Key Vault instead of environment variables
4. **Monitoring**: Enable Azure Monitor to track service principal usage
5. **Conditional Access**: Consider applying conditional access policies
6. **Named Accounts**: Use descriptive names like `sp-aas-query-prod`

## Using Azure Key Vault (Recommended for Production)

### Store Secret in Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name kv-aas-secrets \
  --resource-group your-rg \
  --location eastus2

# Store client secret
az keyvault secret set \
  --vault-name kv-aas-secrets \
  --name CLIENT-SECRET \
  --value "{your-client-secret}"
```

### Reference in Azure Function

Update Azure Function app settings:

```bash
az functionapp config appsettings set \
  --name your-function-app \
  --resource-group your-rg \
  --settings \
    CLIENT_SECRET="@Microsoft.KeyVault(SecretUri=https://kv-aas-secrets.vault.azure.net/secrets/CLIENT-SECRET/)"
```

Grant Function App access to Key Vault:

```bash
# Enable system-assigned managed identity
az functionapp identity assign \
  --name your-function-app \
  --resource-group your-rg

# Get the principal ID (from output above)
PRINCIPAL_ID=$(az functionapp identity show \
  --name your-function-app \
  --resource-group your-rg \
  --query principalId -o tsv)

# Grant access to Key Vault
az keyvault set-policy \
  --name kv-aas-secrets \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list
```

## Credential Values Summary

After completing these steps, you should have:

| Value | Description | Where to Use |
|-------|-------------|--------------|
| `TENANT_ID` | Azure AD Directory ID | Azure Function, local.settings.json |
| `CLIENT_ID` | Application (client) ID | Azure Function, local.settings.json |
| `CLIENT_SECRET` | Client secret value | Azure Function, Key Vault |
| `app:{CLIENT_ID}@{TENANT_ID}` | AAS admin format | Analysis Services Admins list |

## Next Steps

1. [Deploy Azure Function](deploy-azure-function.md)
2. [Deploy MCP Server](deploy-mcp-server.md)
3. Test end-to-end functionality

## Additional Resources

- [Azure AD App Registrations](https://learn.microsoft.com/azure/active-directory/develop/quickstart-register-app)
- [Service Principal Authentication](https://learn.microsoft.com/azure/active-directory/develop/howto-create-service-principal-portal)
- [Analysis Services Security](https://learn.microsoft.com/azure/analysis-services/analysis-services-manage-users)
- [Azure Key Vault](https://learn.microsoft.com/azure/key-vault/general/overview)
