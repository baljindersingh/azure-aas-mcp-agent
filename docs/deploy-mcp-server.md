# Deploying the MCP Server

This guide covers setting up and running the MCP (Model Context Protocol) server to integrate Azure Analysis Services with AI agents.

## Prerequisites

- Completed [Azure Function deployment](deploy-azure-function.md)
- Python 3.10 or higher
- Azure OpenAI service (optional, for agent example)
- Function URL from deployed Azure Function

---

## Local Development Setup

### Step 1: Python Environment

```bash
# Navigate to MCP server directory
cd mcp-server

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `mcp>=1.0.0` - Model Context Protocol SDK
- `httpx>=0.27.0` - Async HTTP client
- `openai>=1.0.0` - OpenAI SDK (for agent example)

### Step 3: Configure Environment

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Required: Azure Function endpoint
AZURE_FUNCTION_URL=https://your-function-app.azurewebsites.net/api/query

# Optional: For simple_agent.py example
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### Step 4: Verify Installation

```bash
# Test MCP server (should show usage info)
python server.py
```

---

## Running the MCP Server

### Understanding MCP Architecture

The MCP server uses **stdio (standard input/output)** for communication:

- **Not** a standalone HTTP server
- Communicates via stdin/stdout
- Must be invoked by an MCP client
- Cannot be tested with curl/browser

### MCP Client Integration

The server is designed to be used by MCP clients like:
- Claude Desktop
- Custom AI agents
- Other MCP-compatible applications

### Example: Using with Custom Agent

```bash
python simple_agent.py
```

This runs an interactive agent that uses the MCP server internally.

---

## Production Deployment Options

### Option 1: Container Deployment (Recommended)

#### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server.py .
COPY .env .

# MCP servers use stdio, not HTTP
CMD ["python", "server.py"]
```

#### Build and Run

```bash
# Build image
docker build -t aas-mcp-server .

# Run container
docker run -it --rm \
  -e AZURE_FUNCTION_URL=$AZURE_FUNCTION_URL \
  aas-mcp-server
```

### Option 2: Azure Container Instances

```bash
# Set variables
RESOURCE_GROUP="rg-aas-mcp"
LOCATION="eastus2"
CONTAINER_NAME="aas-mcp-server"

# Create container
az container create \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_NAME \
  --image your-registry/aas-mcp-server:latest \
  --environment-variables \
    AZURE_FUNCTION_URL=$AZURE_FUNCTION_URL \
  --cpu 1 \
  --memory 1.5
```

### Option 3: Azure App Service (Linux)

```bash
# Create App Service Plan
az appservice plan create \
  --name plan-aas-mcp \
  --resource-group $RESOURCE_GROUP \
  --sku B1 \
  --is-linux

# Create Web App
az webapp create \
  --name webapp-aas-mcp \
  --resource-group $RESOURCE_GROUP \
  --plan plan-aas-mcp \
  --runtime "PYTHON:3.11"

# Configure settings
az webapp config appsettings set \
  --name webapp-aas-mcp \
  --resource-group $RESOURCE_GROUP \
  --settings \
    AZURE_FUNCTION_URL=$AZURE_FUNCTION_URL

# Deploy code
az webapp up \
  --name webapp-aas-mcp \
  --resource-group $RESOURCE_GROUP \
  --runtime PYTHON:3.11
```

### Option 4: VM Deployment

```bash
# SSH into VM
ssh user@your-vm

# Install Python
sudo apt update
sudo apt install python3.11 python3.11-venv

# Clone repository
git clone https://github.com/your-org/azure-aas-mcp-agent.git
cd azure-aas-mcp-agent/mcp-server

# Setup environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure .env
nano .env

# Run as service (see systemd example below)
```

---

## Running as a Service

### Systemd Service (Linux)

Create `/etc/systemd/system/aas-mcp.service`:

```ini
[Unit]
Description=Azure AAS MCP Server
After=network.target

[Service]
Type=simple
User=mcpuser
WorkingDirectory=/opt/aas-mcp-server
Environment="PATH=/opt/aas-mcp-server/venv/bin"
EnvironmentFile=/opt/aas-mcp-server/.env
ExecStart=/opt/aas-mcp-server/venv/bin/python server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aas-mcp.service
sudo systemctl start aas-mcp.service
sudo systemctl status aas-mcp.service
```

### Windows Service

Use NSSM (Non-Sucking Service Manager):

```powershell
# Install NSSM
choco install nssm

# Create service
nssm install AAS-MCP "C:\path\to\venv\Scripts\python.exe" "C:\path\to\server.py"
nssm set AAS-MCP AppDirectory "C:\path\to\mcp-server"
nssm set AAS-MCP AppEnvironmentExtra "AZURE_FUNCTION_URL=https://..."
nssm start AAS-MCP
```

---

## Integration with AI Platforms

