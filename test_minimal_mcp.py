#!/usr/bin/env python3
"""
Minimal MCP server test to isolate the issue
"""
import os
import sys

# Add src to path
sys.path.insert(0, '/Users/jamespeltier/AI Projects/MCP_m_and_a/src')

from fastmcp import FastMCP

# Initialize minimal MCP server
mcp = FastMCP("Test Server")

@mcp.tool()
async def test_tool() -> dict:
    """Simple test tool"""
    return {"status": "working"}

if __name__ == "__main__":
    # Set MCP mode
    os.environ['MCP_MODE'] = 'true'
    
    try:
        print("Starting minimal test server...", file=sys.stderr)
        mcp.run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()