# Automated Company Discovery - Technical Design

## Technical Architecture

### Service Architecture

```python
# New discovery service structure
services/
├── discovery/
│   ├── __init__.py
│   ├── discovery_orchestrator.py    # Main coordination
│   ├── website_discovery.py         # Website finding
│   ├── linkedin_discovery.py        # LinkedIn search
│   ├── crunchbase_service.py        # Crunchbase API
│   ├── google_discovery.py          # Google search/KG
│   └── validation_engine.py         # Cross-validation
```

### Data Models

#### DiscoveryRequest Model
```python
class DiscoveryRequest(BaseModel):
    company_name: str
    industry_hint: Optional[str] = None
    location_hint: Optional[str] = None
    company_type_hint: Optional[str] = None  # "software", "saas", etc.
    discovery_timeout: int = 30  # seconds
    required_sources: List[str] = ["website", "linkedin"]
    optional_sources: List[str] = ["crunchbase", "google_kg"]

class DiscoveryResult(BaseModel):
    request_id: str
    company_name: str
    normalized_name: str
    discovery_timestamp: datetime
    
    # Discovered URLs
    website_url: Optional[str] = None
    website_confidence: float = 0.0
    website_evidence: List[str] = []
    
    linkedin_url: Optional[str] = None
    linkedin_confidence: float = 0.0
    linkedin_company_id: Optional[str] = None
    
    # Additional sources
    crunchbase_url: Optional[str] = None
    crunchbase_data: Optional[Dict[str, Any]] = None
    
    google_kg_data: Optional[Dict[str, Any]] = None
    google_search_results: List[Dict[str, Any]] = []
    
    # Validation
    cross_validation_score: float = 0.0
    validation_conflicts: List[Dict[str, Any]] = []
    discovery_metadata: DiscoveryMetadata

class DiscoveryMetadata(BaseModel):
    total_sources_checked: int
    successful_sources: List[str]
    failed_sources: Dict[str, str]  # source: error_reason
    discovery_duration_seconds: float
    api_calls_made: Dict[str, int]  # api_name: count
    estimated_cost_usd: float
    cache_hits: Dict[str, bool]
```

### Service Implementations

#### 1. Discovery Orchestrator
```python
class DiscoveryOrchestrator:
    def __init__(self):
        self.website_discovery = WebsiteDiscoveryService()
        self.linkedin_discovery = LinkedInDiscoveryService()
        self.crunchbase_service = CrunchbaseService()
        self.google_discovery = GoogleDiscoveryService()
        self.validation_engine = ValidationEngine()
        self.cache_service = DiscoveryCacheService()
        
    async def discover_company(
        self, 
        request: DiscoveryRequest
    ) -> DiscoveryResult:
        """Main discovery coordination"""
        # Check cache first
        cached_result = await self.cache_service.get_cached_discovery(
            request.company_name
        )
        if cached_result and not self._is_stale(cached_result):
            return cached_result
            
        # Parallel discovery with timeout
        async with asyncio.timeout(request.discovery_timeout):
            tasks = [
                self._discover_website(request),
                self._discover_linkedin(request),
                self._discover_crunchbase(request),
                self._discover_google(request)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        # Combine and validate results
        discovery_result = self._combine_results(request, results)
        
        # Cross-validate sources
        validation_result = await self.validation_engine.validate(
            discovery_result
        )
        
        discovery_result.cross_validation_score = validation_result.score
        discovery_result.validation_conflicts = validation_result.conflicts
        
        # Cache successful discoveries
        if discovery_result.website_url or discovery_result.linkedin_url:
            await self.cache_service.cache_discovery(discovery_result)
            
        return discovery_result
```

