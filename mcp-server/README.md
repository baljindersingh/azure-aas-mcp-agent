# MCP Server - Azure Analysis Services Query Tool

A Model Context Protocol (MCP) server that exposes Azure Analysis Services querying capabilities as a tool for AI agents.

## Overview

This MCP server provides a `query_analysis_services` tool that allows AI agents to execute DAX or MDX queries against Azure Analysis Services through the deployed Azure Function endpoint.

## Features

- ✅ Standard MCP stdio protocol implementation
- ✅ Exposes Azure Analysis Services queries as AI agent tool
- ✅ Supports both DAX and MDX query types
- ✅ Includes example AI agent implementation
- ✅ Environment-based configuration

## Prerequisites

- Python 3.10 or higher
- Deployed Azure Function (see [deploy-azure-function.md](../docs/deploy-azure-function.md))
- Azure OpenAI account (for running the example agent)

## Setup

### 1. Install Dependencies

```bash
cd mcp-server
python -m pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```env
AZURE_FUNCTION_URL=https://your-function-app.azurewebsites.net/api/query
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

## Components

### server.py

The main MCP server implementation. This file:
- Implements the MCP stdio protocol
- Defines the `query_analysis_services` tool
- Handles communication between AI agents and the Azure Function

**Usage**: This server is designed to be invoked by MCP clients (like AI agents), not run directly.

### simple_agent.py

An example AI agent that demonstrates how to use the MCP server to query Analysis Services using natural language.

**Run the agent**:
```bash
python simple_agent.py
```

**Example interaction**:
```
You: Show me the top 10 products
Agent: [Calls query_analysis_services with generated DAX query]
       Here are the top 10 products:
       1. Product A
       2. Product B
       ...
```

## MCP Tool Reference

### query_analysis_services

Execute DAX or MDX queries against Azure Analysis Services.

**Parameters**:
- `query` (string, required): The DAX or MDX query to execute
- `query_type` (string, optional): Either "DAX" or "MDX" (defaults to "DAX")

**Returns**: JSON object with query results

**Example**:
```json
{
  "row_count": 5,
  "rows": [
    {
      "Product[Product Name]": "Product A",
      "Product[Price]": 100
    },
    ...
  ]
}
```

## Integration with AI Frameworks

### Using with Custom Agents

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set up MCP server connection
server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
)

# Connect and use
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # Call the tool
        result = await session.call_tool(
            "query_analysis_services",
            arguments={
                "query": "EVALUATE TOPN(10, 'Product')"
            }
        )
        
        print(result.content[0].text)
```

### Using with OpenAI Function Calling

The `simple_agent.py` demonstrates how to:
1. Connect to the MCP server
2. List available tools
3. Convert MCP tool definitions to OpenAI function format
4. Use OpenAI's function calling to automatically invoke the tool

## Configuration Reference

| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| `AZURE_FUNCTION_URL` | URL of the deployed Azure Function | Yes |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key (for agent only) | No* |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint (for agent only) | No* |

*Required only for running `simple_agent.py`

## Troubleshooting

### Server won't start

**Issue**: ImportError or module not found
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Connection refused

**Issue**: Cannot connect to Azure Function
- Verify `AZURE_FUNCTION_URL` in `.env` is correct
- Test the Azure Function directly with curl
- Check Azure Function is running and accessible

### Tool execution fails

**Issue**: Error when executing queries
- Check Azure Function logs for errors
- Verify service principal has permissions
- Ensure DAX/MDX syntax is correct

### Agent doesn't respond

**Issue**: simple_agent.py hangs or doesn't respond
- Verify OpenAI credentials are correct
- Check your OpenAI deployment name matches the model specified
- Ensure you have sufficient quota

## Development

### Testing the MCP Server

You can test the server using the included agent:

```bash
# With test credentials
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
python simple_agent.py
```

### Adding Custom Tools

To add more tools to the MCP server, edit `server.py`:

1. Add new tool definition in `list_tools()`:
```python
Tool(
    name="your_new_tool",
    description="Tool description",
    inputSchema={...}
)
```

2. Handle the tool in `call_tool()`:
```python
elif name == "your_new_tool":
    # Implementation
```

## Architecture

```
┌─────────────────┐
│   AI Agent      │
│ (simple_agent)  │
└────────┬────────┘
         │
         │ MCP stdio protocol
         │
┌────────▼────────┐
│   MCP Server    │
│   (server.py)   │
└────────┬────────┘
         │
         │ HTTPS POST
         │
┌────────▼────────┐
│ Azure Function  │
└────────┬────────┘
         │
         │ ADOMD.NET
         │
┌────────▼────────┐
│   Azure AAS     │
└─────────────────┘
```

## Performance Considerations

- **Concurrent Requests**: The MCP server handles one request at a time per session
- **Timeout**: HTTP requests to Azure Function timeout after 60 seconds
- **Query Optimization**: Complex DAX queries may take longer to execute
- **Caching**: Consider implementing result caching for frequently accessed data

## Security Notes

- The MCP server runs locally and uses stdio for communication
- Azure Function URL should use HTTPS
- Never commit `.env` file with real credentials
- For production, consider authentication on the Azure Function endpoint

## Additional Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [DAX Query Reference](https://learn.microsoft.com/dax/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)

## Examples

See [simple_agent.py](simple_agent.py) for a complete example of:
- Setting up MCP client connection
- Converting MCP tools to OpenAI functions
- Natural language to DAX query translation
- Result formatting and presentation
