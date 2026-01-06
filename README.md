# Azure Analysis Services MCP Agent

An AI agent that queries Azure Analysis Services through a Model Context Protocol (MCP) server, enabling natural language interactions with your data warehouse.

## 🏗️ Architecture

This solution consists of two main components:

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

### Components:

1. **Azure Function** - Secure endpoint that authenticates with Azure Analysis Services using OAuth2 and executes DAX/MDX queries via ADOMD.NET
2. **MCP Server** - Model Context Protocol server that exposes the Azure Function as a tool for AI agents
3. **AI Agent** - Example implementation showing how to use OpenAI to interact with Analysis Services through natural language

## ✨ Features

- 🔐 **Secure Authentication** - Uses Azure AD service principal with OAuth2
- 🚀 **Native Protocol** - ADOMD.NET for optimal Azure Analysis Services performance
- 🤖 **AI-Powered** - Natural language queries translated to DAX automatically
- 🔌 **MCP Standard** - Compatible with any MCP-enabled AI framework
- 📊 **Full Query Support** - Supports both DAX and MDX queries
- ☁️ **Serverless** - Azure Functions for scalable, cost-effective deployment

## 📋 Prerequisites

### Required Software

- **Azure Subscription** with permissions to create:
  - Azure Analysis Services
  - Azure Function App
  - Azure AD App Registrations (Service Principal)
  - Storage Account

- **.NET 8.0 SDK** - [Download](https://dotnet.microsoft.com/download/dotnet/8.0)
- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Azure CLI** - [Download](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **Azure Functions Core Tools** - [Download](https://learn.microsoft.com/azure/azure-functions/functions-run-local)

### Azure Resources

You'll need an existing Azure Analysis Services instance with:
- A deployed tabular model (e.g., AdventureWorks)
- Administrator access to configure service principal permissions

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/azure-aas-mcp-agent.git
cd azure-aas-mcp-agent
```

### 2. Set Up Azure Resources

Follow the detailed setup guides in the `docs/` folder:

1. [Create and configure Azure Service Principal](docs/setup-service-principal.md)
2. [Deploy the Azure Function](docs/deploy-azure-function.md)
3. [Set up the MCP Server](docs/deploy-mcp-server.md)

### 3. Quick Test

Once deployed, test the Azure Function:

```bash
curl -X POST https://your-function-app.azurewebsites.net/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "EVALUATE TOPN(5, '\''Product'\'')"}'
```

Test the MCP server:

```bash
cd mcp-server
python -m pip install -r requirements.txt
# Set environment variables in .env file
python simple_agent.py
```

## 📁 Repository Structure

```
azure-aas-mcp-agent/
├── README.md                       # This file
├── .gitignore                      # Git ignore patterns
├── azure-function/                 # Azure Function App
│   ├── README.md                   # Azure Function documentation
│   ├── azure-function.csproj       # .NET project file
│   ├── azure-function.sln          # Visual Studio solution
│   ├── Program.cs                  # Function app entry point
│   ├── QueryAasFunction.cs         # Main function implementation
│   ├── host.json                   # Function host configuration
│   ├── local.settings.json.example # Local development settings template
│   └── Properties/
│       └── launchSettings.json     # Debug launch settings
├── mcp-server/                     # MCP Server
│   ├── README.md                   # MCP Server documentation
│   ├── server.py                   # MCP server implementation
│   ├── simple_agent.py             # Example AI agent
│   ├── requirements.txt            # Python dependencies
│   └── .env.example                # Environment variables template
└── docs/                           # Documentation
    ├── setup-service-principal.md  # Service principal setup guide
    ├── deploy-azure-function.md    # Azure Function deployment guide
    └── deploy-mcp-server.md        # MCP server deployment guide
```

## 🔧 Configuration

### Azure Function Configuration

Set these environment variables in your Azure Function App:

| Variable | Description | Example |
|----------|-------------|---------|
| `AAS_REGION_HOST` | Azure Analysis Services region | `aspaaseastus2.asazure.windows.net` |
| `AAS_SERVER_NAME` | Analysis Services server name | `aastest` |
| `AAS_DATABASE` | Database/model name | `adventureworks` |
| `TENANT_ID` | Azure AD tenant ID | `your-tenant-id` |
| `CLIENT_ID` | Service principal application ID | `your-client-id` |
| `CLIENT_SECRET` | Service principal secret | `your-client-secret` |

### MCP Server Configuration

Create a `.env` file in the `mcp-server/` directory:

```env
AZURE_FUNCTION_URL=https://your-function-app.azurewebsites.net/api/query
AZURE_OPENAI_API_KEY=your-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

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

## 🔒 Security Considerations

- **Service Principal Permissions**: Grant only necessary permissions to Analysis Services
- **Function Authentication**: Consider enabling Azure Functions authentication for production
- **Secrets Management**: Use Azure Key Vault for sensitive configuration
- **Network Security**: Configure firewall rules on Analysis Services
- **Token Caching**: MSAL automatically caches tokens for optimal performance
- **HTTPS Only**: All communication uses HTTPS/TLS encryption

## 🐛 Troubleshooting

### Common Issues

**Error: "Unauthorized" when querying Analysis Services**
- Verify service principal is added to Analysis Services administrators
- Check service principal format: `app:{CLIENT_ID}@{TENANT_ID}`

**Error: "Connection timeout"**
- Verify Analysis Services firewall allows Azure services
- Check network connectivity from Function App to Analysis Services

**Error: "Invalid query"**
- Verify DAX syntax is correct
- Check table and column names match your model

**MCP Server connection issues**
- Ensure Python dependencies are installed: `pip install -r requirements.txt`
- Verify Azure Function URL is correct in environment variables

For more detailed troubleshooting, see the component-specific README files.

## 📚 Additional Resources

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
1. Check the [documentation](docs/)
2. Search [existing issues](../../issues)
3. Create a [new issue](../../issues/new) with detailed information

---

**Note**: This is a proof-of-concept implementation. For production use, consider additional security hardening, error handling, and monitoring capabilities.
