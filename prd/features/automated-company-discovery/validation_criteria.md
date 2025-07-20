# Automated Company Discovery - Validation Criteria

## Automated Test Specifications

### 1. Website Discovery Tests

#### Test 1.1: Direct Domain Discovery
```python
def test_direct_domain_discovery():
    """Test discovery of companies with predictable domains"""
    # Given: Companies with standard domain patterns
    test_companies = [
        ("Microsoft", "https://www.microsoft.com"),
        ("Salesforce", "https://www.salesforce.com"),
        ("HubSpot", "https://www.hubspot.com")
    ]
    # When: Discovery service runs
    # Then: All websites found with >0.9 confidence
    # And: Discovery time < 5 seconds each
    # And: No false positives
```

#### Test 1.2: Complex Domain Discovery
```python
def test_complex_domain_discovery():
    """Test discovery of non-obvious domains"""
    # Given: Companies with non-standard domains
    test_companies = [
        ("Alphabet Inc", "https://abc.xyz"),  # Parent of Google
        ("Meta Platforms", "https://about.meta.com"),
        ("X Corp", "https://x.com")  # Formerly Twitter
    ]
    # When: Discovery includes search engines
    # Then: Correct websites found
    # And: Confidence scores reflect complexity
    # And: Search evidence documented
```

#### Test 1.3: Domain Validation
```python
def test_domain_validation():
    """Test website verification logic"""
    # Given: Mix of valid and invalid domains
    # When: Validation checks run
    # Then: Parking pages rejected
    # And: Company name mismatch detected
    # And: SSL certificates validated
    # And: Recently expired domains caught
```

### 2. LinkedIn Discovery Tests

#### Test 2.1: Standard LinkedIn Discovery
```python
def test_linkedin_profile_discovery():
    """Test finding LinkedIn company profiles"""
    # Given: Companies with LinkedIn presence
    test_companies = [
        "Microsoft",
        "Amazon Web Services",
        "Google Cloud"
    ]
    # When: LinkedIn discovery runs
    # Then: Correct profiles found
    # And: Company IDs extracted
    # And: Employee counts retrieved
    # And: Industry classification matches
```

#### Test 2.2: LinkedIn Disambiguation
```python
def test_linkedin_disambiguation():
    """Test handling multiple LinkedIn matches"""
    # Given: Companies with common names
    test_cases = [
        ("Delta", "software", "USA"),  # Not the airline
        ("Oracle", "software", None),   # Should find tech company
        ("Apple", "technology", None)   # Not the record label
    ]
    # When: Multiple profiles exist
    # Then: Correct profile selected using hints
    # And: Confidence reflects ambiguity
    # And: All candidates logged
```

#### Test 2.3: No LinkedIn Profile
```python
def test_missing_linkedin():
    """Test handling companies without LinkedIn"""
    # Given: Companies without LinkedIn presence
    # When: Discovery attempts to find profile
    # Then: Returns None gracefully
    # And: No false positive matches
    # And: Alternative sources attempted
```

### 3. Crunchbase Integration Tests

#### Test 3.1: Crunchbase Data Retrieval
```python
def test_crunchbase_discovery():
    """Test Crunchbase API integration"""
    # Given: Well-known tech companies
    test_companies = ["Stripe", "Airbnb", "SpaceX"]
    # When: Crunchbase search executes
    # Then: Correct company profiles found
    # And: Funding data retrieved
    # And: Employee range extracted
    # And: Categories correctly parsed
```

#### Test 3.2: Crunchbase Cost Optimization
```python
def test_crunchbase_field_selection():
    """Test cost-optimized field retrieval"""
    # Given: Different analysis requirements
    # When: API calls made with field selection
    # Then: Only requested fields retrieved
    # And: Cost per call < $0.10
    # And: Critical fields always included
```

### 4. Google Discovery Tests

#### Test 4.1: Google Search Results
```python
def test_google_search_discovery():
    """Test Google Custom Search integration"""
    # Given: Company name search queries
    # When: Search API called
    # Then: Official website in top 3 results
    # And: Result snippets parsed for facts
    # And: Knowledge panel data extracted
```

#### Test 4.2: Knowledge Graph Integration
```python
def test_knowledge_graph_data():
    """Test Google Knowledge Graph API"""
    # Given: Public companies with KG entries
    # When: Knowledge Graph queried
    # Then: Stock ticker retrieved
    # And: Founded date matches
    # And: Headquarters location correct
    # And: Entity type identified
```

### 5. Cross-Validation Tests

#### Test 5.1: Data Consistency Validation
```python
def test_cross_source_validation():
    """Test validation across multiple sources"""
    # Given: Company data from all sources
    validation_scenarios = [
        {
            "company": "Example Corp",
            "website_data": {"employees": "100-500"},
            "linkedin_data": {"employees": 250},
            "crunchbase_data": {"employee_range": "101-250"}
        }
    ]
    # When: Validation engine runs
    # Then: Consistency score calculated
    # And: No false conflicts for valid ranges
    # And: Major discrepancies flagged
```

#### Test 5.2: Conflict Resolution
```python
def test_conflict_resolution():
    """Test handling of conflicting data"""
    # Given: Sources with conflicting information
    conflict_scenarios = [
        {
            "field": "founded_year",
            "website": 2010,
            "crunchbase": 2011,
            "linkedin": None
        }
    ]
    # When: Conflicts detected
    # Then: Resolution strategy applied
    # And: Most reliable source preferred
    # And: Conflicts logged for review
```

### 6. Performance Tests

#### Test 6.1: Discovery Speed
```python
def test_discovery_performance():
    """Test discovery completes within SLA"""
    # Given: Single company discovery request
    # When: All sources queried in parallel
    # Then: Results returned < 10 seconds
    # And: Timeout handling works
    # And: Partial results on timeout
```

