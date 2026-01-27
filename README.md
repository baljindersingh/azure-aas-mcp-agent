# Azure Analysis Services MCP Agent

An AI-powered solution that enables natural language interactions with Azure Analysis Services through the Model Context Protocol (MCP), combining a C# Azure Function with a Python MCP server and AI agent.

## 🏗️ Architecture

This solution uses a hybrid architecture to work around Azure Analysis Services protocol limitations:

```
┌─────────────────────┐
│   AI Agent/Client   │
│  (uses OpenAI API)  │
└──────────┬──────────┘
           │
           │ MCP Protocol (stdio)
           │
┌──────────▼──────────┐
│    MCP Server       │
│   (Python/stdio)    │
└──────────┬──────────┘
           │
           │ HTTPS
           │
┌──────────▼──────────┐
│  Azure Function     │
│   (.NET 8/C#)       │
│ Managed Identity    │
└──────────┬──────────┘
           │
           │ ADOMD.NET + OAuth2
           │
┌──────────▼──────────┐
│ Azure Analysis      │
│    Services         │
│ (Tabular Model)     │
└─────────────────────┘
```

### Why This Architecture?

**Azure Analysis Services requires ADOMD.NET** - it does NOT support XMLA over HTTPS. This means:
- ✅ C# with ADOMD.NET works perfectly
- ❌ Python direct connection doesn't work (no native ADOMD library available)
- ❌ Direct MCP → AAS fails (all HTTP/XMLA endpoints return 404)
- ✅ Solution: C# Azure Function handles AAS connectivity, Python MCP wraps the HTTP endpoint

**Why can't we skip the Azure Function?** The MCP server can't talk directly to AAS because:
1. Azure Analysis Services only supports the proprietary **ADOMD.NET protocol** (not standard HTTP/REST)
2. Python has **no native ADOMD library** - it only exists for .NET languages
3. XMLA over HTTPS is **not supported** by Azure Analysis Services (verified through testing)

For detailed architecture diagrams and decision rationale, see [ARCHITECTURE.md](ARCHITECTURE.md).

### Components:

