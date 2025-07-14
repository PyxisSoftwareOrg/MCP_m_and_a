# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an M&A Research Assistant MCP Server for evaluating software companies as potential acquisition targets. It analyzes companies across 8 dimensions by scraping web content, LinkedIn data, and using LLM scoring algorithms with results stored in AWS S3.

## Architecture

- **Language**: Python 3.11+
- **Framework**: FastMCP 2.9+
- **Storage**: AWS S3 with versioning
- **Web Scraping**: Beautiful Soup 4, Requests
- **LinkedIn Data**: Apify API
- **LLM**: OpenAI API (gpt-4o-mini)
- **Data Processing**: Pandas, Pydantic models

## Key Dependencies

```python
fastmcp>=2.9.0
boto3>=1.28.0
beautifulsoup4>=4.12.0
requests>=2.31.0
openai>=1.0.0
pandas>=2.0.0
pydantic>=2.0.0
aiohttp>=3.9.0
tenacity>=8.2.0
```

## Core Components

1. **Web Scraping Engine**: Scrapes company websites recursively up to 3 priority subpages
2. **LinkedIn Integration**: Uses Apify API for company metadata and growth metrics
3. **LLM Analysis Engine**: Structured scoring with OpenAI API
4. **S3 Storage Manager**: Handles versioned analysis storage with lifecycle policies

## MCP Tools

The server implements 10 MCP tools:

- `analyze_company`: Full company analysis orchestration
- `scrape_website`: Intelligent website scraping
- `get_linkedin_data`: LinkedIn company data via Apify
- `score_dimension`: Generic scoring for 8 dimensions
- `get_company_history`: Historical analysis retrieval
- `compare_analyses`: Compare two analyses
- `bulk_analyze`: Parallel multi-company analysis
- `search_companies`: Search analyzed companies by criteria
- `export_report`: Generate formatted reports
- `update_metadata`: Manual metadata updates

## Scoring Dimensions

Eight scoring dimensions evaluate companies:

1. **VMS Score** (0-5): How tailored software is to specific industries
2. **Revenue Model** (0-5): Percentage of revenue from software licenses
3. **Suite vs Point** (0-5): Solution comprehensiveness
4. **Customer Quality** (0-5): Barriers to entry in target industries
5. **Pricing** (5-10): Annual pricing levels
6. **OPM Score** (5 or 10): Government/public funding dependency
7. **Size/Growth/Age** (5-9): Company maturity and growth trajectory
8. **Ownership Profile** (5-9): Funding vs revenue ratio

## S3 Storage Structure

```
s3://ma-research-bucket/
├── companies/{company-name}/{timestamp}/
│   ├── analysis.json
│   ├── raw_website_content.json
│   ├── linkedin_data.json
│   └── metadata.json
├── reports/{report-id}/
├── exports/{export-date}/
└── config/
```

## Environment Configuration

Required environment variables:
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- `S3_BUCKET_NAME`
- `OPENAI_API_KEY`
- `APIFY_API_TOKEN`
- `MCP_SERVER_NAME`, `MCP_SERVER_VERSION`

## Performance Requirements

- Single company analysis: < 60 seconds
- Bulk analysis (10 companies): < 5 minutes
- Maximum 5 parallel analyses
- Rate limiting for APIs and web scraping
- Comprehensive caching strategy

## Error Handling

Categorized error handling for:
- Web scraping failures (timeouts, 404s, rate limits)
- LinkedIn API errors
- LLM API issues
- S3 storage problems

Always save partial results and implement retry queues with exponential backoff.

## Development Commands

Check the prd.md file for detailed implementation requirements. The project uses:
- Async/await patterns for I/O operations
- Pydantic models for data validation
- Comprehensive logging and monitoring
- Docker containerization
- Health check endpoints

## Security

- All S3 data encrypted (AES-256)
- TLS 1.3 for API calls
- Input validation and sanitization
- PII detection and redaction
- Access logging and audit trails