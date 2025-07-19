# M&A Research Assistant - Validation Criteria

## Overview
This document defines the validation criteria and test requirements to ensure the M&A Research Assistant MCP Server is working properly. It includes automated QA tests, manual testing procedures, and acceptance criteria.

## QA Automation Tests

### Test 1: Company Analysis End-to-End
**Purpose**: Validate complete company analysis workflow
**Type**: Integration Test
**Automation**: Required
```python
def test_company_analysis_e2e():
    # Given a valid company with website and LinkedIn
    company = "Salesforce"
    website = "https://salesforce.com"
    linkedin = "https://linkedin.com/company/salesforce"
    
    # When analyzing the company
    result = analyze_company(company, website, linkedin)
    
    # Then analysis should complete successfully
    assert result.success == True
    assert result.s3_path is not None
    assert result.analysis_summary contains all 8 dimensions
    assert result.overall_score between 0 and 50
    assert result.recommendation in ["Acquire", "Monitor", "Pass"]
```

### Test 2: Web Scraping Resilience
**Purpose**: Ensure web scraper handles various website conditions
**Type**: Unit Test
**Automation**: Required
```python
def test_web_scraping_resilience():
    test_cases = [
        {"url": "https://valid-site.com", "expected": "success"},
        {"url": "https://404-site.com", "expected": "partial_success"},
        {"url": "https://timeout-site.com", "expected": "retry_success"},
        {"url": "https://blocked-site.com", "expected": "fallback_success"}
    ]
    
    for case in test_cases:
        result = scrape_website(case["url"])
        assert result.status == case["expected"]
        assert result.content is not None or result.error_handled == True
```

### Test 3: Scoring System Accuracy
**Purpose**: Validate scoring algorithms produce consistent results
**Type**: Unit Test
**Automation**: Required
```python
def test_scoring_system_accuracy():
    # Test data with known expected scores
    test_companies = [
        {"name": "High VMS SaaS", "expected_vms": 4.5, "expected_revenue_model": 4.8},
        {"name": "Low VMS Hardware", "expected_vms": 1.2, "expected_revenue_model": 2.1}
    ]
    
    for company in test_companies:
        scores = score_all_dimensions(company["data"])
        assert abs(scores.vms_score - company["expected_vms"]) < 0.5
        assert abs(scores.revenue_model - company["expected_revenue_model"]) < 0.5
```

### Test 4: S3 Storage Operations
**Purpose**: Ensure all S3 operations work correctly
**Type**: Integration Test
**Automation**: Required
```python
def test_s3_storage_operations():
    test_data = generate_sample_analysis()
    company_name = "TestCompany"
    
    # Test storage
    s3_path = store_analysis(company_name, test_data)
    assert s3_path is not None
    
    # Test retrieval
    retrieved_data = get_analysis(company_name, s3_path)
    assert retrieved_data == test_data
    
    # Test indexing
    index = get_companies_index()
    assert company_name in [c.name for c in index]
    
    # Test cleanup
    cleanup_test_data(s3_path)
```

### Test 5: LinkedIn API Integration
**Purpose**: Validate LinkedIn data collection via Apify
**Type**: Integration Test
**Automation**: Required
```python
def test_linkedin_integration():
    test_urls = [
        "https://linkedin.com/company/microsoft",
        "https://linkedin.com/company/invalid-company"
    ]
    
    for url in test_urls:
        result = get_linkedin_data(url)
        
        if "invalid" in url:
            assert result.success == False
            assert result.error_type == "company_not_found"
        else:
            assert result.success == True
            assert result.employee_count > 0
            assert result.company_size is not None
            assert result.growth_metrics is not None
```