1. **Azure Function (.NET 8/C#)** - Uses ADOMD.NET to connect to AAS with **Managed Identity** (no secrets!)
2. **MCP Server (Python)** - Wraps the Azure Function as an MCP tool for AI agents
3. **AI Agent (Python)** - Uses OpenAI to translate natural language to DAX/MDX queries

## ✨ Features

- 🔐 **Managed Identity** - No secrets to manage or rotate (recommended)
- 🚀 **Native Protocol** - ADOMD.NET for optimal Azure Analysis Services performance
- 🤖 **AI-Powered** - Natural language queries translated to DAX automatically
- 🔌 **MCP Standard** - Compatible with any MCP-enabled AI framework
- 📊 **Full Query Support** - Supports both DAX and MDX queries
- ☁️ **Serverless** - Azure Functions for scalable, cost-effective deployment
- 🏗️ **Infrastructure as Code** - Deploy with Bicep or Terraform

## 📋 Prerequisites

### Required Software

- **Azure Subscription** with Contributor access
- **Azure CLI** - [Download](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **.NET 8.0 SDK** - [Download](https://dotnet.microsoft.com/download/dotnet/8.0)
- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Azure Functions Core Tools v4** - [Download](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- **Bicep** (included with Azure CLI) or **Terraform** (optional) - [Download](https://www.terraform.io/downloads)

### Required Azure Resources

- **Azure Analysis Services** instance with a deployed tabular model
- **Azure OpenAI** resource for the AI agent
- Administrator access to configure AAS permissions

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/azure-aas-mcp-agent.git
cd azure-aas-mcp-agent
```

### 2. Deploy the Azure Function

#### Option 1: Automated Deployment (Recommended)

**Using Bicep:**
```bash
cd infrastructure/bicep
.\deploy.ps1 -Environment dev  # PowerShell
# or
./deploy.sh dev                # Bash
```

**Using Terraform:**
```bash
cd infrastructure/terraform
terraform init
terraform apply -var-file="dev.tfvars"
```

Both options automatically:
- Create Azure Function App with Managed Identity
- Configure all required app settings
- Assign permissions to Azure Analysis Services
- Deploy the function code

#### Option 2: Manual Setup

Follow the comprehensive step-by-step guide:

📖 **[Complete Setup Guide](SETUP_GUIDE.md)** - Detailed manual deployment instructions

### 3. Setup the MCP Server

```bash
cd mcp-server
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your Azure Function URL:
# AZURE_FUNCTION_URL=https://your-function.azurewebsites.net/api/query
```

### 4. Run the AI Agent

```bash
cd mcp-server
python simple_agent.py

# Ask natural language questions
You: Show me the top 10 products by sales
Agent: [Generates DAX query and returns formatted results]
```

## 📁 Project Structure

```
azure-aas-mcp-agent/
├── README.md                       # This file
├── SETUP_GUIDE.md                  # Step-by-step manual setup instructions
├── ARCHITECTURE.md                 # Detailed architecture diagrams
├── .gitignore                      # Git ignore rules
├── azure-function/                 # C# Azure Function (.NET 8)
│   ├── Program.cs                  # Function host configuration
│   ├── QueryAasFunction.cs         # HTTP trigger (ADOMD.NET client)
│   ├── azure-function.csproj       # Project file with dependencies
│   ├── host.json                   # Function host settings
│   └── local.settings.json.example # Local development settings template
├── infrastructure/                 # Infrastructure as Code
│   ├── README.md                   # Bicep vs Terraform comparison
│   ├── bicep/                      # Azure Bicep templates
│   │   ├── main.bicep              # Main template (Function + Managed Identity)
│   │   ├── parameters.dev.json     # Dev environment parameters
│   │   ├── parameters.prod.json    # Prod environment parameters
│   │   ├── deploy.ps1              # PowerShell deployment script
│   │   ├── deploy.sh               # Bash deployment script
│   │   └── README.md               # Bicep deployment guide
│   └── terraform/                  # Terraform templates
│       ├── main.tf                 # Main configuration
│       ├── variables.tf            # Variable definitions
│       ├── outputs.tf              # Output values
│       ├── dev.tfvars              # Dev environment variables
│       ├── prod.tfvars             # Prod environment variables
│       ├── .gitignore              # Terraform-specific ignores
│       └── README.md               # Terraform guide
└── mcp-server/                     # Python MCP Server & AI Agent
    ├── server.py                   # MCP server (calls Azure Function)
    ├── simple_agent.py             # AI agent example
    ├── requirements.txt            # Python dependencies
    └── .env.example                # Environment variables template
```

## 🔧 Configuration

### Azure Function App Settings

Automatically configured by Bicep/Terraform, or set manually in Azure Portal:

| Variable | Description | Example |
|----------|-------------|---------|
| `AAS_REGION_HOST` | Azure Analysis Services region endpoint | `aspaaseastus2.asazure.windows.net` |
| `AAS_SERVER_NAME` | Analysis Services server name | `aastest` |
| `AAS_DATABASE` | Database/model name | `adventureworks` |
| `USE_MANAGED_IDENTITY` | Use Managed Identity (recommended) | `true` |

**Note:** With Managed Identity, you don't need `TENANT_ID`, `CLIENT_ID`, or `CLIENT_SECRET`!

### MCP Server Environment Variables

Create `mcp-server/.env` from `.env.example`:

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_FUNCTION_URL` | Azure Function endpoint URL | Yes |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | Yes (for AI agent) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Yes (for AI agent) |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | Yes (for AI agent) |

## 💡 Usage Examples

### Using the AI Agent

```python
# Start the agent
cd mcp-server
python simple_agent.py

# Ask natural language questions
You: Show me the top 10 products by sales
Agent: [Generates DAX query and returns formatted results]

You: What are the sales by region?
Agent: [Automatically queries and presents the data]
```

### Direct MCP Tool Usage

```python
from mcp import ClientSession
# ... (see simple_agent.py for full example)

# Call the tool directly
result = await session.call_tool(
    "query_analysis_services",
    arguments={"query": "EVALUATE TOPN(5, 'Product')"}
)
```

### Direct Azure Function Call

```bash
curl -X POST https://your-function.azurewebsites.net/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "queryType": "DAX",
    "query": "EVALUATE ROW(\"Test\", 1)"
  }'
```

## 🔒 Security Best Practices

- **Managed Identity (Recommended)**: Use system-assigned managed identity for Azure Function → AAS authentication
- **Service Principal Permissions**: Grant only necessary permissions to Analysis Services
- **Function Authentication**: Enable Azure Functions authentication for production
- **Secrets Management**: Use Azure Key Vault for sensitive configuration
- **Network Security**: Configure firewall rules on Analysis Services
- **HTTPS Only**: All communication uses HTTPS/TLS encryption

## 🐛 Troubleshooting

### Common Issues

**Error: "Unauthorized" when querying Analysis Services**
- Verify Managed Identity is added to Analysis Services administrators
- For Service Principal: check format `app:{CLIENT_ID}@{TENANT_ID}`
- Use Azure Portal → Analysis Services → Server administrators

**Error: "Connection timeout"**
- Verify Analysis Services firewall allows Azure services
- Check network connectivity from Function App to Analysis Services
- Review Function App networking configuration

**Error: "Invalid query"**
- Verify DAX syntax is correct
- Check table and column names match your tabular model
- Test query directly in SQL Server Management Studio first

**MCP Server connection issues**
- Ensure Python dependencies are installed: `pip install -r requirements.txt`
- Verify `AZURE_FUNCTION_URL` in `.env` is correct and accessible
- Check Azure Function logs for errors

**Azure Function deployment fails**
- Ensure .NET 8.0 SDK is installed
- Verify Azure CLI is authenticated: `az login`
- Check Azure subscription permissions

For more detailed troubleshooting, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

## 📚 Additional Resources

- [ARCHITECTURE.md](ARCHITECTURE.md) - 11 detailed Mermaid diagrams explaining the architecture
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Complete step-by-step setup instructions
- [infrastructure/README.md](infrastructure/README.md) - Bicep vs Terraform comparison
- [Azure Analysis Services Documentation](https://learn.microsoft.com/azure/analysis-services/)
- [DAX Reference](https://learn.microsoft.com/dax/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Azure Functions Documentation](https://learn.microsoft.com/azure/azure-functions/)
- [ADOMD.NET Documentation](https://learn.microsoft.com/analysis-services/adomd/developing-with-adomd-net)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Model Context Protocol](https://modelcontextprotocol.io/)
- Uses [ADOMD.NET](https://www.nuget.org/packages/Microsoft.AnalysisServices.AdomdClient.NetCore.retail.amd64/) for Analysis Services connectivity
- Example based on AdventureWorks sample database

## 📞 Support

For questions or issues:
1. Review the [SETUP_GUIDE.md](SETUP_GUIDE.md) and [ARCHITECTURE.md](ARCHITECTURE.md)
2. Check the troubleshooting section above
3. Search [existing issues](../../issues)
4. Create a [new issue](../../issues/new) with detailed information

---

**Note**: This is a proof-of-concept implementation. For production use, consider additional security hardening, error handling, and monitoring capabilities.
