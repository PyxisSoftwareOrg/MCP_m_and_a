#!/usr/bin/env python3
"""
Simple HTTP server for MCP tools using FastAPI
"""
import asyncio
import logging
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .tools import (
    analyze_company,
    scrape_website,
    get_linkedin_data,
    score_dimension,
    search_companies,
    export_report,
)
from .core.config import get_config
from .core.logging_config import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="M&A Research Assistant",
    description="HTTP API for M&A research tools",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    config = get_config()
    return {
        "status": "healthy",
        "version": "1.0.0",
        "server_name": config.MCP_SERVER_NAME,
        "timestamp": asyncio.get_event_loop().time()
    }

@app.post("/tools/analyze_company")
async def api_analyze_company(
    company_name: str,
    website_url: str,
    linkedin_url: str = "",
    force_refresh: bool = False,
    skip_filtering: bool = False,
    manual_override: bool = False
):
    """Analyze a company"""
    try:
        result = await analyze_company(
            company_name, website_url, linkedin_url, 
            force_refresh, skip_filtering, manual_override
        )
        return result
    except Exception as e:
        logger.error(f"Error analyzing company: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/scrape_website")
async def api_scrape_website(
    website_url: str,
    max_pages: int = 5,
    priority_keywords: List[str] = None
):
    """Scrape a website"""
    try:
        result = await scrape_website(website_url, max_pages, priority_keywords or [])
        return result
    except Exception as e:
        logger.error(f"Error scraping website: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/get_linkedin_data")
async def api_get_linkedin_data(
    linkedin_url: str,
    force_refresh: bool = False
):
    """Get LinkedIn company data"""
    try:
        result = await get_linkedin_data(linkedin_url, force_refresh)
        return result
    except Exception as e:
        logger.error(f"Error getting LinkedIn data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/score_dimension")
async def api_score_dimension(
    dimension_name: str,
    company_data: Dict[str, Any],
    scoring_system_id: str = "default"
):
    """Score a company dimension"""
    try:
        result = await score_dimension(dimension_name, company_data, scoring_system_id)
        return result
    except Exception as e:
        logger.error(f"Error scoring dimension: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/search_companies")
async def api_search_companies(
    criteria: Dict[str, Any],
    sort_by: str = "overall_score",
    limit: int = 50
):
    """Search companies"""
    try:
        result = await search_companies(criteria, sort_by, limit)
        return result
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/export_report")
async def api_export_report(
    company_names: List[str],
    format: str = "json",
    include_raw_data: bool = False
):
    """Export company reports"""
    try:
        result = await export_report(company_names, format, include_raw_data)
        return result
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """Main entry point"""
    logger.info("Starting M&A Research Assistant HTTP Server")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()