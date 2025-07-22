"""
Main entry point for the M&A Research Assistant MCP Server
"""

import asyncio
import logging
from typing import Any, Dict

from fastmcp import FastMCP

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
from .tools.discovery_tools import discover_company_sources
from .core.config import get_config
from .core.logging_config import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("M&A Research Assistant")

# Register all tools
@mcp.tool()
async def analyze_company_tool(
    company_name: str,
    website_url: str = None,
    linkedin_url: str = None,
    auto_discover: bool = True,
    discovery_hints: Dict[str, Any] = None,
    force_refresh: bool = False,
    skip_filtering: bool = False,
    manual_override: bool = False,
    quick_mode: bool = True
) -> Dict[str, Any]:
    """Orchestrates complete company analysis with scoring and qualification. Can auto-discover URLs if not provided. Use quick_mode=True for faster responses."""
    return await analyze_company(
        company_name=company_name,
        website_url=website_url,
        linkedin_url=linkedin_url,
        auto_discover=auto_discover,
        discovery_hints=discovery_hints,
        force_refresh=force_refresh,
        skip_filtering=skip_filtering,
        manual_override=manual_override,
        research_depth="basic" if quick_mode else "standard",
        include_public_filings=not quick_mode,
        include_news_analysis=not quick_mode,
        include_location_extraction=not quick_mode
    )

@mcp.tool()
async def scrape_website_tool(
    website_url: str,
    max_pages: int = 5,
    priority_keywords: list[str] = None
) -> Dict[str, Any]:
    """Intelligent website scraping with priority keyword targeting"""
    return await scrape_website(website_url, max_pages, priority_keywords or [])

