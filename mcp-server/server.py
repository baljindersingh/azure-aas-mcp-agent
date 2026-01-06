"""
MCP Server for Azure Analysis Services Query Function
Exposes the Azure Function as an MCP tool for Foundry Agents
"""

import asyncio
import json
import os
from typing import Any
import httpx
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Azure Function endpoint
AZURE_FUNCTION_URL = os.getenv(
    "AZURE_FUNCTION_URL", 
    "https://your-function-app.azurewebsites.net/api/query"
)

# Create MCP server instance
app = Server("azure-aas-query")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="query_analysis_services",
            description=(
                "Execute DAX or MDX queries against Azure Analysis Services. "
                "Use this tool to query the adventureworks tabular model. "
                "Supports DAX queries for tabular models and MDX queries for multidimensional models. "
                "Returns query results as rows of data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The DAX or MDX query to execute. "
                            "Example DAX: EVALUATE TOPN(10, 'Product') "
                            "Example MDX: SELECT [Measures].[Sales Amount] ON 0 FROM [AdventureWorks]"
                        ),
                    },
                    "query_type": {
                        "type": "string",
                        "enum": ["DAX", "MDX"],
                        "default": "DAX",
                        "description": "The type of query - DAX for tabular models, MDX for multidimensional models",
                    },
                },
                "required": ["query"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    
    if name != "query_analysis_services":
        raise ValueError(f"Unknown tool: {name}")
    
    # Extract arguments
    query = arguments.get("query")
    query_type = arguments.get("query_type", "DAX")
    
    if not query:
        raise ValueError("Query parameter is required")
    
    # Call Azure Function
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                AZURE_FUNCTION_URL,
                json={
                    "queryType": query_type,
                    "query": query,
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Format the response
            if "rows" in result:
                rows = result["rows"]
                if rows:
                    # Format as a readable table
                    formatted_result = {
                        "row_count": len(rows),
                        "rows": rows,
                    }
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(formatted_result, indent=2),
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text="Query executed successfully but returned no rows.",
                        )
                    ]
            elif "error" in result:
                return [
                    TextContent(
                        type="text",
                        text=f"Query failed: {result['error']}",
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2),
                    )
                ]
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            return [TextContent(type="text", text=f"Error calling Azure Function: {error_msg}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="azure-aas-query",
            server_version="1.0.0",
            capabilities=app.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
        await app.run(
            read_stream,
            write_stream,
            init_options,
        )


if __name__ == "__main__":
    asyncio.run(main())
