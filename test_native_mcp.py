#!/usr/bin/env python3
"""
Native MCP server test using the official mcp library
"""
import asyncio
import sys
import os
from typing import Any

# Add src to path
sys.path.insert(0, '/Users/jamespeltier/AI Projects/MCP_m_and_a/src')

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Create server instance
server = Server("ma-research-test")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="test_tool",
            description="Simple test tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Test message"
                    }
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    if name == "test_tool":
        message = arguments.get("message", "Hello")
        return [
            TextContent(
                type="text",
                text=f"Test tool received: {message}"
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Main server entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        # Log error to file
        with open('native_mcp_error.log', 'w') as f:
            import traceback
            f.write(f"Error: {e}\n")
            f.write(traceback.format_exc())
        raise