#### 2. Website Discovery Service
```python
class WebsiteDiscoveryService:
    def __init__(self):
        self.search_engines = {
            "google": GoogleSearchAPI(),
            "bing": BingSearchAPI(),  # Fallback
            "duckduckgo": DuckDuckGoAPI()  # Free fallback
        }
        
    async def discover_website(
        self,
        company_name: str,
        hints: Dict[str, Any]
    ) -> WebsiteDiscoveryResult:
        """Discover company website using multiple strategies"""
        
        # Strategy 1: Direct domain guessing
        domain_guesses = self._generate_domain_guesses(company_name)
        valid_domains = await self._check_domains(domain_guesses)
        
        if valid_domains:
            return self._select_best_domain(valid_domains)
            
        # Strategy 2: Search engine queries
        search_queries = [
            f'"{company_name}" official website',
            f'"{company_name}" software company',
            f'"{company_name}" {hints.get("industry_hint", "")} software',
            f'intitle:"{company_name}" "about us" "contact"'
        ]
        
        search_results = []
        for query in search_queries:
            try:
                results = await self._search_web(query)
                search_results.extend(results)
            except Exception as e:
                logger.warning(f"Search failed for {query}: {e}")
                
        # Validate and rank results
        validated_results = await self._validate_search_results(
            search_results, company_name
        )
        
        if validated_results:
            return validated_results[0]
            
        return WebsiteDiscoveryResult(
            url=None,
            confidence=0.0,
            evidence=["No website found"]
        )
        
    def _generate_domain_guesses(self, company_name: str) -> List[str]:
        """Generate potential domain names"""
        # Normalize company name
        normalized = company_name.lower()
        normalized = re.sub(r'[^a-z0-9\s-]', '', normalized)
        normalized = re.sub(r'\s+', '', normalized)
        
        domains = []
        tlds = ['.com', '.io', '.net', '.org', '.co', '.ai']
        
        # Direct name
        for tld in tlds:
            domains.append(f"https://{normalized}{tld}")
            domains.append(f"https://www.{normalized}{tld}")
            
        # With hyphens
        hyphenated = normalized.replace(' ', '-')
        for tld in tlds[:3]:  # Only try top TLDs
            domains.append(f"https://{hyphenated}{tld}")
            
        # Common patterns
        if 'software' not in normalized:
            domains.append(f"https://{normalized}software.com")
            
        return domains[:20]  # Limit to prevent abuse
```

#### 3. LinkedIn Discovery Service
```python
class LinkedInDiscoveryService:
    def __init__(self):
        self.apify_client = ApifyClient(token=config.APIFY_API_TOKEN)
        self.google_search = GoogleSearchAPI()
        
    async def discover_linkedin(
        self,
        company_name: str,
        hints: Dict[str, Any]
    ) -> LinkedInDiscoveryResult:
        """Discover LinkedIn company profile"""
        
        # Strategy 1: Direct LinkedIn search via Apify
        try:
            linkedin_results = await self._search_linkedin_direct(
                company_name, hints
            )
            if linkedin_results:
                return self._validate_linkedin_profile(
                    linkedin_results[0], company_name
                )
        except Exception as e:
            logger.warning(f"Direct LinkedIn search failed: {e}")
            
        # Strategy 2: Google site search
        search_query = f'site:linkedin.com/company "{company_name}"'
        google_results = await self.google_search.search(search_query)
        
        for result in google_results[:5]:
            if self._is_company_profile_url(result.url):
                profile = await self._fetch_linkedin_basics(result.url)
                if self._matches_company(profile, company_name):
                    return LinkedInDiscoveryResult(
                        url=result.url,
                        company_id=self._extract_company_id(result.url),
                        confidence=0.85,
                        employee_count=profile.get('employee_count'),
                        industry=profile.get('industry')
                    )
                    
        return LinkedInDiscoveryResult(url=None, confidence=0.0)
        
    def _is_company_profile_url(self, url: str) -> bool:
        """Check if URL is a LinkedIn company profile"""
        pattern = r'linkedin\.com/company/[a-zA-Z0-9-]+/?$'
        return bool(re.search(pattern, url))
```