#### Test 6.2: Batch Discovery
```python
def test_batch_discovery_performance():
    """Test bulk company discovery"""
    # Given: 100 company names
    # When: Batch discovery initiated
    # Then: Completes < 5 minutes
    # And: Rate limits respected
    # And: Failed discoveries retried
    # And: Progress tracking accurate
```

#### Test 6.3: Cache Effectiveness
```python
def test_discovery_caching():
    """Test cache reduces API calls"""
    # Given: Previously discovered companies
    # When: Repeat discovery requested
    # Then: Cache hit rate > 80%
    # And: No API calls for cached data
    # And: Cache TTL respected
```

### 7. Error Handling Tests

#### Test 7.1: API Failure Handling
```python
def test_api_failure_resilience():
    """Test handling of API failures"""
    # Given: Simulated API failures
    failure_scenarios = [
        "Google API rate limit",
        "Crunchbase 503 error",
        "LinkedIn timeout"
    ]
    # When: APIs fail
    # Then: Fallback sources attempted
    # And: Partial results returned
    # And: Clear error messages
```

#### Test 7.2: Invalid Input Handling
```python
def test_invalid_company_names():
    """Test handling of invalid inputs"""
    # Given: Problematic company names
    test_inputs = [
        "",  # Empty
        "X",  # Too short
        "Company " * 100,  # Too long
        "<script>alert('xss')</script>",  # XSS attempt
        "🏢 Emoji Corp 🚀"  # Special characters
    ]
    # When: Discovery attempted
    # Then: Input sanitized safely
    # And: Reasonable results or errors
```

## Manual Testing Procedures

### 1. New Company Discovery Flow

#### Test Case: First-Time Company Analysis
1. Enter company name: "TechStartup Inc"
2. Do NOT provide website or LinkedIn
3. Click analyze
4. Verify discovery spinner shows
5. Check discovered URLs displayed
6. Confirm user can edit URLs before analysis
7. Verify analysis uses discovered data

### 2. Ambiguous Company Handling

#### Test Case: Multiple Possible Matches
1. Enter "Delta" as company name
2. Add hint: Industry = "Software"
3. Verify NOT Delta Airlines
4. Check confidence score < 0.9
5. Verify explanation of ambiguity
6. Confirm correct Delta selected

### 3. International Company Discovery

#### Test Case: Non-English Company
1. Enter "SAP" (German company)
2. Verify finds sap.com
3. Check LinkedIn found despite location
4. Verify Crunchbase data includes HQ
5. Confirm no degradation in quality

### 4. Discovery Failure Scenarios

#### Test Case: Stealth/Private Company
1. Enter unknown startup name
2. Watch discovery process
3. Verify timeout after 30 seconds
4. Check clear "not found" message
5. Verify can proceed with manual URLs
6. Confirm no system errors

## Acceptance Criteria

### Functional Requirements
- [ ] Website discovery success rate ≥ 85%
- [ ] LinkedIn discovery success rate ≥ 80%
- [ ] Crunchbase match rate ≥ 70% for tech companies
- [ ] False positive rate < 5%
- [ ] Cross-validation catches 90% of conflicts

### Performance Requirements
- [ ] Single company discovery < 10 seconds
- [ ] Batch of 100 companies < 5 minutes
- [ ] API costs < $0.50 per company
- [ ] Cache hit rate > 60%
- [ ] Zero memory leaks in 24-hour test

### Data Quality Requirements
- [ ] Website validation accuracy > 95%
- [ ] LinkedIn profile matching > 90% precision
- [ ] Confidence scores correlate with accuracy
- [ ] All data sources properly attributed
- [ ] Conflicts logged and traceable

### Integration Requirements
- [ ] Backward compatible with existing tools
- [ ] Discovery data enhances analysis
- [ ] No degradation of existing features
- [ ] Smooth fallback to manual entry
- [ ] Clear status communication

### User Experience Requirements
- [ ] Discovery status clearly shown
- [ ] Ability to skip discovery
- [ ] Manual override always available
- [ ] Confidence scores explained
- [ ] Source attribution visible

## Monitoring and Alerts

### Key Metrics to Monitor
```yaml
discovery_metrics:
  - name: discovery_success_rate
    threshold: < 80% triggers alert
  - name: api_cost_per_company
    threshold: > $0.75 triggers alert
  - name: discovery_latency_p95
    threshold: > 15s triggers alert
  - name: validation_conflict_rate
    threshold: > 20% triggers investigation
  - name: cache_hit_rate
    threshold: < 50% triggers optimization
```

### API Usage Tracking
```yaml
api_monitoring:
  google_search:
    daily_limit: 100
    alert_at: 80%
  crunchbase:
    monthly_budget: $500
    alert_at: 70%
  knowledge_graph:
    daily_limit: 10000
    alert_at: 90%
```

### Error Rate Monitoring
- Discovery timeout rate
- API failure rates by source
- Validation conflict types
- User override frequency

## Sign-off Criteria

### Development Team
- [ ] All automated tests passing
- [ ] Performance benchmarks met
- [ ] API integration stable
- [ ] Error handling comprehensive

### Product Team
- [ ] Discovery accuracy validated
- [ ] User workflow approved
- [ ] Cost model acceptable
- [ ] Feature value demonstrated

### Operations Team
- [ ] Monitoring configured
- [ ] Cost alerts active
- [ ] Cache strategy optimal
- [ ] Runbooks created

### Security Team
- [ ] API keys secure
- [ ] No data leakage
- [ ] Input validation complete
- [ ] Rate limiting effective

### Executive Sign-off
- [ ] ROI demonstrated
- [ ] Risk assessment complete
- [ ] Budget approved
- [ ] Launch plan reviewed