### Test 6: Custom Scoring Systems
**Purpose**: Verify custom scoring systems execute correctly
**Type**: Integration Test
**Automation**: Required
```python
def test_custom_scoring_systems():
    # Create custom scoring system
    custom_system = ScoringSystem(
        system_id="test_custom",
        system_name="Test Custom Scoring",
        owner="test_user",
        dimensions=[...],
        weights={"vms": 0.3, "revenue": 0.4, "growth": 0.3}
    )
    
    # Register system
    register_scoring_system(custom_system)
    
    # Run analysis with custom system
    result = run_custom_scoring("TestCompany", "test_custom")
    
    assert result.success == True
    assert result.system_id == "test_custom"
    assert result.weighted_score is not None
```

### Test 7: Bulk Operations Performance
**Purpose**: Ensure bulk analysis meets performance requirements
**Type**: Performance Test
**Automation**: Required
```python
def test_bulk_operations_performance():
    companies = generate_test_companies(10)
    
    start_time = time.time()
    results = bulk_analyze(companies)
    execution_time = time.time() - start_time
    
    # Should complete 10 companies in under 5 minutes
    assert execution_time < 300
    assert len(results) == 10
    assert all(r.success for r in results if r.qualified)
    
    # Check parallel execution
    assert max_concurrent_analyses <= 5
```

### Test 8: Lead Classification Logic
**Purpose**: Validate tier assignment and override functionality
**Type**: Unit Test
**Automation**: Required
```python
def test_lead_classification():
    test_cases = [
        {"score": 45.0, "expected_tier": "VIP"},
        {"score": 35.0, "expected_tier": "HIGH"},
        {"score": 25.0, "expected_tier": "MEDIUM"},
        {"score": 15.0, "expected_tier": "LOW"}
    ]
    
    for case in test_cases:
        tier = classify_lead_tier(case["score"])
        assert tier == case["expected_tier"]
    
    # Test manual override
    override_result = override_company_tier("TestCompany", "VIP", "Strategic importance")
    assert override_result.success == True
    assert override_result.audit_trail is not None
```

### Test 9: XLSX Export Generation
**Purpose**: Verify Excel export functionality
**Type**: Integration Test
**Automation**: Required
```python
def test_xlsx_export_generation():
    companies = generate_test_companies(5)
    
    # Generate XLSX export
    export_result = generate_xlsx_export(companies, "full")
    
    assert export_result.success == True
    assert export_result.s3_url is not None
    assert export_result.file_size > 0
    
    # Download and validate structure
    workbook = download_and_parse_xlsx(export_result.s3_url)
    assert "Company Analysis" in workbook.sheetnames
    assert "Scoring Summary" in workbook.sheetnames
    assert workbook["Company Analysis"].max_row >= len(companies)
```

### Test 10: Error Recovery and Resilience
**Purpose**: Ensure system handles failures gracefully
**Type**: Integration Test
**Automation**: Required
```python
def test_error_recovery():
    # Test API failures
    with mock_api_failure("linkedin"):
        result = analyze_company("TestCompany", "https://test.com", "https://linkedin.com/test")
        assert result.partial_success == True
        assert "linkedin_data" in result.missing_components
    
    # Test network timeouts
    with mock_network_timeout():
        result = scrape_website("https://slow-site.com")
        assert result.retry_count > 0
        assert result.fallback_used == True
    
    # Test S3 failures
    with mock_s3_failure():
        result = store_analysis("TestCompany", sample_data)
        assert result.local_backup_created == True
```

## Additional QA Tests (Manual/Semi-Automated)

### Test 11: Data Quality Validation
**Type**: Manual Review
**Frequency**: Weekly
**Purpose**: Review scoring accuracy against known companies
- Sample 10 analyzed companies monthly
- Validate scores against manual assessment
- Check for scoring drift or inconsistencies
- Review LLM prompt effectiveness

### Test 12: Security and Compliance
**Type**: Automated Security Scan
**Frequency**: Each deployment
**Purpose**: Ensure security standards are maintained
- Scan for exposed credentials
- Validate encryption at rest and in transit
- Check access controls and permissions
- Verify PII handling compliance

