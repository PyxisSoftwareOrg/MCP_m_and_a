# M&A Research Assistant MCP Server - Product Requirements Document

## Executive Summary

The M&A Research Assistant MCP Server is a comprehensive tool for evaluating software companies as potential acquisition targets. It automates the analysis of companies across 8 key dimensions by scraping web content and LinkedIn data, applying sophisticated scoring algorithms, and storing results in AWS S3 with full version history.

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Core Components](#core-components)
3. [Scoring Dimensions](#scoring-dimensions)
4. [MCP Tools Specification](#mcp-tools-specification)
5. [Data Models](#data-models)
6. [S3 Storage Structure](#s3-storage-structure)
7. [Implementation Requirements](#implementation-requirements)
8. [Error Handling](#error-handling)
9. [Performance Requirements](#performance-requirements)
10. [Security Considerations](#security-considerations)

## System Architecture

### Technology Stack
NOTE: Always review sites to get the latest version of software and use those.  The versions listed below are minimums.  Example review: https://pypi.org/ and other sites like npmjs and nuget.
- **Language**: Python 3.11+
- **MCP Framework**: FastMCP 2.9+
- **Storage**: AWS S3
- **Web Scraping**: Beautiful Soup 4, Requests
- **LinkedIn Data**: Apify API
- **LLM Integration**: AWS Bedrock (Claude 3.5 Sonnet, Nova Pro)
- **Data Processing**: Pandas, JSON

### External Dependencies
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

## Web Sources for Company Information

### Free Access Sources

#### General Business Information
- **Company Websites**: Primary source for products, services, pricing, and team information
- **LinkedIn Company Pages**: Employee count, growth metrics, company updates, leadership
- **Crunchbase (Limited)**: Basic company info, funding rounds, employee estimates
- **AngelList**: Startup information, funding, team, and job postings
- **Glassdoor**: Employee reviews, salary data, company culture insights
- **Indeed Company Pages**: Job postings, company reviews, size indicators
- **Google My Business**: Local business information, reviews, contact details

#### Financial & Legal Information
- **SEC EDGAR Database**: Public company filings, financial statements, insider trading
- **OpenCorporates**: Corporate registration data, officers, filing history
- **Hoovers (Basic)**: Limited company profiles and contact information
- **Yellow Pages**: Business listings, contact information, basic company data
- **Better Business Bureau**: Business ratings, complaints, accreditation status

#### Industry & Market Data
- **Google News/Alerts**: Recent company news, press releases, market mentions
- **PRNewswire**: Press releases, company announcements
- **Business Wire**: Corporate news, financial results, product launches
- **Industry Association Websites**: Member directories, industry reports
- **Trade Publications**: Industry-specific news and company coverage

#### Technology & Product Information
- **Product Hunt**: Product launches, user reviews, technology stack
- **GitHub**: Open source projects, developer activity, technology choices
- **Stack Overflow**: Technology usage, developer community presence
- **G2 Crowd**: Software reviews, competitor comparisons, market position
- **Capterra**: Software listings, user reviews, pricing information

#### Archive & Historical Data
- **Wayback Machine**: Historical website versions, company evolution
- **Library of Congress**: Historical business records, patents
- **Google Cache**: Recent website changes, content history

### Paid Access Sources

#### Premium Business Intelligence
- **Crunchbase Pro** ($29-99/month): Comprehensive startup data, advanced search, API access
- **PitchBook** ($3,000+/year): Private market data, detailed financials, deal flow
- **CB Insights** ($1,000+/year): Market intelligence, startup tracking, trend analysis
- **Owler** ($35-840/month): Company news, competitive intelligence, alerts

#### Financial & Market Data
- **Bloomberg Terminal** ($2,000+/month): Real-time financial data, news, analytics
- **S&P Capital IQ** ($12,000+/year): Financial data, market analysis, company profiles
- **FactSet** ($1,000+/month): Financial data, portfolio analytics, market intelligence
- **Refinitiv (Thomson Reuters)** ($500+/month): Financial data, news, analytics
- **Hoovers Premium** ($300+/month): Detailed company profiles, contact data

#### Contact & Sales Intelligence
- **ZoomInfo** ($79-400/month): Contact data, company information, technographics
- **Apollo** ($39-79/month): Sales intelligence, contact database, company insights
- **Clearbit** ($99-999/month): Company data enrichment, technographics, contact info
- **DiscoverOrg** ($300+/month): Contact data, organizational charts, technology usage
- **Leadfeeder** ($53-199/month): Website visitor identification, company tracking

#### Industry & Market Research
- **IBISWorld** ($1,000+/year): Industry reports, market analysis, company performance
- **Euromonitor** ($5,000+/year): Market research, consumer data, industry trends
- **Gartner** ($15,000+/year): Technology research, market analysis, vendor ratings
- **Forrester** ($10,000+/year): Technology research, market forecasts, buyer insights

#### Technology & Competitive Intelligence
- **SimilarWeb Pro** ($199-799/month): Website traffic, competitive analysis, market share
- **Alexa Pro** ($99-499/month): Website analytics, competitive intelligence
- **BuiltWith Pro** ($295-995/month): Technology stack analysis, lead generation
- **Wappalyzer** ($50-250/month): Technology profiling, market analysis
- **Datanyze** ($21-169/month): Technology adoption, company technographics

#### Legal & Compliance
- **Westlaw** ($89-500/month): Legal research, case law, regulatory information
- **LexisNexis** ($100-400/month): Legal and business research, public records
- **Dun & Bradstreet** ($50-500/month): Business credit, risk assessment, company data
- **Experian Business** ($39-199/month): Business credit, risk analysis, company profiles

#### Specialized Industry Sources
- **Healthcare**: HIMSS Analytics, Definitive Healthcare, Healthcare Financial Management
- **Technology**: Gartner, IDC, TechCrunch Pro, VentureBeat Intelligence
- **Financial Services**: SNL Financial, Dealogic, Thomson ONE
- **Manufacturing**: ThomasNet, IndustryWeek, Manufacturing News
- **Retail**: Retail Dive, Chain Store Age, RetailNext

### Source Integration Strategy

#### Data Collection Priority
1. **Tier 1 (Always Scrape)**: Company website, LinkedIn, basic Crunchbase
2. **Tier 2 (Conditional)**: Industry-specific sources, news mentions
3. **Tier 3 (Premium)**: Paid sources for high-value targets

#### API Integration Capabilities
```python
SUPPORTED_APIS = {
    "free_apis": [
        "linkedin_company_api",
        "crunchbase_basic",
        "sec_edgar_api",
        "opencorporates_api",
        "github_api"
    ],
    "paid_apis": [
        "crunchbase_pro",
        "clearbit_api",
        "zoominfo_api",
        "similarweb_api",
        "builtwith_api",
        "pitchbook_api"
    ]
}
```

#### Data Quality Scoring
```python
SOURCE_RELIABILITY_SCORES = {
    "primary_sources": {
        "company_website": 0.9,
        "sec_filings": 0.95,
        "linkedin_company": 0.8
    },
    "secondary_sources": {
        "crunchbase": 0.7,
        "news_articles": 0.6,
        "review_sites": 0.5
    },
    "third_party_aggregators": {
        "paid_databases": 0.8,
        "free_databases": 0.6,
        "social_media": 0.4
    }
}
```

## Core Components

### 1. Web Scraping Engine
- Fetch and parse HTML content
- Convert HTML to markdown for text extraction
- Extract and prioritize links based on relevance
- Recursive scraping of up to 3 priority subpages
- Handle JavaScript-rendered content where possible
- Respect robots.txt and implement polite crawling

### 2. LinkedIn Integration
- Integration with Apify LinkedIn Company Scraper API
- Extract company metadata (age, size, growth)
- Handle API rate limits and errors
- Cache LinkedIn data to minimize API calls

### 3. LLM Analysis Engine
- Integration with AWS Bedrock
- Support for Claude 3.5 Sonnet and Nova Pro models
- Structured prompt engineering for consistent scoring
- JSON schema validation for LLM outputs
- Fallback to alternative models if primary fails
- Cost optimization through model selection based on task complexity

### 4. S3 Storage Manager
- Handle all S3 operations (read, write, list)
- Manage folder structure and naming conventions
- Implement versioning and lifecycle policies
- Local caching for performance optimization

## Lead Qualification & Filtering System

The system implements a multi-tier filtering and scoring approach to identify high-quality acquisition targets. Companies must pass through multiple qualification gates before receiving detailed analysis.

### Target Quality Threshold
- **Minimum Average Score**: 7.0/10.0 across all qualification dimensions
- **Review Process**: BD (Lead Owner) and Executive (CEO, PM, VP M&A) assessment
- **Scoring Framework**: 5 core qualification questions + likelihood factors

### CUT #1: Initial Filtering Criteria

#### 1. Geographic Requirements
- **North America**: Any vertical market software company
- **United Kingdom**: Sports & Fitness vertical ONLY
- **Disqualified**: All other geographic regions

#### 2. Business Model Requirements
- **Software Business**: Must be primarily a software company
  - ❌ **EXCLUDE**: Development shops, consulting services, pure services
  - ✅ **INCLUDE**: Heavy recurring service business IF it complements existing VMS
- **B2B Focus**: Must predominantly serve Business-to-Business customers
  - ❌ **EXCLUDE**: Pure B2C companies, consumer marketplaces
  - ✅ **INCLUDE**: Some B2C components IF they complement existing VMS

#### 3. Solution Type Requirements
- **VMS-Compatible**: Must align with vertical market software strategy
  - ❌ **EXCLUDE**: Marketplace solutions, platforms connecting buyers/sellers
  - ❌ **EXCLUDE**: Horizontal software without vertical focus
  - ✅ **INCLUDE**: Industry-specific software solutions

### CUT #2: Size & Maturity Requirements

#### 1. Revenue & Scale Requirements
- **Minimum Revenue**: >$1M annually OR 10+ FTE
- **Exception**: Fast-growing companies or strategic tuck-in opportunities
- **Profit**: No specific EBITDA requirement (opportunity to improve)
- **Risk Assessment**: Consider key personnel and revenue concentration risks

#### 2. Company Maturity Requirements
- **Founding Year**: Must be >4 years old (excludes companies founded <4 years ago)
- **Recent Funding/Sale**: Exclude companies with funding/sale <18 months ago
- **Stability**: Must demonstrate business model validation and market traction

#### 3. Strategic Fit Requirements
- **Tuck-in Potential**: Can be smaller if strategic fit with existing VMS
- **Growth Trajectory**: Fast growth can offset smaller current size
- **Market Position**: Established presence in target vertical

### Core Qualification Questions (Q1-Q5)

#### Q1: Horizontal vs Vertical (Score: 0-10)
- **Definition**: "Only include prospects that serve selected vertical markets"
- **Scoring**:
  - 10: Pure vertical solution for specific sub-industry
  - 8-9: Industry-specific with deep vertical focus
  - 6-7: Some vertical tailoring but serves multiple industries
  - 4-5: Loosely connected to verticals
  - 1-3: Horizontal solution with minimal vertical focus
  - 0: Pure horizontal/generic solution

#### Q2: Point vs Suite (Score: 0-10)
- **Definition**: Evaluate solution comprehensiveness and workflow coverage
- **Scoring**:
  - 10: Complete end-to-end platform covering all critical workflows
  - 8-9: Comprehensive suite covering most critical workflows
  - 6-7: Covers 1-2 critical workflows with expansion potential
  - 4-5: Niche component of critical workflow
  - 1-3: Non-critical workflow component
  - 0: Peripheral functionality only

#### Q3: Mission Critical (Score: 0-10)
- **Definition**: Assess how critical the solution is to customer operations
- **Scoring**:
  - 10: Business-critical, customers cannot operate without it
  - 8-9: Essential for daily operations, high switching costs
  - 6-7: Important but alternatives exist
  - 4-5: Nice-to-have, provides efficiency gains
  - 1-3: Optional tool, low switching costs
  - 0: Discretionary spending

#### Q4: OPM vs Own Money (Score: 5 or 10)
- **Definition**: Government/public funding vs private sector revenue
- **Scoring**:
  - 10: Government entities or government-funded programs
  - 5: Private sector customers

#### Q5: ARPU (Annual Revenue Per User) (Score: 5-10)
- **Definition**: Annual pricing levels per customer/user
- **Scoring**:
  - 10: >$40,000 annually
  - 9: $30,000-$39,999
  - 8: $10,000-$29,999
  - 7: $3,000-$9,999
  - 6: $2,000-$2,999
  - 5: <$2,000

### Likelihood Assessment Factors

#### Market & Competitive Position
- **Payment Processing**: Revenue model and payment mechanisms
- **Customer Concentration**: Risk assessment of customer dependency
- **Growth Trajectory**: Historical and projected growth patterns
- **TAM & Competition**: Market size and competitive landscape

#### Organizational Factors
- **Number & Location of Staff**: Team size and geographic distribution
- **Seller's Growth Ambitions**: Management's expansion goals
- **Seller's Challenges**: Current business challenges and pain points
- **Ownership & Changes**: Current ownership structure and recent changes

#### Transaction Readiness
- **Value Expectations**: Owner's price expectations and valuation basis
- **Sale Timing**: Timeline and urgency for potential transaction
- **Owner Motivations**: Primary drivers for considering a sale
- **What is Motivating Sale**: Specific catalysts (retirement, growth capital, etc.)

### Filtering Rules Configuration

```python
FILTERING_RULES = {
    "cut_1": {
        "geography": {
            "allowed_regions": ["North America", "United States", "Canada", "Mexico"],
            "uk_verticals_only": ["Sports", "Fitness", "Recreation", "Wellness", "Athletics"],
            "blocked_regions": ["Europe (except UK)", "Asia", "Africa", "South America", "Australia"]
        },
        "business_model": {
            "excluded_keywords": [
                "development shop", "consulting", "agency", "marketplace", 
                "platform connecting", "freelancer platform", "gig economy",
                "pure services", "implementation services"
            ],
            "b2c_disqualifiers": [
                "consumer app", "direct to consumer", "B2C marketplace",
                "social media", "gaming", "entertainment"
            ]
        },
        "solution_type": {
            "excluded_types": [
                "marketplace", "two-sided platform", "aggregator",
                "comparison site", "lead generation", "advertising platform"
            ]
        }
    },
    "cut_2": {
        "size_requirements": {
            "min_revenue_usd": 1000000,  # $1M
            "min_fte_alternative": 10,
            "founding_year_cutoff": 4,  # Must be >4 years old
            "recent_funding_exclusion_months": 18
        },
        "growth_exceptions": {
            "fast_growth_threshold": 0.5,  # 50% YoY growth
            "tuck_in_revenue_minimum": 500000,  # $500K for strategic tuck-ins
            "strategic_fit_override": True
        }
    },
    "quality_thresholds": {
        "minimum_average_score": 7.0,
        "individual_score_minimum": 5.0,
        "critical_question_weights": {
            "q1_vertical": 0.25,
            "q2_suite": 0.20,
            "q3_mission_critical": 0.25,
            "q4_opm": 0.15,
            "q5_arpu": 0.15
        }
    }
}
```

### Multi-Tier Qualification Process

#### Stage 1: Initial Filtering (CUT #1)
1. **Geographic Check**: Extract company location from LinkedIn/website
2. **Business Model Analysis**: Analyze company description and services
3. **Market Type Detection**: Identify if B2B, B2C, or marketplace
4. **VMS Alignment**: Assess vertical market focus

#### Stage 2: Size & Maturity Filter (CUT #2)
1. **Revenue Verification**: Confirm >$1M revenue or >10 FTE
2. **Maturity Assessment**: Verify >4 years in business
3. **Recent Activity Check**: Exclude recent funding/sales (<18 months)
4. **Strategic Exception Review**: Evaluate tuck-in potential

#### Stage 3: Quality Scoring (Q1-Q5)
1. **Qualification Questions**: Score each of the 5 core dimensions
2. **Average Calculation**: Must achieve >7.0/10 average
3. **Individual Minimums**: No score below 5.0 on critical questions
4. **Executive Review**: BD and Executive assessment alignment

#### Stage 4: Likelihood Assessment
1. **Market Position Analysis**: Competitive and growth factors
2. **Organizational Readiness**: Team and operational factors
3. **Transaction Potential**: Seller motivations and timing

### Qualification Results

```python
class QualificationResult(BaseModel):
    company_name: str
    is_qualified: bool
    overall_quality_score: float  # 0.0 to 10.0
    
    # Multi-tier filtering results
    cut_1_passed: bool
    cut_2_passed: bool
    quality_threshold_met: bool
    
    # Individual question scores
    q1_horizontal_vertical: float  # 0-10
    q2_point_suite: float  # 0-10
    q3_mission_critical: float  # 0-10
    q4_opm_own_money: float  # 5 or 10
    q5_arpu: float  # 5-10
    
    # Size and maturity
    estimated_revenue: Optional[float]
    estimated_fte: Optional[int]
    company_age_years: Optional[int]
    recent_funding_date: Optional[str]
    
    # Likelihood factors
    likelihood_score: float  # 0.0 to 10.0
    transaction_readiness: str  # "high", "medium", "low"
    
    # Classification
    lead_tier: str  # "VIP", "HIGH", "MEDIUM", "LOW", "DISQUALIFIED"
    requires_executive_review: bool = False
    disqualification_reasons: List[str] = []
    
class QualificationScores(BaseModel):
    vertical_focus: float
    solution_comprehensiveness: float
    business_criticality: float
    funding_source: float
    pricing_level: float
    weighted_average: float
    
class LikelihoodFactors(BaseModel):
    market_position: float
    growth_trajectory: float
    competitive_moat: float
    customer_concentration_risk: float
    management_motivation: float
    transaction_timing: float
    value_expectations_alignment: float
    
class LeadClassification(BaseModel):
    tier: str  # VIP, HIGH, MEDIUM
    nurturing_strategy: str
    bd_contact_frequency: str
    executive_involvement_level: str
    priority_score: float
```

## Lead Nurturing & Cohort Management System

### Nurturing Framework (Middle of Funnel)

#### Lead Cohort Classification
```python\nLEAD_TIERS = {\n    \"VIP\": {\n        \"criteria\": \"Overall score 9.0+, strategic fit, immediate opportunity\",\n        \"bd_contact_frequency\": \"Weekly\",\n        \"executive_involvement\": \"Direct CEO/VP M&A engagement\",\n        \"in_person_priority\": \"Top 10-15 targets\",\n        \"activities\": [\"Executive dinners\", \"Site visits\", \"Advisory relationships\"]\n    },\n    \"HIGH\": {\n        \"criteria\": \"Overall score 8.0-8.9, strong strategic fit\",\n        \"bd_contact_frequency\": \"Bi-weekly\",\n        \"executive_involvement\": \"PM/VP M&A quarterly\",\n        \"activities\": [\"Industry events\", \"Webinars\", \"Advisory calls\"]\n    },\n    \"MEDIUM\": {\n        \"criteria\": \"Overall score 7.0-7.9, potential fit\",\n        \"bd_contact_frequency\": \"Monthly\",\n        \"executive_involvement\": \"BD managed with exec review\",\n        \"activities\": [\"Newsletters\", \"Industry reports\", \"Quarterly check-ins\"]\n    }\n}\n```\n\n#### Nurturing Activities & Expectations\n\n**VIP Tier (Top 10-15 Companies)**\n- **Executive Focus**: Direct CEO, PM, or VP M&A involvement\n- **In-Person Planning**: Build 12-month contact strategy\n- **Relationship Building**: Advisory roles, industry partnerships\n- **Communication**: Personalized outreach, exclusive content\n\n**HIGH Tier**\n- **BD Management**: Primary BD ownership with executive oversight\n- **Regular Engagement**: Bi-weekly touchpoints, value-add content\n- **Relationship Nurturing**: Industry event invitations, expert connections\n\n**MEDIUM Tier**\n- **Automated Nurturing**: Newsletter campaigns, industry insights\n- **Quarterly Reviews**: BD assessment and tier re-evaluation\n- **Opportunistic Engagement**: Event-driven outreach\n\n#### Sales Plan Framework\n\nEach acquisition target (AD) requires a customized sales plan:\n\n```python\nSALES_PLAN_TEMPLATE = {\n    \"company_profile\": {\n        \"qualification_scores\": \"Q1-Q5 detailed breakdown\",\n        \"likelihood_assessment\": \"Transaction readiness factors\",\n        \"strategic_fit\": \"VMS alignment and synergies\",\n        \"key_contacts\": \"Decision makers and influencers\"\n    },\n    \"engagement_strategy\": {\n        \"primary_value_proposition\": \"Tailored messaging\",\n        \"content_strategy\": \"Industry-specific materials\",\n        \"relationship_mapping\": \"Contact hierarchy and approach\",\n        \"timeline\": \"12-month engagement roadmap\"\n    },\n    \"activity_expectations\": {\n        \"bd_activities\": \"Monthly targets and KPIs\",\n        \"executive_activities\": \"Quarterly goals and metrics\",\n        \"success_metrics\": \"Advancement milestones\",\n        \"review_cadence\": \"Progress assessment schedule\"\n    }\n}\n```\n\n### Investment Thesis Generation\n\n#### AI-Powered Thesis Development\n- **Agent Training**: Specialized ChatGPT Pro agent for investment analysis\n- **Data Integration**: Pull core company data from Salesforce\n- **Thesis Components**: Strategic rationale, synergies, valuation framework\n- **Executive Review**: Guided suggestions for investment committee\n\n#### Thesis Framework Elements\n```python\nINVESTMENT_THESIS_COMPONENTS = {\n    \"strategic_rationale\": {\n        \"vms_alignment\": \"Vertical market fit analysis\",\n        \"portfolio_synergies\": \"Cross-selling and integration opportunities\",\n        \"market_expansion\": \"Geographic or product expansion potential\",\n        \"competitive_advantage\": \"Unique positioning and moats\"\n    },\n    \"financial_profile\": {\n        \"revenue_quality\": \"Recurring vs one-time revenue\",\n        \"growth_trajectory\": \"Historical and projected growth\",\n        \"profitability_path\": \"EBITDA improvement opportunities\",\n        \"valuation_framework\": \"Multiple and pricing considerations\"\n    },\n    \"execution_factors\": {\n        \"integration_complexity\": \"Technical and operational integration\",\n        \"management_retention\": \"Key personnel and cultural fit\",\n        \"customer_retention\": \"Customer concentration and satisfaction\",\n        \"risk_mitigation\": \"Key risks and mitigation strategies\"\n    }\n}\n```\n\n### CRM Integration & Data Flow\n\n#### Salesforce Integration\n- **Data Synchronization**: Bi-directional sync with MCP analysis results\n- **Lead Scoring**: Automated Q1-Q5 scoring updates\n- **Activity Tracking**: BD and executive engagement logging\n- **Pipeline Management**: Stage progression and probability updates\n\n#### Communication Systems\n- **Newsletter Automation**: Tier-specific content delivery\n- **Event Coordination**: Industry event planning and follow-up\n- **Executive Calendar**: Strategic meeting scheduling and preparation\n\n## Scoring Dimensions

### 1. Vertical Market Software (VMS) Score
**Range**: 0-5  
**Purpose**: Evaluate how tailored the software is to specific industries

| Score | Description | Example |
|-------|-------------|---------|
| 5 | Pure VMS for sub-verticals | EHR for long-term care facilities |
| 4 | Industry-specific software | Generic healthcare EHR |
| 3 | Software for related industries | Compliance for regulated industries |
| 2 | Loosely connected industries | Job scheduling for field services |
| 1 | Minimal vertical tailoring | CRM with industry add-ons |
| 0 | Industry-agnostic | Microsoft Excel |

### 2. Revenue Model Score
**Range**: 0-5  
**Purpose**: Assess percentage of revenue from software licenses vs services/hardware

| Score | Revenue from Software |
|-------|----------------------|
| 5 | 90-100% |
| 4 | 80-90% |
| 3 | 70-80% |
| 2 | 60-70% |
| 1 | 50-60% |
| 0 | <50% |

### 3. Suite vs Point Solution Score
**Range**: 0-5  
**Purpose**: Evaluate solution comprehensiveness

| Score | Description |
|-------|-------------|
| 5 | End-to-end platform |
| 4 | Covers most critical workflows |
| 3 | Covers 1-2 critical workflows |
| 2 | Niche component of critical workflow |
| 1 | Non-critical workflow component |
| 0 | Peripheral functionality |

### 4. Customer Base Quality Score
**Range**: 0-5  
**Purpose**: Assess barriers to entry in target industries

| Score | Barrier Level | Example Industries |
|-------|--------------|-------------------|
| 5 | Very High | Healthcare, Aerospace, Defense |
| 4 | High | Financial Services, Banking, Insurance |
| 3 | Medium | Construction, Real Estate, Agriculture |
| 2 | Low | Restaurants, Retail, Beauty Salons |
| 1 | Very Low | Fitness Studios, Tutoring, Food Trucks |
| 0 | None | Direct to Consumer apps |

### 5. Pricing Score
**Range**: 5-10  
**Purpose**: Evaluate annual pricing levels

| Score | Annual Price |
|-------|-------------|
| 10 | >$40,000 |
| 9 | $30,000-$39,999 |
| 8 | $10,000-$29,999 |
| 7 | $3,000-$9,999 |
| 6 | $2,000-$2,999 |
| 5 | <$2,000 |

**Assumptions**:
- For per-user pricing: assume 20 users
- Average cost of add-on modules included
- Use competitor pricing if not available (marked with asterisk)

### 6. Other People's Money (OPM) Score
**Range**: 5 or 10  
**Purpose**: Assess government/public funding dependency

| Score | Customer Type |
|-------|--------------|
| 10 | Government entities or government-funded programs |
| 5 | Private sector |

### 7. Size, Growth & Age Score
**Range**: 5-9  
**Purpose**: Evaluate company maturity and growth trajectory

| Score | Criteria |
|-------|----------|
| 9 | 20+ years, 100+ FTE, <5% YoY growth OR 20+ years, 20+ FTE, <10% YoY |
| 8 | 20+ years, 100+ FTE, 6-10% YoY growth OR 20+ years, 20+ FTE, <20% YoY |
| 7 | 10+ years, 10+ FTE, <30% YoY OR <10 years, 10+ FTE, <70% YoY |
| 6 | 40-100% YoY growth at any stage |
| 5 | >100% YoY growth OR 15+ years, <10 FTE, stagnant |

### 8. Ownership Profile Score
**Range**: 5-9  
**Purpose**: Evaluate funding vs revenue ratio

| Score | Funding vs Revenue (assuming $100K/FTE) |
|-------|----------------------------------------|
| 9 | No funding (bootstrapped) |
| 8 | Funding <10% of revenue (10+ years old) |
| 7 | Funding <30% of revenue (10+ years old) |
| 6 | Funding <50% of revenue (10+ years old) |
| 5 | Funding >100% of revenue |

## MCP Tools Specification

### 1. `analyze_company`
**Description**: Orchestrates complete company analysis with pre-filtering

**Input Schema**:
```python
{
    "company_name": str,  # Required
    "website_url": str,   # Required
    "linkedin_url": str,  # Optional
    "force_refresh": bool = False,  # Skip cache
    "skip_filtering": bool = False,  # Skip qualification filtering
    "manual_override": bool = False  # Override disqualification
}
```

**Output Schema**:
```python
{
    "success": bool,
    "is_qualified": bool,  # Passed all filtering criteria
    "filtering_result": FilteringResult,  # Detailed filtering breakdown
    "s3_path": str,  # s3://bucket/companies/company-name/timestamp/
    "analysis_summary": {
        "overall_score": float,
        "recommendation": str,  # "Strong Buy", "Buy", "Hold", "Pass", "DISQUALIFIED"
        "key_strengths": List[str],
        "key_concerns": List[str]
    },
    "error": str  # Only if success=False
}
```

### 2. `scrape_website`
**Description**: Scrapes website content with intelligent link following

**Input Schema**:
```python
{
    "url": str,
    "max_depth": int = 1,  # How many levels deep to crawl
    "max_pages": int = 3,  # Maximum pages to scrape
    "priority_keywords": List[str] = ["pricing", "products", "features", "customers", "about"],
    "additional_sources": List[str] = [],  # Additional URLs to scrape
    "source_priority": str = "primary"  # "primary", "secondary", "comprehensive"
}
```

**Output Schema**:
```python
{
    "main_content": str,
    "subpages": List[{
        "url": str,
        "content": str,
        "title": str
    }],
    "aggregated_content": str,
    "total_pages_scraped": int,
    "links_found": List[str]
}
```

### 3. `get_linkedin_data`
**Description**: Fetches LinkedIn company data via Apify

**Input Schema**:
```python
{
    "linkedin_url": str,
    "api_key": str  # Apify API key
}
```

**Output Schema**:
```python
{
    "company_name": str,
    "founded_year": int,
    "employee_count": int,
    "employee_range": str,
    "industry": str,
    "headquarters": str,
    "growth_metrics": {
        "current_employees": int,
        "previous_year_employees": int,
        "yoy_growth_percent": float
    },
    "funding_data": {
        "total_funding": float,
        "last_funding_date": str,
        "funding_rounds": List[dict]
    }
}
```

### 4. `score_dimension`
**Description**: Generic scoring function for any dimension

**Input Schema**:
```python
{
    "dimension": str,  # One of: vms, revenue_model, suite_vs_point, etc.
    "content": str,    # Website content or LinkedIn data
    "llm_model": str = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Default model
}
```

**Output Schema**:
```python
{
    "score": float,
    "explanation": str,
    "confidence": float,  # 0.0 to 1.0
    "evidence": List[str],  # Key phrases that influenced the score
    "is_estimated": bool
}
```

### 5. `get_company_history`
**Description**: Retrieves all analyses for a company

**Input Schema**:
```python
{
    "company_name": str,
    "limit": int = 10,
    "start_date": str = None,  # ISO format
    "end_date": str = None     # ISO format
}
```

**Output Schema**:
```python
{
    "company_name": str,
    "analyses": List[{
        "timestamp": str,
        "s3_path": str,
        "overall_score": float,
        "score_changes": dict  # Diff from previous analysis
    }],
    "total_count": int
}
```

### 6. `compare_analyses`
**Description**: Compares two analyses for the same company

**Input Schema**:
```python
{
    "company_name": str,
    "timestamp1": str,
    "timestamp2": str
}
```

**Output Schema**:
```python
{
    "company_name": str,
    "comparison": {
        "overall_score_change": float,
        "dimension_changes": Dict[str, {
            "old_score": float,
            "new_score": float,
            "change": float,
            "explanation": str
        }],
        "key_improvements": List[str],
        "key_deteriorations": List[str]
    }
}
```

### 7. `bulk_analyze`
**Description**: Analyzes multiple companies in parallel

**Input Schema**:
```python
{
    "companies": List[{
        "company_name": str,
        "website_url": str,
        "linkedin_url": str
    }],
    "max_parallel": int = 5
}
```

**Output Schema**:
```python
{
    "total_companies": int,
    "successful": int,
    "failed": int,
    "results": List[{
        "company_name": str,
        "success": bool,
        "s3_path": str,
        "error": str  # If failed
    }]
}
```

### 8. `search_companies`
**Description**: Search analyzed companies by criteria

**Input Schema**:
```python
{
    "filters": {
        "min_overall_score": float,
        "max_overall_score": float,
        "dimension_filters": Dict[str, {
            "min": float,
            "max": float
        }],
        "industries": List[str],
        "analyzed_after": str,  # ISO date
        "qualification_status": str = "qualified",  # "qualified", "disqualified", "all"
        "geographic_regions": List[str] = [],  # Filter by geography
        "business_models": List[str] = []  # Filter by business model
    },
    "sort_by": str = "overall_score",
    "limit": int = 20
}
```

**Output Schema**:
```python
{
    "total_matches": int,
    "companies": List[{
        "company_name": str,
        "overall_score": float,
        "latest_analysis": str,
        "scores": dict,
        "s3_path": str
    }]
}
```

### 9. `export_report`
**Description**: Generate formatted reports

**Input Schema**:
```python
{
    "company_names": List[str],
    "format": str,  # "json", "csv", "pdf", "excel", "xlsx"
    "include_history": bool = False,
    "output_path": str  # S3 path for report
}
```

**Output Schema**:
```python
{
    "success": bool,
    "report_path": str,  # S3 path
    "report_size_bytes": int,
    "companies_included": int
}
```

### 10. `generate_xlsx_export`
**Description**: Generate downloadable XLSX file from company list

**Input Schema**:
```python
{
    "company_names": List[str],
    "include_sections": List[str] = ["summary", "scores", "analysis", "metadata"],  # Configurable sections
    "sort_by": str = "overall_score",  # "overall_score", "company_name", "analysis_date"
    "sort_order": str = "desc",  # "asc" or "desc"
    "include_charts": bool = True,  # Include score visualization charts
    "custom_fields": Dict[str, str] = {},  # Custom columns with formulas
    "template": str = "default"  # "default", "summary", "detailed"
}
```

**Output Schema**:
```python
{
    "success": bool,
    "download_url": str,  # Pre-signed S3 URL for download
    "file_path": str,  # S3 path
    "file_size_bytes": int,
    "companies_included": int,
    "sheets_created": List[str],  # List of sheet names
    "expires_at": str,  # ISO timestamp when download URL expires
    "error": str  # Only if success=False
}
```

### 11. `update_metadata`
**Description**: Manually update company metadata

**Input Schema**:
```python
{
    "company_name": str,
    "updates": {
        "aliases": List[str],
        "tags": List[str],
        "notes": str,
        "exclude_from_reports": bool
    }
}
```

### 12. `qualify_lead`
**Description**: Complete multi-tier qualification including Q1-Q5 scoring

**Input Schema**:
```python
{
    "company_name": str,
    "website_url": str,
    "linkedin_url": str = None,
    "salesforce_data": dict = None,  # Existing CRM data
    "manual_overrides": dict = None,  # BD/Executive input
    "skip_stages": List[str] = []  # Skip specific qualification stages
}
```

**Output Schema**:
```python
{
    "success": bool,
    "qualification_result": QualificationResult,
    "lead_tier": str,  # "VIP", "HIGH", "MEDIUM", "LOW", "DISQUALIFIED"
    "nurturing_strategy": dict,
    "sales_plan_template": dict,
    "processing_time_seconds": float,
    "error": str  # Only if success=False
}
```

### 13. `bulk_filter`
**Description**: Filter multiple companies against criteria

**Input Schema**:
```python
{
    "companies": List[{
        "company_name": str,
        "website_url": str,
        "linkedin_url": str
    }],
    "stop_on_qualified_count": int = None,  # Stop after N qualified companies
    "max_parallel": int = 10
}
```

**Output Schema**:
```python
{
    "total_companies": int,
    "qualified_count": int,
    "disqualified_count": int,
    "requires_review_count": int,
    "results": List[{
        "company_name": str,
        "is_qualified": bool,
        "disqualification_reasons": List[str],
        "confidence_score": float
    }],
    "processing_time_seconds": float
}
```

### 13. `generate_investment_thesis`
**Description**: AI-powered investment thesis generation

**Input Schema**:
```python
{
    "company_name": str,
    "qualification_result": QualificationResult,
    "salesforce_data": dict,
    "market_research": dict = None,
    "portfolio_context": dict = None,  # Existing VMS portfolio
    "thesis_type": str = "comprehensive"  # "summary", "comprehensive", "executive"
}
```

**Output Schema**:
```python
{
    "success": bool,
    "investment_thesis": {
        "strategic_rationale": str,
        "financial_profile": dict,
        "execution_factors": dict,
        "risk_assessment": dict,
        "synergy_analysis": dict,
        "valuation_framework": dict
    },
    "executive_summary": str,
    "recommendation": str,  # "Pursue", "Monitor", "Pass"
    "confidence_score": float,
    "error": str  # Only if success=False
}
```

### 14. `manage_lead_nurturing`
**Description**: Update lead tier and nurturing activities

**Input Schema**:
```python
{
    "company_name": str,
    "current_tier": str,
    "engagement_history": List[dict],
    "performance_metrics": dict,
    "market_changes": dict = None,
    "executive_feedback": str = None
}
```

**Output Schema**:
```python
{
    "success": bool,
    "updated_tier": str,
    "tier_change_reason": str,
    "recommended_activities": List[dict],
    "bd_action_items": List[str],
    "executive_action_items": List[str],
    "next_review_date": str,
    "error": str  # Only if success=False
}
```

### 15. `enrich_company_data`
**Description**: Enhance company data using additional web sources

**Input Schema**:
```python
{
    "company_name": str,
    "website_url": str,
    "source_tiers": List[str] = ["tier1"],  # "tier1", "tier2", "tier3"
    "paid_sources": List[str] = [],  # Specific paid sources to use
    "data_types": List[str] = ["financial", "technology", "market", "legal"],
    "max_cost_per_lookup": float = 0.0,  # Maximum cost per API call
    "priority_score_threshold": float = 7.0  # Only use paid sources for high-priority companies
}
```

**Output Schema**:
```python
{
    "success": bool,
    "enriched_data": Dict[str, Any],
    "sources_used": List[str],
    "data_quality_score": float,
    "cost_incurred": float,
    "cache_duration": int,  # seconds
    "confidence_improvements": Dict[str, float],
    "error": str  # Only if success=False
}
```

## XLSX Export Specifications

### Sheet Structure

#### 1. Summary Sheet
- Company overview with key metrics
- Overall scores and recommendations
- Summary statistics and charts

#### 2. Detailed Scores Sheet
- All 8 dimension scores with explanations
- Confidence levels and evidence
- Score change history (if available)

#### 3. Company Data Sheet
- Raw company information
- Website content snippets
- LinkedIn data
- Metadata and processing info

#### 4. Analysis Notes Sheet
- Key strengths and concerns
- Recommendations and action items
- Analyst notes and flags

### XLSX Features

```python
XLSX_FEATURES = {
    "formatting": {
        "conditional_formatting": True,  # Color-code scores
        "data_validation": True,  # Dropdowns for filters
        "frozen_panes": True,  # Freeze headers
        "auto_filters": True,  # Enable filtering
        "column_width_auto": True
    },
    "charts": {
        "score_radar_chart": True,  # 8-dimension radar
        "score_bar_chart": True,  # Comparative bar chart
        "trend_chart": True,  # Historical trends if available
        "distribution_chart": True  # Score distribution
    },
    "formulas": {
        "weighted_averages": True,  # Calculated fields
        "ranking_formulas": True,  # Auto-ranking
        "summary_statistics": True  # Min, max, average
    },
    "styling": {
        "company_branding": True,  # Custom headers
        "professional_theme": True,  # Corporate styling
        "print_optimization": True  # Print-friendly layout
    }
}
```

### Template Options

#### Default Template
- All sheets included
- Full data with charts
- Suitable for detailed analysis

#### Summary Template
- Summary and scores sheets only
- Focus on key metrics
- Ideal for executive briefings

#### Detailed Template
- All sheets plus additional analysis
- Custom formulas and calculations
- Advanced formatting and charts
- Best for comprehensive reviews

## Data Models

### Analysis Result Model
```python
class AnalysisResult(BaseModel):
    company_name: str
    analysis_timestamp: str  # ISO 8601
    website_url: str
    linkedin_url: Optional[str]
    
    qualification_result: QualificationResult  # Multi-tier qualification
    scores: Dict[str, ScoreDimension]
    overall_score: float  # Weighted average
    recommendation: str  # "Strong Buy", "Buy", "Hold", "Pass", "DISQUALIFIED"
    
    key_strengths: List[str]
    key_concerns: List[str]
    
    lead_tier: str  # "VIP", "HIGH", "MEDIUM", "LOW"
    investment_thesis: Optional[dict] = None
    nurturing_plan: Optional[dict] = None
    
    metadata: AnalysisMetadata
    export_metadata: Optional[ExportMetadata] = None  # For XLSX export tracking
    
class ScoreDimension(BaseModel):
    score: float
    explanation: str
    confidence: float  # 0.0 to 1.0
    evidence: List[str]
    is_estimated: bool = False
    
class AnalysisMetadata(BaseModel):
    llm_model: str  # e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_region: str
    model_response_time_ms: float
    tokens_used: int
    model_cost_usd: float
    mcp_version: str
    processing_time_seconds: float
    data_sources: List[str]
    warnings: List[str]
    fallback_model_used: bool = False
    
class ExportMetadata(BaseModel):
    export_timestamp: str  # ISO 8601
    export_format: str  # "xlsx", "csv", "json", etc.
    template_used: str  # "default", "summary", "detailed"
    sheets_included: List[str]
    file_size_bytes: int
    download_expires_at: str  # ISO 8601
    custom_fields: Dict[str, str] = {}
    
class XLSXExportRequest(BaseModel):
    company_names: List[str]
    include_sections: List[str] = ["summary", "scores", "analysis", "metadata"]
    sort_by: str = "overall_score"
    sort_order: str = "desc"  # "asc" or "desc"
    include_charts: bool = True
    custom_fields: Dict[str, str] = {}  # Custom columns with formulas
    template: str = "default"  # "default", "summary", "detailed"
    
class XLSXExportResult(BaseModel):
    success: bool
    download_url: str  # Pre-signed S3 URL
    file_path: str  # S3 path
    file_size_bytes: int
    companies_included: int
    sheets_created: List[str]
    expires_at: str  # ISO timestamp
    error: Optional[str] = None
```

### Website Content Model
```python
class WebsiteContent(BaseModel):
    main_page: PageContent
    subpages: List[PageContent]
    aggregated_content: str
    total_characters: int
    scrape_metadata: ScrapeMetadata
    
class PageContent(BaseModel):
    url: str
    title: str
    content: str
    links_found: List[str]
    scraped_at: str
    
class ScrapeMetadata(BaseModel):
    total_pages_attempted: int
    total_pages_successful: int
    total_time_seconds: float
    errors: List[str]
```

### LinkedIn Data Model
```python
class LinkedInData(BaseModel):
    company_name: str
    founded_year: Optional[int]
    employee_count: Optional[int]
    employee_range: str
    industry: str
    headquarters: Optional[str]
    description: str
    
    growth_data: GrowthMetrics
    funding_data: FundingInfo
    
    scraped_at: str
    data_quality_score: float  # 0.0 to 1.0
    
class GrowthMetrics(BaseModel):
    current_employees: int
    previous_year_employees: Optional[int]
    yoy_growth_percent: Optional[float]
    growth_trend: str  # "rapid", "steady", "slow", "declining"
    
class FundingInfo(BaseModel):
    total_funding: float
    funding_rounds: List[FundingRound]
    is_bootstrapped: bool
    last_funding_date: Optional[str]
    
class FundingRound(BaseModel):
    round_type: str
    amount: float
    date: str
    investors: List[str]
```

### XLSX Sheet Models

```python
class XLSXSheet(BaseModel):
    name: str
    data: List[Dict[str, Any]]
    headers: List[str]
    formatting: Dict[str, Any]
    charts: List[Dict[str, Any]] = []
    
class SummarySheet(XLSXSheet):
    name: str = "Summary"
    columns: List[str] = [
        "Company Name", "Overall Score", "Recommendation", 
        "VMS Score", "Revenue Model", "Suite vs Point",
        "Customer Quality", "Pricing", "OPM", "Size/Growth", 
        "Ownership", "Analysis Date", "Key Strengths", "Key Concerns"
    ]
    
class DetailedScoresSheet(XLSXSheet):
    name: str = "Detailed Scores"
    columns: List[str] = [
        "Company Name", "Dimension", "Score", "Explanation",
        "Confidence", "Evidence", "Is Estimated", "Previous Score",
        "Score Change", "Change Reason"
    ]
    
class CompanyDataSheet(XLSXSheet):
    name: str = "Company Data"
    columns: List[str] = [
        "Company Name", "Website URL", "LinkedIn URL", "Industry",
        "Founded Year", "Employee Count", "Headquarters", "Funding",
        "Content Summary", "Processing Time", "Data Sources"
    ]
    
class AnalysisNotesSheet(XLSXSheet):
    name: str = "Analysis Notes"
    columns: List[str] = [
        "Company Name", "Analyst Notes", "Flags", "Follow-up Actions",
        "Confidence Level", "Data Quality", "Warnings", "Review Date"
    ]
```

### Filtering Implementation

```python
class CompanyFilterService:
    def __init__(self, bedrock_client):
        self.bedrock_client = bedrock_client
        self.rules = DISQUALIFICATION_RULES
        
    async def filter_company(self, company_data: dict) -> FilteringResult:
        """Apply all filtering criteria to a company"""
        result = FilteringResult(
            company_name=company_data["company_name"],
            is_qualified=True,
            confidence_score=1.0
        )
        
        # Geographic filtering
        geo_status = await self._check_geography(company_data)
        result.geographic_status = geo_status["status"]
        if geo_status["status"] == "disqualified":
            result.is_qualified = False
            result.disqualification_reasons.append("Geographic restrictions")
            
        # Business model filtering
        biz_status = await self._check_business_model(company_data)
        result.business_model_status = biz_status["status"]
        if biz_status["status"] == "disqualified":
            result.is_qualified = False
            result.disqualification_reasons.extend(biz_status["reasons"])
            
        # Solution type filtering
        solution_status = await self._check_solution_type(company_data)
        result.solution_type_status = solution_status["status"]
        if solution_status["status"] == "disqualified":
            result.is_qualified = False
            result.disqualification_reasons.extend(solution_status["reasons"])
            
        # Set confidence based on data quality
        result.confidence_score = self._calculate_confidence(company_data)
        result.requires_manual_review = result.confidence_score < 0.7
        
        return result
        
    async def _check_geography(self, company_data: dict) -> dict:
        """Check geographic eligibility"""
        location_prompt = f"""
        Determine the primary geographic location of this company:
        Company: {company_data.get('company_name')}
        Website: {company_data.get('website_content', '')}
        LinkedIn: {company_data.get('linkedin_data', {})}
        
        Return JSON: {{
            "primary_location": "country/region",
            "confidence": 0.0-1.0,
            "evidence": ["location indicators"]
        }}
        """
        # Use Bedrock to analyze location
        # Apply geographic rules
        # Return status
        
    async def _check_business_model(self, company_data: dict) -> dict:
        """Check business model eligibility"""
        model_prompt = f"""
        Analyze this company's business model:
        Company: {company_data.get('company_name')}
        Description: {company_data.get('company_description', '')}
        Services: {company_data.get('services', '')}
        
        Determine:
        1. Is this primarily a software company or services company?
        2. Is this B2B, B2C, or marketplace?
        3. Any disqualifying factors?
        
        Return JSON: {{
            "business_type": "software|services|mixed",
            "market_type": "b2b|b2c|marketplace|mixed",
            "disqualifying_factors": ["list of issues"],
            "confidence": 0.0-1.0
        }}
        """
        # Use Bedrock to analyze business model
        # Apply business model rules
        # Return status
```

## S3 Storage Structure

### Bucket Organization
```
s3://ma-research-bucket/
├── companies/
│   ├── {sanitized-company-name}/
│   │   ├── {ISO-8601-timestamp}/
│   │   │   ├── analysis.json          # Complete analysis results
│   │   │   ├── raw_website_content.json  # Scraped content
│   │   │   ├── linkedin_data.json    # LinkedIn information
│   │   │   └── metadata.json         # Processing metadata
│   │   ├── latest/                   # Copy of most recent analysis
│   │   └── company_metadata.json     # Persistent company info
│   └── _index/
│       ├── companies_list.json       # All companies with latest scores
│       └── analysis_calendar.json    # Timeline of all analyses
├── reports/
│   ├── {report-id}/
│   │   └── report.{format}
│   └── _templates/
│       └── report_templates/
├── exports/
│   └── {export-date}/
│       ├── full_export.json
│       └── xlsx_exports/
│           └── {export-id}.xlsx
└── config/
    ├── scoring_weights.json
    └── system_config.json
```

### File Naming Conventions
- Company names: Lowercase, spaces to hyphens, remove special chars
- Timestamps: ISO 8601 with colons replaced by hyphens (2024-01-10T14-30-00Z)
- Report IDs: UUID v4

### S3 Configuration Requirements
```python
{
    "bucket_name": "ma-research-bucket",
    "region": "us-east-1",
    "storage_class": "STANDARD_IA",  # For older analyses
    "encryption": "AES256",
    "versioning": True,
    "lifecycle_rules": [
        {
            "id": "archive-old-analyses",
            "status": "Enabled",
            "transitions": [
                {
                    "days": 90,
                    "storage_class": "GLACIER"
                }
            ]
        }
    ],
    "cors_rules": [
        {
            "allowed_origins": ["*"],
            "allowed_methods": ["GET"],
            "allowed_headers": ["*"]
        }
    ]
}
```

## Implementation Requirements

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
BEDROCK_MAX_TOKENS=4096
BEDROCK_TEMPERATURE=0.1

# Optional Paid Source APIs
CRUNCHBASE_PRO_API_KEY=xxx
CLEARBIT_API_KEY=xxx
ZOOMINFO_API_KEY=xxx
SIMILARWEB_API_KEY=xxx
BUILTWITH_API_KEY=xxx
PITCHBOOK_API_KEY=xxx

# MCP Configuration
MCP_SERVER_NAME=ma-research-assistant
MCP_SERVER_VERSION=1.0.0
MCP_LOG_LEVEL=INFO

# Feature Flags
ENABLE_CACHING=true
CACHE_TTL_SECONDS=3600
MAX_PARALLEL_ANALYSES=5
WEB_SCRAPE_TIMEOUT=30

# XLSX Export Configuration
XLSX_MAX_COMPANIES=100
XLSX_DOWNLOAD_EXPIRY_HOURS=24
XLSX_ENABLE_CHARTS=true
XLSX_MAX_FILE_SIZE_MB=50

# Lead Qualification Configuration
QUALIFICATION_MINIMUM_SCORE=7.0
TIER_VIP_THRESHOLD=9.0
TIER_HIGH_THRESHOLD=8.0
TIER_MEDIUM_THRESHOLD=7.0

# Nurturing Configuration
VIP_CONTACT_FREQUENCY_DAYS=7
HIGH_CONTACT_FREQUENCY_DAYS=14
MEDIUM_CONTACT_FREQUENCY_DAYS=30
MAX_VIP_TARGETS=15

# Investment Thesis
THESIS_AI_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
THESIS_CONFIDENCE_THRESHOLD=0.8
```

### Caching Strategy
- Cache website content for 24 hours
- Cache LinkedIn data for 7 days
- Cache analysis results indefinitely (immutable)
- Cache paid API responses for 30 days (or per API terms)
- Use Redis or local file cache
- Implement cache warming for frequently accessed companies
- Cache source reliability scores and API response times
- Implement intelligent cache invalidation based on data staleness

### Rate Limiting
```python
RATE_LIMITS = {
    "bedrock_api": {
        "requests_per_minute": 100,
        "tokens_per_minute": 200000,
        "max_concurrent_requests": 10
    },
    "qualification_api": {
        "max_parallel_qualifications": 5,
        "thesis_generation_timeout": 180,
        "salesforce_sync_interval": 3600
    },
    "apify_api": {
        "requests_per_hour": 100
    },
    "web_scraping": {
        "requests_per_second_per_domain": 1,
        "concurrent_domains": 5
    },
    "paid_apis": {
        "crunchbase_pro": {"requests_per_day": 5000},
        "clearbit": {"requests_per_month": 50000},
        "zoominfo": {"requests_per_day": 1000},
        "similarweb": {"requests_per_month": 10000},
        "builtwith": {"requests_per_month": 1000},
        "pitchbook": {"requests_per_day": 500}
    }
}
```

### Logging Configuration
```python
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "ma_research.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "default"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}
```

## Error Handling

### Error Categories and Responses

#### 1. Web Scraping Errors
```python
class WebScrapingError:
    - ConnectionTimeout: Retry with exponential backoff
    - 404 NotFound: Mark as invalid URL, continue analysis
    - 403 Forbidden: Try alternative user agents, mark if persistent
    - RateLimited: Implement backoff, queue for later
    - InvalidHTML: Log warning, extract what's possible
```

#### 5. Paid API Errors
```python
class PaidAPIError:
    - QuotaExceeded: Stop using API, fallback to free sources
    - InvalidCredentials: Alert user, disable API
    - CostLimitReached: Stop API calls, notify user
    - ServiceUnavailable: Retry with exponential backoff
    - DataNotFound: Continue with partial analysis
```

#### 2. LinkedIn API Errors
```python
class LinkedInAPIError:
    - APIKeyInvalid: Alert user, halt LinkedIn scoring
    - CompanyNotFound: Continue with partial analysis
    - RateLimited: Queue for retry after cooldown
    - DataIncomplete: Use partial data, mark confidence lower
```

#### 3. LLM API Errors
```python
class BedrockAPIError:
    - TokenLimitExceeded: Chunk content and retry
    - InvalidResponse: Retry with adjusted prompt
    - ModelNotAvailable: Fallback to alternative model
    - ThrottlingException: Implement exponential backoff
    - AccessDeniedException: Check IAM permissions
    - ValidationException: Validate request parameters
    - ServiceQuotaExceededException: Wait and retry
```

#### 4. S3 Storage Errors
```python
class S3StorageError:
    - AccessDenied: Check credentials, alert user
    - BucketNotFound: Create bucket or alert configuration error
    - UploadFailed: Retry with exponential backoff
    - ConcurrentModification: Implement optimistic locking
```

### Error Recovery Strategies
1. **Partial Results**: Always save whatever data was successfully collected
2. **Retry Queue**: Failed operations go to retry queue with exponential backoff
3. **Fallback Sources**: Use archive.org for unavailable pages
4. **Manual Review Flag**: Mark analyses requiring human review
5. **Error Reporting**: Comprehensive error reports in metadata

## Performance Requirements

### Response Time SLAs
- Single company analysis: < 60 seconds
- Bulk analysis (10 companies): < 5 minutes
- Search operations: < 2 seconds
- Report generation: < 10 seconds

### Concurrency Limits
- Maximum parallel company analyses: 5
- Maximum concurrent web scraping threads: 10
- Maximum concurrent S3 operations: 20
- LLM API concurrent requests: 3

### Resource Limits
```python
RESOURCE_LIMITS = {
    "max_memory_per_analysis": "512MB",
    "max_website_content_size": "10MB",
    "max_pages_per_company": 10,
    "max_analysis_time": 300,  # seconds
    "max_retry_attempts": 3
}
```

### Optimization Strategies
1. **Parallel Processing**: Use asyncio for I/O operations
2. **Content Deduplication**: Hash content to avoid reprocessing
3. **Smart Caching**: Cache at multiple levels (content, scores, analyses)
4. **Batch Operations**: Group S3 operations for efficiency
5. **Connection Pooling**: Reuse HTTP connections
6. **XLSX Streaming**: Use streaming for large Excel files
7. **Pre-signed URLs**: Generate time-limited download links
8. **Template Caching**: Cache XLSX templates for faster generation

## Security Considerations

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
1. **Encryption at Rest**: All S3 data encrypted with AES-256
2. **Encryption in Transit**: TLS 1.3 for all API calls
3. **API Key Management**: Store in AWS Secrets Manager
4. **PII Handling**: Detect and redact personal information
5. **Access Logging**: CloudTrail for all S3 operations

### Compliance Requirements
- GDPR compliance for European companies
- Data retention policies (7 years default)
- Right to deletion implementation
- Audit trail for all data access
- Regular security scans

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
    },
    "linkedin_url": {
        "pattern": r"^https://([a-z]{2,3}\.)?linkedin\.com/company/[\w\-]+/?$",
        "required": False
    },
    "xlsx_export": {
        "max_companies": 100,
        "allowed_templates": ["default", "summary", "detailed"],
        "allowed_sections": ["summary", "scores", "analysis", "metadata"],
        "allowed_sort_fields": ["overall_score", "company_name", "analysis_date"],
        "max_custom_fields": 10
    },
    "filtering": {
        "allowed_regions": ["North America", "United States", "Canada", "Mexico", "United Kingdom"],
        "uk_allowed_verticals": ["Sports", "Fitness", "Recreation", "Wellness", "Athletics"],
        "required_confidence_threshold": 0.7,
        "manual_review_threshold": 0.5,
        "max_disqualification_keywords": 5
    }
}
```

## Testing Requirements

### Unit Tests
- Test each scoring algorithm independently
- Mock external API calls
- Validate data models
- Test error handling paths

### Integration Tests
- End-to-end analysis workflow
- S3 operations with localstack
- API integration with retries
- Cache behavior validation
- XLSX export generation and download
- Pre-signed URL creation and expiry

### Performance Tests
- Load testing with 100 concurrent analyses
- Memory usage profiling
- Response time benchmarking
- Storage growth projections

### Test Data
```python
TEST_COMPANIES = [
    {
        "name": "Acme Healthcare",
        "website": "https://acme-healthcare.example.com",
        "linkedin": "https://linkedin.com/company/acme-healthcare",
        "expected_vms_score": 4,
        "expected_overall_score": 7.5
    }
    # ... more test cases
]
```

## Deployment Considerations

### Docker Configuration
```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Set AWS Bedrock environment
ENV AWS_DEFAULT_REGION=us-east-1
ENV BEDROCK_REGION=us-east-1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["fastmcp", "serve", "ma_research_mcp"]
```

### Health Checks
```python
HEALTH_CHECK_ENDPOINTS = {
    "/health": "Basic liveness check",
    "/ready": "Check all dependencies",
    "/metrics": "Prometheus metrics",
    "/xlsx/status": "XLSX export service status"
}
```

### XLSX Export Implementation

```python
class XLSXExportService:
    def __init__(self, s3_client, config):
        self.s3_client = s3_client
        self.config = config
        self.workbook_engine = "openpyxl"  # or "xlsxwriter"
        
    async def generate_xlsx_export(self, request: XLSXExportRequest) -> XLSXExportResult:
        """Generate XLSX file from company analysis data"""
        # 1. Validate request
        # 2. Fetch company data
        # 3. Generate sheets based on template
        # 4. Apply formatting and charts
        # 5. Upload to S3
        # 6. Generate pre-signed download URL
        
    def _create_summary_sheet(self, workbook, companies_data):
        """Create summary sheet with key metrics"""
        
    def _create_detailed_scores_sheet(self, workbook, companies_data):
        """Create detailed scores sheet"""
        
    def _create_company_data_sheet(self, workbook, companies_data):
        """Create raw company data sheet"""
        
    def _create_analysis_notes_sheet(self, workbook, companies_data):
        """Create analysis notes sheet"""
        
    def _apply_formatting(self, workbook, template):
        """Apply conditional formatting and styling"""
        
    def _add_charts(self, workbook, companies_data):
        """Add visualization charts"""
        
    async def _upload_to_s3(self, file_path, content):
        """Upload XLSX file to S3"""
        
    async def _generate_download_url(self, s3_path, expiry_hours=24):
        """Generate pre-signed download URL"""
```

### Monitoring & Alerting
1. CloudWatch metrics for S3 operations
2. Bedrock API response time and token usage tracking
3. Error rate monitoring (including Bedrock throttling)
4. Cost tracking and alerts (Bedrock costs per model)
5. Analysis success rate dashboards
6. Model performance metrics (Claude vs Nova success rates)
7. Token usage optimization alerts

### XLSX Export Error Handling

```python
class XLSXExportError(Exception):
    """Base exception for XLSX export errors"""
    pass

class XLSXGenerationError(XLSXExportError):
    """Error during XLSX file generation"""
    pass

class XLSXUploadError(XLSXExportError):
    """Error during S3 upload"""
    pass

class XLSXSizeError(XLSXExportError):
    """Generated file exceeds size limits"""
    pass

XLSX_ERROR_HANDLING = {
    "generation_timeout": 300,  # seconds
    "max_retries": 3,
    "retry_delay": 5,  # seconds
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "cleanup_temp_files": True,
    "error_notification": True
}
```

### XLSX Performance Optimizations

```python
XLSX_PERFORMANCE_CONFIG = {
    "streaming_threshold": 1000,  # rows
    "chunk_size": 100,  # companies per batch
    "memory_limit": "512MB",
    "compression_level": 6,
    "enable_formulas": True,
    "enable_charts": True,
    "parallel_sheet_generation": True,
    "cache_templates": True,
    "optimize_for_speed": True
}
```

### AWS Bedrock Implementation Details

```python
class BedrockLLMService:
    def __init__(self, region="us-east-1"):
        self.bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region
        )
        self.primary_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        self.fallback_model = "amazon.nova-pro-v1:0"
        
    async def score_dimension(self, dimension: str, content: str, 
                            model_preference: str = "auto") -> ScoreDimension:
        """Score a company dimension using Bedrock models"""
        model_id = self._select_model(content, dimension, model_preference)
        
        try:
            response = await self._invoke_bedrock_model(
                model_id=model_id,
                prompt=self._build_prompt(dimension, content),
                max_tokens=4096,
                temperature=0.1
            )
            return self._parse_response(response)
        except Exception as e:
            if "ThrottlingException" in str(e):
                await asyncio.sleep(2 ** self.retry_count)
                return await self.score_dimension(dimension, content, "fallback")
            raise
    
    def _select_model(self, content: str, dimension: str, preference: str) -> str:
        """Select optimal model based on content complexity and cost"""
        if preference == "claude":
            return self.primary_model
        elif preference == "nova":
            return self.fallback_model
        
        # Auto-selection logic
        content_complexity = self._calculate_complexity(content)
        if content_complexity > 0.7 or dimension in ["vms", "suite_vs_point"]:
            return self.primary_model
        return self.fallback_model
    
    async def _invoke_bedrock_model(self, model_id: str, prompt: str, 
                                  **kwargs) -> dict:
        """Invoke Bedrock model with proper error handling"""
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.1),
            "top_p": kwargs.get("top_p", 0.9),
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
        
        response = self.bedrock_client.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        
        return json.loads(response.get("body").read())
```

## Future Enhancements

### Phase 2 Features
1. **Machine Learning**: Predict acquisition success based on historical data
2. **Competitive Analysis**: Compare companies within same vertical
3. **Financial Integration**: Pull revenue data from financial APIs
4. **Patent Analysis**: Score based on intellectual property
5. **Social Sentiment**: Include social media sentiment analysis
6. **Advanced XLSX Features**: 
   - Interactive dashboards within Excel
   - Pivot tables and slicers
   - Custom VBA macros
   - Real-time data connections

### Phase 3 Features
1. **Real-time Monitoring**: Track score changes over time
2. **Custom Scoring Models**: User-defined scoring criteria
3. **API Webhooks**: Notify on significant score changes
4. **Mobile App**: iOS/Android apps for on-the-go analysis
5. **Advanced Visualizations**: D3.js powered analytics dashboard
6. **Enterprise XLSX Features**:
   - Multi-language support
   - Custom branding and themes
   - Automated email delivery
   - Integration with PowerBI/Tableau
   - Version control and collaboration

## Appendices

### A. Scoring Weight Configuration
```json
{
    "dimension_weights": {
        "vms": 0.15,
        "revenue_model": 0.15,
        "suite_vs_point": 0.10,
        "customer_quality": 0.15,
        "pricing": 0.10,
        "opm": 0.10,
        "size_growth": 0.15,
        "ownership": 0.10
    },
    "overall_score_thresholds": {
        "strong_buy": 8.0,
        "buy": 7.0,
        "hold": 5.5,
        "pass": 0.0,
        "disqualified": -1.0
    },
    "filtering_weights": {
        "geography_compliance": 1.0,
        "business_model_fit": 0.8,
        "solution_type_alignment": 0.9,
        "confidence_threshold": 0.7
    }
}
```

### B. AWS Bedrock Model Configuration
```python
BEDROCK_MODEL_CONFIG = {
    "primary_model": {
        "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 0.9,
        "use_cases": ["complex_analysis", "detailed_scoring", "comprehensive_evaluation"]
    },
    "fallback_model": {
        "model_id": "amazon.nova-pro-v1:0",
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 0.9,
        "use_cases": ["simple_scoring", "backup_analysis"]
    },
    "cost_optimization": {
        "use_nova_for_simple_tasks": True,
        "token_threshold_for_claude": 2000,
        "complexity_threshold_for_claude": 0.7
    }
}
```

### C. LLM Prompt Templates
```python
VMS_PROMPT_TEMPLATE = """
You are an M&A Research Assistant assessing whether this company is a vertical market software business.

Score the company from 0-5 based on how tailored their software is to specific industries:
- 5: Pure VMS for sub-verticals (e.g., EHR for long-term care)
- 4: Industry-specific software (e.g., generic healthcare EHR)
- 3: Software for related industries
- 2: Loosely connected industries
- 1: Minimal vertical tailoring
- 0: Industry-agnostic

Company Website Content:
{content}

Provide your response in JSON format:
{
    "score": <0-5>,
    "explanation": "<detailed reasoning>",
    "confidence": <0.0-1.0>,
    "evidence": ["<key phrase 1>", "<key phrase 2>", ...]
}
"""

BEDROCK_SYSTEM_PROMPT = """
You are an expert M&A Research Assistant specializing in evaluating software companies for acquisition potential. You provide structured, analytical assessments based on 8 key dimensions. Always respond with valid JSON and provide specific evidence from the source material.
"""
```

### C. S3 Lifecycle Policy
```json
{
    "Rules": [
        {
            "ID": "ArchiveOldAnalyses",
            "Status": "Enabled",
            "Transitions": [
                {
                    "Days": 30,
                    "StorageClass": "STANDARD_IA"
                },
                {
                    "Days": 90,
                    "StorageClass": "GLACIER"
                }
            ]
        },
        {
            "ID": "DeleteOldReports",
            "Status": "Enabled",
            "Expiration": {
                "Days": 365
            },
            "Filter": {
                "Prefix": "reports/"
            }
        }
    ]
}
```

### D. Error Code Reference
| Code | Description | User Action |
|------|-------------|-------------|
| E001 | Invalid company name | Check formatting |
| E002 | Website unreachable | Verify URL |
| E003 | LinkedIn API failed | Check API key |
| E004 | LLM quota exceeded | Wait or upgrade |
| E005 | S3 permission denied | Check IAM role |
| E006 | Analysis timeout | Retry later |
| E007 | Invalid score value | Contact support |
| E008 | Duplicate analysis | Use force_refresh |
| E009 | Company disqualified | Review criteria |
| E010 | Geographic restriction | Check location |
| E011 | Business model mismatch | Verify company type |
| E012 | Marketplace detected | Review solution type |

---

This PRD provides comprehensive specifications for building the M&A Research Assistant MCP Server. The implementation should follow these guidelines while maintaining flexibility for future enhancements and modifications based on user feedback and evolving requirements.