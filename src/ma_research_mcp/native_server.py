#!/usr/bin/env python3
"""
Native MCP server implementation for M&A Research Assistant
"""
import asyncio
import sys
import os
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import our existing tools
from .tools import (
    analyze_company,
    scrape_website,
    get_linkedin_data,
    score_dimension,
    enrich_company_data,
    get_company_history,
    compare_analyses,
    bulk_analyze,
    bulk_filter,
    run_custom_scoring,
    search_companies,
    export_report,
    generate_xlsx_export,
    qualify_lead,
    generate_investment_thesis,
    manage_lead_nurturing,
    manage_scoring_systems,
    override_company_tier,
    manage_company_lists,
    update_metadata,
)
from .core.config import get_config
from .core.logging_config import setup_logging

# Initialize logging
setup_logging()

# Create server instance
server = Server("M&A Research Assistant")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="analyze_company",
            description="Orchestrates complete company analysis with scoring and qualification",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Name of the company to analyze"},
                    "website_url": {"type": "string", "description": "Company website URL"},
                    "linkedin_url": {"type": "string", "description": "LinkedIn company URL (optional)"},
                    "force_refresh": {"type": "boolean", "description": "Force refresh of cached data", "default": False},
                    "skip_filtering": {"type": "boolean", "description": "Skip lead qualification filtering", "default": False},
                    "manual_override": {"type": "boolean", "description": "Allow manual override of scoring", "default": False}
                },
                "required": ["company_name", "website_url"]
            }
        ),
        Tool(
            name="scrape_website",
            description="Intelligent website scraping with priority keyword targeting",
            inputSchema={
                "type": "object",
                "properties": {
                    "website_url": {"type": "string", "description": "Website URL to scrape"},
                    "max_pages": {"type": "integer", "description": "Maximum pages to scrape", "default": 5},
                    "priority_keywords": {"type": "array", "items": {"type": "string"}, "description": "Priority keywords for targeting"}
                },
                "required": ["website_url"]
            }
        ),
        Tool(
            name="get_linkedin_data",
            description="Fetches LinkedIn company data via Apify API",
            inputSchema={
                "type": "object",
                "properties": {
                    "linkedin_url": {"type": "string", "description": "LinkedIn company URL"},
                    "force_refresh": {"type": "boolean", "description": "Force refresh of cached data", "default": False}
                },
                "required": ["linkedin_url"]
            }
        ),
        Tool(
            name="score_dimension",
            description="Generic scoring function for any dimension",
            inputSchema={
                "type": "object",
                "properties": {
                    "dimension_name": {"type": "string", "description": "Name of the dimension to score"},
                    "company_data": {"type": "object", "description": "Company data for scoring"},
                    "scoring_system_id": {"type": "string", "description": "Scoring system ID", "default": "default"}
                },
                "required": ["dimension_name", "company_data"]
            }
        ),
        Tool(
            name="search_companies",
            description="Search analyzed companies by various criteria",
            inputSchema={
                "type": "object",
                "properties": {
                    "criteria": {"type": "object", "description": "Search criteria"},
                    "sort_by": {"type": "string", "description": "Sort field", "default": "overall_score"},
                    "limit": {"type": "integer", "description": "Result limit", "default": 50}
                },
                "required": ["criteria"]
            }
        ),
        Tool(
            name="export_report",
            description="Generate formatted reports for companies",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_names": {"type": "array", "items": {"type": "string"}, "description": "List of company names"},
                    "format": {"type": "string", "description": "Export format (json, csv, xlsx)", "default": "json"},
                    "include_raw_data": {"type": "boolean", "description": "Include raw data", "default": False}
                },
                "required": ["company_names"]
            }
        ),
        Tool(
            name="health_check",
            description="Health check endpoint for monitoring",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "analyze_company":
            result = await analyze_company(
                arguments["company_name"],
                arguments["website_url"],
                arguments.get("linkedin_url", ""),
                arguments.get("force_refresh", False),
                arguments.get("skip_filtering", False),
                arguments.get("manual_override", False)
            )
        elif name == "scrape_website":
            result = await scrape_website(
                arguments["website_url"],
                arguments.get("max_pages", 5),
                arguments.get("priority_keywords", [])
            )
        elif name == "get_linkedin_data":
            result = await get_linkedin_data(
                arguments["linkedin_url"],
                arguments.get("force_refresh", False)
            )
        elif name == "score_dimension":
            result = await score_dimension(
                arguments["dimension_name"],
                arguments["company_data"],
                arguments.get("scoring_system_id", "default")
            )
        elif name == "search_companies":
            result = await search_companies(
                arguments["criteria"],
                arguments.get("sort_by", "overall_score"),
                arguments.get("limit", 50)
            )
        elif name == "export_report":
            result = await export_report(
                arguments["company_names"],
                arguments.get("format", "json"),
                arguments.get("include_raw_data", False)
            )
        elif name == "health_check":
            config = get_config()
            result = {
                "status": "healthy",
                "version": "1.0.0",
                "server_name": config.MCP_SERVER_NAME,
                "timestamp": asyncio.get_event_loop().time()
            }
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        # Convert result to JSON string for text content
        import json
        result_text = json.dumps(result, indent=2, default=str)
        
        return [
            TextContent(
                type="text",
                text=result_text
            )
        ]
    
    except Exception as e:
        import traceback
        error_text = f"Error executing {name}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        return [
            TextContent(
                type="text", 
                text=error_text
            )
        ]

async def main():
    """Main server entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())