#### 4. Crunchbase Integration
```python
class CrunchbaseService:
    def __init__(self):
        self.api_key = config.CRUNCHBASE_API_KEY
        self.base_url = "https://api.crunchbase.com/v4"
        self.rate_limiter = RateLimiter(calls_per_minute=60)
        
    async def search_company(
        self,
        company_name: str,
        location: Optional[str] = None
    ) -> Optional[CrunchbaseCompanyData]:
        """Search for company in Crunchbase"""
        
        await self.rate_limiter.acquire()
        
        # Use autocomplete endpoint for efficiency
        params = {
            "query": company_name,
            "collection_ids": "organizations",
            "limit": 10
        }
        
        if location:
            params["locations"] = location
            
        try:
            response = await self._api_request(
                "/searches/autocompletes", 
                params=params
            )
            
            if response.get("entities"):
                # Find best match
                best_match = self._find_best_match(
                    response["entities"], 
                    company_name
                )
                
                if best_match:
                    # Fetch detailed data
                    return await self._fetch_company_details(
                        best_match["identifier"]["uuid"]
                    )
                    
        except Exception as e:
            logger.error(f"Crunchbase search failed: {e}")
            
        return None
        
    async def _fetch_company_details(
        self, 
        company_uuid: str
    ) -> CrunchbaseCompanyData:
        """Fetch detailed company information"""
        
        # Define fields to retrieve (costs vary by field)
        fields = [
            "name", "description", "website_url", "linkedin",
            "founded_on", "num_employees_enum", "revenue_range",
            "total_funding_usd", "last_funding_on", "investor_names",
            "categories", "location_identifiers", "num_exits"
        ]
        
        response = await self._api_request(
            f"/entities/organizations/{company_uuid}",
            params={"field_ids": ",".join(fields)}
        )
        
        return CrunchbaseCompanyData(
            uuid=company_uuid,
            name=response["properties"]["name"],
            website=response["properties"].get("website_url"),
            description=response["properties"].get("description"),
            founded_year=self._extract_year(
                response["properties"].get("founded_on")
            ),
            employee_range=response["properties"].get("num_employees_enum"),
            revenue_range=response["properties"].get("revenue_range"),
            total_funding_usd=response["properties"].get("total_funding_usd"),
            last_funding_date=response["properties"].get("last_funding_on"),
            investors=response["properties"].get("investor_names", []),
            categories=response["properties"].get("categories", []),
            linkedin_url=response["properties"].get("linkedin"),
            exit_count=response["properties"].get("num_exits", 0)
        )
```

#### 5. Google Discovery Service
```python
class GoogleDiscoveryService:
    def __init__(self):
        # Can use Custom Search API or SerpAPI
        self.search_api = GoogleCustomSearchAPI(
            api_key=config.GOOGLE_API_KEY,
            cx=config.GOOGLE_SEARCH_ENGINE_ID
        )
        self.knowledge_graph_api = GoogleKnowledgeGraphAPI(
            api_key=config.GOOGLE_API_KEY
        )
        
    async def discover_google_data(
        self,
        company_name: str
    ) -> GoogleDiscoveryResult:
        """Get data from Google Knowledge Graph and search"""
        
        result = GoogleDiscoveryResult()
        
        # Try Knowledge Graph first
        kg_data = await self._search_knowledge_graph(company_name)
        if kg_data:
            result.knowledge_graph_data = kg_data
            result.official_website = kg_data.get("url")
            result.description = kg_data.get("description")
            result.entity_type = kg_data.get("@type", [])
            
        # Perform general search
        search_results = await self._search_web(company_name)
        result.search_results = search_results[:10]
        
        # Extract structured data
        for item in search_results:
            if "snippet" in item:
                # Look for employee count, location, etc.
                result.extracted_facts.extend(
                    self._extract_facts(item["snippet"])
                )
                
        return result
```

#### 6. Cross-Validation Engine
```python
class ValidationEngine:
    def __init__(self):
        self.validation_rules = [
            self._validate_company_names,
            self._validate_employee_counts,
            self._validate_locations,
            self._validate_industries,
            self._validate_founding_years,
            self._validate_website_consistency
        ]
        
    async def validate(
        self, 
        discovery_result: DiscoveryResult
    ) -> ValidationResult:
        """Cross-validate data from multiple sources"""
        
        conflicts = []
        confidence_scores = {}
        
        for rule in self.validation_rules:
            rule_result = await rule(discovery_result)
            if rule_result.has_conflict:
                conflicts.append(rule_result.conflict)
            confidence_scores[rule_result.field] = rule_result.confidence
            
        # Calculate overall confidence
        overall_confidence = sum(confidence_scores.values()) / len(
            confidence_scores
        )
        
        return ValidationResult(
            score=overall_confidence,
            conflicts=conflicts,
            field_confidence=confidence_scores
        )
        
    async def _validate_employee_counts(
        self, 
        result: DiscoveryResult
    ) -> RuleResult:
        """Validate employee counts across sources"""
        
        counts = {}
        
        if result.linkedin_data:
            counts["linkedin"] = result.linkedin_data.get("employee_count")
            
        if result.crunchbase_data:
            counts["crunchbase"] = self._parse_employee_range(
                result.crunchbase_data.get("employee_range")
            )
            
        if result.google_kg_data:
            counts["google"] = result.google_kg_data.get("employees")
            
        # Check for major discrepancies
        values = [v for v in counts.values() if v]
        if len(values) >= 2:
            min_val = min(values)
            max_val = max(values)
            
            if max_val > min_val * 2:
                return RuleResult(
                    field="employee_count",
                    has_conflict=True,
                    conflict={
                        "type": "employee_count_mismatch",
                        "sources": counts,
                        "variance": max_val / min_val
                    },
                    confidence=0.6
                )
                
        return RuleResult(
            field="employee_count",
            has_conflict=False,
            confidence=0.9
        )
```

