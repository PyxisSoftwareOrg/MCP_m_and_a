# Automated Company Discovery Feature - Product Requirements

## Feature Overview

The Automated Company Discovery feature enhances the M&A Research Assistant by automatically finding company websites, LinkedIn profiles, and additional data sources when not provided by the user. This eliminates the need for manual URL entry and ensures comprehensive data collection from multiple sources including Crunchbase and Google search results.

## Business Objectives

1. **Reduce Manual Research Time**: Eliminate the need for users to manually find company URLs
2. **Increase Data Completeness**: Automatically gather data from multiple sources
3. **Improve Analysis Accuracy**: Cross-reference multiple data sources for validation
4. **Enhance User Experience**: Single company name input triggers comprehensive research
5. **Maximize Deal Coverage**: Don't miss potential targets due to incomplete information

## Target Users

### Primary Users
- **BD Teams**: Can analyze companies with just a name, no URL hunting required
- **Analysts**: Get comprehensive data without manual source searching
- **Executive Team**: Quick company lookups for strategic discussions

### Use Cases
- Analyzing companies from a simple list of names
- Researching competitors mentioned in conversations
- Quick lookups during meetings
- Bulk imports from spreadsheets with just company names

## Core Features

### 1. Intelligent Website Discovery

#### Google Search Integration
- Query patterns:
  - `"{company name}" official website`
  - `"{company name}" company software`
  - `"{company name}" site:com OR site:io OR site:net`
- Result validation:
  - Check for company name match in title/content
  - Verify it's the actual company site (not news/reviews)
  - Prioritize .com domains
  - Check for software/product indicators

#### Domain Verification
- SSL certificate validation
- Company name matching in metadata
- About page verification
- Contact information validation
- Cross-reference with LinkedIn/Crunchbase data

### 2. LinkedIn Profile Discovery

#### LinkedIn Search Strategy
- Search patterns:
  - Direct company search via LinkedIn API
  - Google search: `site:linkedin.com/company "{company name}"`
  - Industry-specific searches for disambiguation
- Validation:
  - Employee count threshold (>10)
  - Industry match with website
  - Active posting history
  - Verified company badge (if available)

#### Profile Selection
- Handle multiple matches:
  - Prefer verified companies
  - Match location with other sources
  - Check employee count consistency
  - Industry alignment

### 3. Crunchbase Integration

#### Data Collection
- Company overview and description
- Funding history and investors
- Employee count and growth
- Industry classification
- Headquarters location
- Key personnel
- Acquisition history
- Technology stack

#### API Integration
- Crunchbase API for verified data
- Fallback to web scraping if needed
- Rate limit management
- Cost optimization (API calls are expensive)

### 4. Google Knowledge Graph

#### Business Information
- Official company data from Google
- Business hours and locations
- Stock ticker (if public)
- Parent/subsidiary relationships
- Industry classification
- Company size indicators

#### Review and Reputation
- Google Business reviews
- News mentions and sentiment
- Recent press releases
- Major partnerships or clients

### 5. Multi-Source Validation

#### Cross-Reference Engine
- Compare data across sources:
  - Company name variations
  - Employee count ranges
  - Industry classifications
  - Founding year
  - Location/headquarters
- Confidence scoring for each data point
- Conflict resolution rules

#### Data Quality Scoring
- Source reliability weights:
  - Official website: 100%
  - LinkedIn verified: 90%
  - Crunchbase: 85%
  - Google Knowledge Graph: 80%
  - Google search results: 60%

### 6. Discovery Workflow

#### Step 1: Initial Search
1. Normalize company name (remove Inc., LLC, etc.)
2. Parallel search across all sources
3. Collect potential matches
4. Apply initial filters

#### Step 2: Validation
1. Cross-reference potential matches
2. Score confidence for each source
3. Resolve conflicts
4. Select best matches

#### Step 3: Deep Discovery
1. Fetch detailed data from confirmed sources
2. Extract structured information
3. Normalize data formats
4. Cache results

#### Step 4: Fallback Handling
1. If website not found: Use LinkedIn/Crunchbase data
2. If LinkedIn not found: Proceed with available data
3. If no sources found: Return clear failure reason
4. Always save partial results

## User Workflows

### Workflow 1: Single Company Analysis
1. User enters: "Analyze company: Acme Software"
2. System searches for Acme Software website
3. Finds acmesoftware.com and LinkedIn profile
4. Discovers Crunchbase profile with funding data
5. Runs full analysis with all discovered sources

### Workflow 2: Bulk Import Without URLs
1. User uploads CSV with 100 company names
2. System queues discovery for all companies
3. Parallel discovery process (respecting rate limits)
4. Shows progress: "Found 95/100 websites, 88/100 LinkedIn profiles"
5. Proceeds with analysis using available data

### Workflow 3: Competitive Intelligence
1. User mentions competitor during analysis
2. System suggests: "Also analyze competitor TechCorp?"
3. Auto-discovers TechCorp's web presence
4. Provides comparative analysis

## Success Metrics

### Discovery Metrics
- Website discovery success rate: >85%
- LinkedIn discovery success rate: >80%
- Crunchbase match rate: >70%
- False positive rate: <5%
- Average discovery time: <10 seconds

### Quality Metrics
- Data accuracy (validated against known companies): >95%
- Cross-source validation success: >90%
- User manual correction rate: <10%

### Business Impact
- Reduction in analysis prep time: 75%
- Increase in companies analyzed: 40%
- More complete data per company: +60%

## Constraints and Limitations

### Technical Constraints
- API rate limits:
  - Google Custom Search: 100 queries/day (free tier)
  - Crunchbase: Based on subscription tier
  - LinkedIn: Via Apify, subject to their limits
- Discovery timeout: 30 seconds max per company
- Parallel discovery: Maximum 10 companies

### Data Constraints
- Cannot discover private/stealth companies
- Limited to publicly available information
- May miss non-English companies
- Subsidiary identification challenges

### Legal Constraints
- Respect robots.txt for all sites
- Comply with terms of service
- No circumvention of paywalls
- GDPR compliance for EU companies

## Future Enhancements

### Phase 2 Features
- Industry-specific discovery sources
- Patent database integration
- GitHub organization discovery
- Product Hunt profile matching
- Social media presence analysis

### Phase 3 Features
- AI-powered disambiguation
- Subsidiary tree discovery
- Executive LinkedIn profile matching
- Technology stack detection
- Customer discovery from case studies

### Advanced Features
- Real-time monitoring for new sources
- Automatic data refresh scheduling
- Discovery confidence explanations
- Manual override interface

## Dependencies

- Google Custom Search API or SerpAPI
- Enhanced web scraping capabilities
- Crunchbase API subscription
- Robust caching system
- Rate limit management system

## Risk Mitigation

### API Cost Management
- Implement strict budgets
- Cache aggressively
- Batch similar searches
- Use free tiers where possible

### False Positive Prevention
- Multiple validation steps
- Human-in-the-loop for low confidence
- Clear confidence indicators
- Easy correction mechanisms

### Performance Impact
- Asynchronous discovery
- Smart caching strategies
- Timeout handling
- Graceful degradation