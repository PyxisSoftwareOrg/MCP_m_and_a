#!/usr/bin/env python3
"""
Simple server test without complex imports
"""
import os
import sys
import asyncio

# Add src to path
sys.path.insert(0, '/Users/jamespeltier/AI Projects/MCP_m_and_a/src')

# Set environment
os.environ['MCP_MODE'] = 'true'

from fastmcp import FastMCP

# Initialize minimal MCP server
mcp = FastMCP("Simple Test")

@mcp.tool()
async def simple_test() -> dict:
    """Simple test tool"""
    return {"message": "Server is working", "status": "ok"}

@mcp.tool()
async def async_test() -> dict:
    """Test async functionality"""
    await asyncio.sleep(0.1)
    return {"async": "working"}

if __name__ == "__main__":
    try:
        # Suppress stderr for banner
        sys.stderr = open(os.devnull, 'w')
        mcp.run()
    except Exception as e:
        # Write to file since stderr is suppressed
        with open('simple_server_error.log', 'w') as f:
            import traceback
            f.write(f"Error: {e}\n")
            f.write(traceback.format_exc())
        raise