@mcp.tool()
async def get_linkedin_data_tool(
    linkedin_url: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """Fetches LinkedIn company data via Apify API"""
    return await get_linkedin_data(linkedin_url, force_refresh)

@mcp.tool()
async def score_dimension_tool(
    dimension_name: str,
    company_data: Dict[str, Any],
    scoring_system_id: str = "default"
) -> Dict[str, Any]:
    """Generic scoring function for any dimension"""
    return await score_dimension(dimension_name, company_data, scoring_system_id)

@mcp.tool()
async def enrich_company_data_tool(
    company_name: str,
    base_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Enhance company data from additional sources"""
    return await enrich_company_data(company_name, base_data)

@mcp.tool()
async def get_company_history_tool(
    company_name: str,
    limit: int = 10
) -> Dict[str, Any]:
    """Retrieves historical analyses for a company"""
    return await get_company_history(company_name, limit)

@mcp.tool()
async def get_latest_analysis_tool(
    company_name: str
) -> Dict[str, Any]:
    """Retrieves the latest analysis for a company"""
    from .services.s3_service import S3Service
    
    try:
        s3_service = S3Service()
        latest_analysis = await s3_service.get_analysis_result(company_name)
        
        if latest_analysis:
            return {
                "success": True,
                "company_name": company_name,
                "analysis": latest_analysis.dict()
            }
        else:
            return {
                "success": False,
                "error": f"No analysis found for company: {company_name}",
                "company_name": company_name
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve analysis: {str(e)}",
            "company_name": company_name
        }

@mcp.tool()
async def compare_analyses_tool(
    company_name: str,
    analysis1_timestamp: str,
    analysis2_timestamp: str
) -> Dict[str, Any]:
    """Compares two analyses of the same company"""
    return await compare_analyses(company_name, analysis1_timestamp, analysis2_timestamp)

@mcp.tool()
async def bulk_analyze_tool(
    companies: list[Dict[str, str]],
    max_parallel: int = 3
) -> Dict[str, Any]:
    """Parallel analysis of multiple companies"""
    return await bulk_analyze(companies, max_parallel)

@mcp.tool()
async def bulk_filter_tool(
    companies: list[str],
    criteria: Dict[str, Any]
) -> Dict[str, Any]:
    """Filter multiple companies against qualification criteria"""
    return await bulk_filter(companies, criteria)

@mcp.tool()
async def run_custom_scoring_tool(
    company_name: str,
    scoring_system_ids: list[str]
) -> Dict[str, Any]:
    """Run specific scoring systems on a company"""
    return await run_custom_scoring(company_name, scoring_system_ids)

@mcp.tool()
async def search_companies_tool(
    criteria: Dict[str, Any],
    sort_by: str = "overall_score",
    limit: int = 50
) -> Dict[str, Any]:
    """Search analyzed companies by various criteria"""
    return await search_companies(criteria, sort_by, limit)

@mcp.tool()
async def export_report_tool(
    company_names: list[str],
    format: str = "json",
    include_raw_data: bool = False
) -> Dict[str, Any]:
    """Generate formatted reports for companies"""
    return await export_report(company_names, format, include_raw_data)

@mcp.tool()
async def generate_xlsx_export_tool(
    companies: list[str],
    include_charts: bool = True,
    custom_fields: list[str] = None
) -> Dict[str, Any]:
    """Generate downloadable XLSX files with formatting"""
    return await generate_xlsx_export(companies, include_charts, custom_fields or [])

@mcp.tool()
async def qualify_lead_tool(
    company_name: str,
    force_requalification: bool = False
) -> Dict[str, Any]:
    """Complete multi-tier lead qualification"""
    return await qualify_lead(company_name, force_requalification)

@mcp.tool()
async def generate_investment_thesis_tool(
    company_name: str,
    thesis_type: str = "standard"
) -> Dict[str, Any]:
    """AI-powered investment thesis generation"""
    return await generate_investment_thesis(company_name, thesis_type)

@mcp.tool()
async def manage_lead_nurturing_tool(
    company_name: str,
    action: str,
    tier: str = None,
    notes: str = ""
) -> Dict[str, Any]:
    """Update lead tier and nurturing activities"""
    return await manage_lead_nurturing(company_name, action, tier, notes)

@mcp.tool()
async def manage_scoring_systems_tool(
    action: str,
    system_data: Dict[str, Any] = None,
    system_id: str = ""
) -> Dict[str, Any]:
    """Create and manage custom scoring systems"""
    return await manage_scoring_systems(action, system_data, system_id)

@mcp.tool()
async def override_company_tier_tool(
    company_name: str,
    new_tier: str,
    reason: str,
    override_by: str
) -> Dict[str, Any]:
    """Manual tier override with approval workflow"""
    return await override_company_tier(company_name, new_tier, reason, override_by)

@mcp.tool()
async def manage_company_lists_tool(
    action: str,
    company_name: str = "",
    list_type: str = "active",
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Manage active and future candidate lists"""
    return await manage_company_lists(action, company_name, list_type, metadata or {})

@mcp.tool()
async def update_metadata_tool(
    company_name: str,
    metadata_updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Manual metadata updates for companies"""
    return await update_metadata(company_name, metadata_updates)

@mcp.tool()
async def discover_company_sources_tool(
    company_name: str,
    industry_hint: str = None,
    location_hint: str = None,
    company_type_hint: str = None,
    discovery_timeout: int = 30,
    required_sources: list[str] = None,
    optional_sources: list[str] = None
) -> Dict[str, Any]:
    """Automatically discover company website, LinkedIn profile, and other data sources"""
    return await discover_company_sources(
        company_name=company_name,
        industry_hint=industry_hint,
        location_hint=location_hint,
        company_type_hint=company_type_hint,
        discovery_timeout=discovery_timeout,
        required_sources=required_sources,
        optional_sources=optional_sources
    )

@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring"""
    config = get_config()
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "server_name": config.MCP_SERVER_NAME,
        "timestamp": asyncio.get_event_loop().time()
    }

def main():
    """Main entry point"""
    # Only log startup message to file, not stdout (for MCP compatibility)
    logger.info("Starting M&A Research Assistant MCP Server")
    
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == "__main__":
    main()