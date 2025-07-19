# M&A Research Assistant MCP Server - Technical Specifications

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Technology Stack](#technology-stack)
3. [MCP Tools Implementation](#mcp-tools-implementation)
4. [Data Models](#data-models)
5. [S3 Storage Structure](#s3-storage-structure)
6. [API Integration](#api-integration)
7. [Caching Strategy](#caching-strategy)
8. [Error Handling](#error-handling)
9. [Performance Requirements](#performance-requirements)
10. [Security Implementation](#security-implementation)
11. [Deployment Configuration](#deployment-configuration)

## System Architecture

### Technology Stack
- **Language**: Python 3.11+
- **MCP Framework**: FastMCP 2.9+ (configured for streamable HTTP as default, STDIO only if requested)
- **Storage**: AWS S3
- **Web Scraping**: Beautiful Soup 4, Requests
- **LinkedIn Data**: Apify API
- **LLM Integration**: AWS Bedrock (Claude 3.5 Sonnet, Nova Pro)
- **Data Processing**: Pandas, JSON

### External Dependencies

**NOTE: Always review library websites to get the latest version of software and use those. The versions listed below are minimums. Example review: https://pypi.org/ for Python packages, https://www.npmjs.com/ for Node.js packages, and https://www.nuget.org/ for .NET packages.**

```python
fastmcp>=2.9.0
boto3>=1.28.0
beautifulsoup4>=4.12.0
requests>=2.31.0
botocore>=1.31.0  # For Bedrock API
pandas>=2.0.0
pydantic>=2.0.0
python-dateutil>=2.8.0
aiohttp>=3.9.0
tenacity>=8.2.0  # For retry logic
openpyxl>=3.1.0  # For XLSX export functionality
xlsxwriter>=3.1.0  # Alternative XLSX writer
```

## MCP Tools Implementation

### Tool Registry
The server implements 19 MCP tools organized into categories:

#### Core Analysis Tools
1. `analyze_company` - Orchestrates complete company analysis
2. `scrape_website` - Intelligent website scraping with priority keywords
3. `get_linkedin_data` - Fetches LinkedIn data via Apify API
4. `score_dimension` - Generic scoring function for any dimension
5. `enrich_company_data` - Enhance data from additional sources

#### History & Comparison Tools
6. `get_company_history` - Retrieves all analyses for a company
7. `compare_analyses` - Compares two analyses

#### Bulk Operations
8. `bulk_analyze` - Parallel multi-company analysis
9. `bulk_filter` - Filter multiple companies against criteria
10. `run_custom_scoring` - Run specific scoring systems

#### Search & Export Tools
11. `search_companies` - Search analyzed companies by criteria
12. `export_report` - Generate formatted reports
13. `generate_xlsx_export` - Generate downloadable XLSX files

#### Lead Management Tools
14. `qualify_lead` - Complete multi-tier qualification
15. `generate_investment_thesis` - AI-powered thesis generation
16. `manage_lead_nurturing` - Update lead tier and activities

#### Configuration Tools
17. `manage_scoring_systems` - Create/manage custom scoring systems
18. `override_company_tier` - Manual tier override
19. `manage_company_lists` - Manage active/future lists
20. `update_metadata` - Manual metadata updates

### Tool Input/Output Schemas

#### analyze_company
```python
Input:
{
    "company_name": str,
    "website_url": str,
    "linkedin_url": str,
    "force_refresh": bool = False,
    "skip_filtering": bool = False,
    "manual_override": bool = False
}

Output:
{
    "success": bool,
    "is_qualified": bool,
    "filtering_result": FilteringResult,
    "s3_path": str,
    "analysis_summary": {...},
    "error": str
}
```

[Additional tool schemas continue...]

## Data Models

### Core Models

```python
class ScoringSystem(BaseModel):
    system_id: str
    system_name: str
    owner: str
    is_active: bool = True
    is_default: bool = False
    created_at: str
    updated_at: str
    dimensions: List[ScoringDimension]
    weights: Dict[str, float]
    thresholds: Dict[str, float]
    custom_prompts: Dict[str, str] = {}
    custom_rules: Dict[str, Any] = {}

class AnalysisResult(BaseModel):
    company_name: str
    analysis_timestamp: str
    website_url: str
    linkedin_url: Optional[str]
    list_type: str  # "active" or "future_candidate"
    qualification_result: QualificationResult
    scoring_results: Dict[str, ScoringSystemResult]
    default_scores: Dict[str, ScoreDimension]
    overall_score: float
    recommendation: str
    key_strengths: List[str]
    key_concerns: List[str]
    automated_tier: str
    manual_tier_override: Optional[str] = None
    override_metadata: Optional[OverrideMetadata] = None
    effective_tier: str
    likelihood_factors: Dict[str, Optional[str]]
    investment_thesis: Optional[dict] = None
    nurturing_plan: Optional[dict] = None
    metadata: AnalysisMetadata
    export_metadata: Optional[ExportMetadata] = None

class CompanyList(BaseModel):
    list_type: str
    company_name: str
    added_date: str
    added_by: str
    automated_tier: str
    automated_score: float
    manual_tier_override: Optional[str] = None
    override_reason: Optional[str] = None
    override_by: Optional[str] = None
    override_date: Optional[str] = None
    monitoring_frequency: str
    alert_thresholds: Dict[str, float]
    promotion_criteria_met: bool = False
    promotion_blockers: List[str] = []
```

## S3 Storage Structure

```
s3://ma-research-bucket/
├── companies/
│   ├── {sanitized-company-name}/
│   │   ├── {ISO-8601-timestamp}/
│   │   │   ├── analysis.json
│   │   │   ├── raw_website_content.json
│   │   │   ├── linkedin_data.json
│   │   │   ├── metadata.json
│   │   │   ├── scoring/
│   │   │   │   ├── default.json
│   │   │   │   ├── {system-id}.json
│   │   │   │   └── scoring_summary.json
│   │   │   └── overrides.json
│   │   ├── latest/
│   │   └── company_metadata.json
│   └── _index/
│       ├── active_companies.json
│       ├── future_candidates.json
│       ├── companies_list.json
│       └── analysis_calendar.json
├── scoring_systems/
│   ├── default/
│   │   ├── configuration.json
│   │   └── prompts.json
│   ├── {system-id}/
│   │   ├── configuration.json
│   │   ├── prompts.json
│   │   └── metadata.json
│   └── _registry.json
├── reports/
│   ├── {report-id}/
│   │   └── report.{format}
│   └── _templates/
├── exports/
│   └── {export-date}/
│       ├── full_export.json
│       └── xlsx_exports/
│           └── {export-id}.xlsx
└── config/
    ├── scoring_weights.json
    ├── system_config.json
    └── list_management.json
```

### S3 Configuration
```python
{
    "bucket_name": "ma-research-bucket",
    "region": "us-east-1",
    "storage_class": "STANDARD_IA",
    "encryption": "AES256",
    "versioning": True,
    "lifecycle_rules": [...],
    "cors_rules": [...]
}
```

## API Integration

### AWS Bedrock Configuration
```python
class BedrockLLMService:
    def __init__(self, region="us-east-1"):
        self.bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region
        )
        self.primary_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        self.fallback_model = "amazon.nova-pro-v1:0"
```

### Apify LinkedIn Integration
```python
APIFY_CONFIG = {
    "actor_id": "linkedin-company-scraper",
    "timeout_secs": 300,
    "memory_mbytes": 256,
    "max_retries": 3
}
```

### Rate Limiting
```python
RATE_LIMITS = {
    "bedrock_api": {
        "requests_per_minute": 100,
        "tokens_per_minute": 200000,
        "max_concurrent_requests": 10
    },
    "apify_api": {
        "requests_per_hour": 100
    },
    "web_scraping": {
        "requests_per_second_per_domain": 1,
        "concurrent_domains": 5
    }
}
```

## Caching Strategy

### Cache Configuration
- Website content: 24 hours
- LinkedIn data: 7 days
- Analysis results: Indefinite (immutable)
- Paid API responses: 30 days
- Implementation: Redis or local file cache

### Cache Keys Pattern
```
company:{company_name}:website:{url_hash}
company:{company_name}:linkedin:{profile_id}
company:{company_name}:analysis:{timestamp}
scoring_system:{system_id}:config
```

## Error Handling

### Error Categories

#### Web Scraping Errors
- ConnectionTimeout: Retry with exponential backoff
- 404 NotFound: Mark as invalid URL, continue
- 403 Forbidden: Try alternative user agents
- RateLimited: Implement backoff, queue for later

#### API Errors
- Bedrock: Token limits, throttling, model unavailable
- Apify: Rate limits, invalid credentials
- S3: Access denied, upload failures

### Recovery Strategies
1. Partial results always saved
2. Retry queue with exponential backoff
3. Fallback sources (archive.org)
4. Manual review flagging

## Performance Requirements

### Response Time SLAs
- Single company analysis: < 60 seconds
- Bulk analysis (10 companies): < 5 minutes
- Search operations: < 2 seconds
- Report generation: < 10 seconds

### Resource Limits
```python
RESOURCE_LIMITS = {
    "max_memory_per_analysis": "512MB",
    "max_website_content_size": "10MB",
    "max_pages_per_company": 10,
    "max_analysis_time": 300,
    "max_retry_attempts": 3
}
```

### Concurrency Limits
- Maximum parallel analyses: 5
- Maximum concurrent web scraping: 10
- Maximum concurrent S3 operations: 20
- LLM API concurrent requests: 3

## Security Implementation

### Authentication & Authorization
```python
class SecurityConfig:
    api_key_rotation_days = 90
    encrypt_sensitive_data = True
    audit_all_operations = True
    allowed_ip_ranges = ["10.0.0.0/8"]
    require_mfa_for_exports = True
```

### Data Protection
1. Encryption at Rest: AES-256
2. Encryption in Transit: TLS 1.3
3. API Key Management: AWS Secrets Manager
4. PII Handling: Detection and redaction
5. Access Logging: CloudTrail

### Input Validation
```python
VALIDATION_RULES = {
    "company_name": {
        "max_length": 100,
        "allowed_chars": "alphanumeric, spaces, hyphens",
        "required": True
    },
    "website_url": {
        "pattern": r"^https?://[\w\-\.]+(\.[\w\-]+)+[/#?]?.*$",
        "max_length": 500,
        "required": True
    }
}
```

## Deployment Configuration

### Docker Configuration
```dockerfile
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV AWS_DEFAULT_REGION=us-east-1
ENV BEDROCK_REGION=us-east-1

HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["fastmcp", "serve", "ma_research_mcp"]
```

### Environment Variables
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
S3_BUCKET_NAME=ma-research-bucket

# API Keys
APIFY_API_TOKEN=xxx

# AWS Bedrock Configuration
BEDROCK_REGION=us-east-1
BEDROCK_PRIMARY_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_FALLBACK_MODEL=amazon.nova-pro-v1:0

# MCP Configuration
MCP_SERVER_NAME=ma-research-assistant
MCP_SERVER_VERSION=1.0.0

# Feature Flags
ENABLE_CACHING=true
MAX_PARALLEL_ANALYSES=5

# Lead Qualification
QUALIFICATION_MINIMUM_SCORE=7.0
TIER_VIP_THRESHOLD=9.0
```

### Health Check Endpoints
- `/health` - Basic liveness check
- `/ready` - Check all dependencies
- `/metrics` - Prometheus metrics
- `/xlsx/status` - XLSX export service status

### Monitoring & Alerting
1. CloudWatch metrics for S3 operations
2. Bedrock API response time tracking
3. Error rate monitoring
4. Cost tracking and alerts
5. Analysis success rate dashboards