"""
Simple agent using OpenAI directly with MCP tool
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from openai import AsyncAzureOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Load environment variables from .env file if it exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


async def query_analysis_services(mcp_session: ClientSession, query: str) -> str:
    """Call the MCP tool to query Analysis Services."""
    result = await mcp_session.call_tool(
        "query_analysis_services",
        arguments={"query": query}
    )
    return result.content[0].text


async def chat_loop(openai_client: AsyncAzureOpenAI, mcp_session: ClientSession):
    """Main chat loop."""
    messages = [
        {
            "role": "system",
            "content": """You are a helpful data analyst assistant with access to the AdventureWorks Analysis Services database.

When users ask about products, sales, customers, or other business data, you need to:
1. Write a DAX query to get the data
2. Use the query_analysis_services function with that query
3. Interpret and present the results to the user

Guidelines for writing DAX queries:
- Use EVALUATE to return a table
- Use VALUES() to get unique values from a column
- Use TOPN() to limit results
- Use SUMMARIZE() for aggregations
- Column references use 'TableName'[ColumnName] syntax
- Table references use 'TableName'

Examples:
- Top products: EVALUATE TOPN(10, 'Product')
- Unique product names: EVALUATE VALUES('Product'[Product Name])
- Products with details: EVALUATE SELECTCOLUMNS('Product', "Name", 'Product'[Product Name], "Color", 'Product'[Color])

After getting results, format them in a clear, readable way for the user."""
        }
    ]
    
    # Get available tools from MCP
    tools_response = await mcp_session.list_tools()
    mcp_tools = tools_response.tools
    
    # Convert MCP tools to OpenAI function format
    tools = []
    for tool in mcp_tools:
        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        })
    
    print("Data Analyst Agent ready! (Type 'exit' to quit)\n")
    
    while True:
        # Get user input
        user_input = input("You: ")
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Goodbye!")
            break
        
        if not user_input.strip():
            continue
        
        # Add user message
        messages.append({"role": "user", "content": user_input})
        
        # Call OpenAI
        print("Agent: ", end="", flush=True)
        
        while True:
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Check if the model wants to call a function
            if message.tool_calls:
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })
                
                # Execute each tool call
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"\n[Calling {function_name}...]", flush=True)
                    
                    if function_name == "query_analysis_services":
                        function_response = await query_analysis_services(
                            mcp_session,
                            function_args["query"]
                        )
                    else:
                        function_response = json.dumps({"error": f"Unknown function: {function_name}"})
                    
                    # Add function response
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response
                    })
                
                # Continue loop to get final response
                continue
            else:
                # No tool calls, print the response
                print(message.content)
                messages.append({"role": "assistant", "content": message.content})
                break
        
        print()


async def main():
    """Run the agent."""
    # Check for required environment variables
    if not os.getenv("AZURE_OPENAI_API_KEY") or not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("Error: Missing required environment variables.")
        print("Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")
        print("You can create a .env file with these values (see .env.example)")
        sys.exit(1)
    
    # Create OpenAI client
    openai_client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-10-21",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    # Set up MCP server
    server_path = Path(__file__).parent / "server.py"
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
    )
    
    # Connect to MCP server and run chat loop
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as mcp_session:
            await mcp_session.initialize()
            await chat_loop(openai_client, mcp_session)


if __name__ == "__main__":
    asyncio.run(main())