### Test 13: Cost Monitoring
**Type**: Automated Alert
**Frequency**: Daily
**Purpose**: Monitor AWS and API costs
- Track Bedrock API usage and costs
- Monitor S3 storage growth
- Alert on unexpected cost spikes
- Validate cost per analysis targets

### Test 14: Load Testing
**Type**: Performance Test
**Frequency**: Before major releases
**Purpose**: Validate system under load
- Simulate 50 concurrent analyses
- Test system behavior at rate limits
- Validate graceful degradation
- Check memory and CPU usage patterns

### Test 15: User Acceptance Testing
**Type**: Manual UAT
**Frequency**: End of each phase
**Purpose**: Validate business requirements
- Test all MCP tools from Claude interface
- Validate export formats meet requirements
- Check tier classification accuracy
- Verify investment thesis quality

## Acceptance Criteria

### Functional Requirements
- [ ] All 19 MCP tools respond within SLA timeouts
- [ ] Single company analysis completes in <60 seconds
- [ ] Bulk analysis (10 companies) completes in <5 minutes
- [ ] Scoring accuracy within ±10% of manual assessment
- [ ] 95% uptime for all core services

### Data Quality Requirements
- [ ] Website scraping success rate >85%
- [ ] LinkedIn data collection success rate >90%
- [ ] Analysis completeness rate >95%
- [ ] Zero data corruption incidents
- [ ] Complete audit trail for all operations

### Performance Requirements
- [ ] Maximum 5 parallel analyses enforced
- [ ] Memory usage <512MB per analysis
- [ ] S3 operations complete within 10 seconds
- [ ] API rate limits respected with proper backoff
- [ ] Cache hit rate >70% for repeated requests

### Security Requirements
- [ ] All data encrypted at rest (AES-256)
- [ ] All API calls use TLS 1.3
- [ ] No credentials in logs or error messages
- [ ] Access controls properly implemented
- [ ] PII detection and redaction working

### Integration Requirements
- [ ] FastMCP server starts and responds to health checks
- [ ] All AWS services accessible with proper permissions
- [ ] Apify API integration stable
- [ ] XLSX exports downloadable via pre-signed URLs
- [ ] Error notifications sent to appropriate channels

## Test Environment Setup

### Prerequisites
- AWS test account with isolated resources
- Test S3 bucket with lifecycle policies
- Mock API endpoints for failure testing
- Sample company dataset for testing
- Apify test token with limited quota

### Test Data Management
- Automated test data generation scripts
- Known-good analysis results for regression testing
- Mock responses for external APIs
- Test company profiles with expected scores
- Cleanup scripts for test artifacts

## Continuous Integration

### Automated Test Pipeline
1. **Unit Tests**: Run on every commit
2. **Integration Tests**: Run on pull requests
3. **Performance Tests**: Run nightly
4. **Security Scans**: Run on deployment
5. **E2E Tests**: Run before production deployment

### Test Reporting
- Real-time test results in CI/CD dashboard
- Weekly test coverage reports
- Monthly performance trend analysis
- Quarterly security assessment reports
- Annual test strategy review

## Monitoring and Alerting

### Key Metrics
- Analysis success rate
- Average response times
- Error rates by category
- Cost per analysis
- System resource utilization

### Alert Thresholds
- Analysis failure rate >5%
- Response time >SLA targets
- Error rate >2%
- Cost variance >20%
- Resource usage >80%

## Risk Mitigation

### High-Risk Areas
1. **External API Dependencies**: Mock testing, fallback strategies
2. **Large-Scale Data Processing**: Memory monitoring, pagination
3. **LLM Cost Control**: Budget limits, model selection
4. **Data Accuracy**: Regular validation, human review

### Mitigation Strategies
- Comprehensive error handling and recovery
- Automated rollback capabilities
- Circuit breaker patterns for external APIs
- Real-time monitoring and alerting
- Regular disaster recovery testing