### MCP Tool Updates

#### Updated analyze_company Tool
```python
@mcp.tool
async def analyze_company(
    company_name: str,
    website_url: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    auto_discover: bool = True,
    discovery_hints: Optional[Dict[str, Any]] = None,
    force_refresh: bool = False,
    skip_filtering: bool = False,
    manual_override: bool = False
) -> Dict[str, Any]:
    """Enhanced company analysis with auto-discovery"""
    
    # Step 1: Auto-discovery if enabled and URLs not provided
    if auto_discover and (not website_url or not linkedin_url):
        logger.info(f"Starting auto-discovery for {company_name}")
        
        discovery_request = DiscoveryRequest(
            company_name=company_name,
            industry_hint=discovery_hints.get("industry") if discovery_hints else None,
            location_hint=discovery_hints.get("location") if discovery_hints else None
        )
        
        discovery_result = await discovery_orchestrator.discover_company(
            discovery_request
        )
        
        # Use discovered URLs
        if not website_url and discovery_result.website_url:
            website_url = discovery_result.website_url
            logger.info(f"Discovered website: {website_url}")
            
        if not linkedin_url and discovery_result.linkedin_url:
            linkedin_url = discovery_result.linkedin_url
            logger.info(f"Discovered LinkedIn: {linkedin_url}")
            
        # Store discovery data for analysis enrichment
        discovery_data = {
            "crunchbase": discovery_result.crunchbase_data,
            "google_kg": discovery_result.google_kg_data,
            "discovery_confidence": discovery_result.cross_validation_score
        }
    else:
        discovery_data = None
        
    # Continue with existing analysis flow...
    # But now include discovery_data in combined_data
```

### Performance Optimizations

#### Caching Strategy
```python
DISCOVERY_CACHE_CONFIG = {
    "company_discovery": {
        "ttl_seconds": 86400,  # 24 hours
        "key_pattern": "discovery:company:{normalized_name}"
    },
    "domain_validation": {
        "ttl_seconds": 3600,  # 1 hour
        "key_pattern": "discovery:domain:{domain}"
    },
    "search_results": {
        "ttl_seconds": 1800,  # 30 minutes
        "key_pattern": "discovery:search:{query_hash}"
    }
}
```

#### Rate Limiting
```python
RATE_LIMITS = {
    "google_search": {
        "requests_per_day": 100,  # Free tier
        "requests_per_second": 1
    },
    "crunchbase_api": {
        "requests_per_minute": 60,
        "cost_per_request": 0.05  # Credits
    },
    "web_scraping": {
        "requests_per_second_per_domain": 0.5,
        "concurrent_domains": 10
    }
}
```

### Error Handling

```python
class DiscoveryError(Exception):
    """Base discovery exception"""

class NoSourcesFoundError(DiscoveryError):
    """No data sources discovered"""

class RateLimitExceededError(DiscoveryError):
    """API rate limit exceeded"""

class ValidationFailureError(DiscoveryError):
    """Cross-validation failed"""

class DiscoveryTimeoutError(DiscoveryError):
    """Discovery process timed out"""
```

### Monitoring

```python
DISCOVERY_METRICS = {
    "discovery_success_rate": Gauge,
    "source_hit_rates": {
        "website": Gauge,
        "linkedin": Gauge,
        "crunchbase": Gauge,
        "google": Gauge
    },
    "discovery_latency": Histogram,
    "api_costs": Counter,
    "validation_conflicts": Counter,
    "cache_hit_rate": Gauge
}
```

### Security Considerations

1. **API Key Management**
   - Store in AWS Secrets Manager
   - Rotate keys regularly
   - Monitor usage for anomalies

2. **Data Privacy**
   - No storage of personal information
   - Company data only
   - GDPR compliance for EU companies

3. **Rate Limit Protection**
   - Circuit breakers for each API
   - Exponential backoff
   - Cost monitoring alerts

### Integration Points

1. **With Existing Analysis**
   - Enrich analysis with Crunchbase funding data
   - Add Google Knowledge Graph facts
   - Include discovery confidence in reports

2. **With Caching System**
   - Share cache between discovery and analysis
   - Warm cache during off-peak hours
   - Cache invalidation strategy

3. **With Export System**
   - Include discovery metadata in exports
   - Show data source attribution
   - Export discovery confidence scores