### Claude Desktop Integration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "azure-aas": {
      "command": "python",
      "args": ["C:/path/to/azure-aas-mcp-agent/mcp-server/server.py"],
      "env": {
        "AZURE_FUNCTION_URL": "https://your-function.azurewebsites.net/api/query"
      }
    }
  }
}
```

Restart Claude Desktop to load the MCP server.

### Custom Agent Integration

Use the `simple_agent.py` as a template:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env={"AZURE_FUNCTION_URL": "https://..."}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {tools}")
            
            # Call tool
            result = await session.call_tool(
                "query_analysis_services",
                arguments={"query": "EVALUATE ROW(\"Test\", 1)"}
            )
            print(result)

asyncio.run(main())
```

### OpenAI Function Calling Integration

```python
from openai import AzureOpenAI
import json

# Initialize OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# Define function for OpenAI
functions = [{
    "name": "query_analysis_services",
    "description": "Query Azure Analysis Services using DAX",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "DAX query to execute"
            }
        },
        "required": ["query"]
    }
}]

# Use in chat
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Show me top 5 products"}
    ],
    functions=functions,
    function_call="auto"
)
```

---

## Monitoring and Logging

### Basic Logging

Add logging to `server.py`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp-server.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### Application Insights Integration

```bash
pip install opencensus-ext-azure
```

```python
from opencensus.ext.azure.log_exporter import AzureLogHandler

logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=your-key'
))
```

### Monitoring Metrics

Track:
- Request count
- Error rate
- Response time
- Azure Function availability

---

## Security Best Practices

### 1. Secure Environment Variables

Use Azure Key Vault:

```bash
# Store Function URL in Key Vault
az keyvault secret set \
  --vault-name your-keyvault \
  --name azure-function-url \
  --value "https://your-function.azurewebsites.net/api/query"

# Retrieve in application
az keyvault secret show \
  --vault-name your-keyvault \
  --name azure-function-url \
  --query value -o tsv
```

### 2. Network Security

- Use VNet integration
- Configure private endpoints
- Enable firewall rules

### 3. Authentication

Add authentication to the MCP server if exposing externally:

```python
import os

def verify_api_key(key: str) -> bool:
    return key == os.getenv("MCP_API_KEY")
```

---

## Troubleshooting

### Common Issues

**Error: "Cannot connect to Azure Function"**

```bash
# Test Function URL
curl -X POST "$AZURE_FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{"query": "EVALUATE ROW(\"Test\", 1)"}'
```

**Error: "Module 'mcp' not found"**

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

**Error: "Environment variable not set"**

```bash
# Check .env file
cat .env

# Verify loading
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('AZURE_FUNCTION_URL'))"
```

### Debug Mode

Run with debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Validate MCP Protocol

Test with MCP inspector:

```bash
npx @modelcontextprotocol/inspector python server.py
```

---

## Performance Optimization

### 1. Connection Pooling

Use httpx connection pooling (already configured in `server.py`):

```python
async with httpx.AsyncClient(timeout=30.0) as client:
    # Reuses connections automatically
    response = await client.post(url, json=payload)
```

### 2. Caching Results

Add caching for frequently accessed queries:

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def get_cached_result(query_hash: str):
    # Return cached result if available
    pass
```

### 3. Async Operations

The server already uses async/await for optimal performance.

---

## Testing

### Unit Tests

Create `test_server.py`:

```python
import pytest
from server import app

@pytest.mark.asyncio
async def test_query_tool():
    # Test MCP tool
    result = await app.call_tool(
        "query_analysis_services",
        {"query": "EVALUATE ROW(\"Test\", 1)"}
    )
    assert result is not None
```

Run tests:

```bash
pytest test_server.py
```

### Integration Tests

Test end-to-end with Function:

```bash
python test_integration.py
```

---

## Updating the Server

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Deploy Updates

```bash
# Pull latest code
git pull

# Restart service
sudo systemctl restart aas-mcp.service

# Or rebuild container
docker build -t aas-mcp-server .
docker stop aas-mcp && docker rm aas-mcp
docker run -d --name aas-mcp aas-mcp-server
```

---

## Production Checklist

- [ ] Configure environment variables securely
- [ ] Enable logging and monitoring
- [ ] Set up error alerting
- [ ] Test failover scenarios
- [ ] Configure automatic restarts
- [ ] Document runbook procedures
- [ ] Set up backup for configuration
- [ ] Test disaster recovery
- [ ] Configure rate limiting (if needed)
- [ ] Enable security scanning

---

## Next Steps

1. Test integration with your AI agent
2. Monitor performance and errors
3. Scale based on usage patterns
4. Implement additional MCP tools as needed

## Additional Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Azure App Service Documentation](https://learn.microsoft.com/azure/app-service/)
- [Python Best Practices](https://learn.microsoft.com/azure/architecture/best-practices/)
