#!/bin/bash

# M&A Research Assistant MCP Server Startup Script
# This script ensures proper environment setup for Claude Desktop

# Set the working directory
cd "/Users/jamespeltier/AI Projects/MCP_m_and_a"

# Activate virtual environment
source venv/bin/activate

# Set Python path
export PYTHONPATH="/Users/jamespeltier/AI Projects/MCP_m_and_a/src:$PYTHONPATH"

# Start the MCP server
python -m ma_research_mcp.main