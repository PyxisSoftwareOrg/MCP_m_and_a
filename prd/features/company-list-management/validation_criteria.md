# Company List Management - Validation Criteria

## Automated Test Specifications

### 1. List Creation Tests

#### Test 1.1: Create Basic Company List
```python
def test_create_basic_list():
    """Verify basic list creation with required fields"""
    # Given: Valid list name and type
    # When: create_company_list is called
    # Then: List is created with unique ID
    # And: List appears in get_company_lists
    # And: S3 storage contains list metadata
```

#### Test 1.2: Create List with Initial Companies
```python
def test_create_list_with_companies():
    """Verify list creation with initial company set"""
    # Given: List of 10 valid company names
    # When: create_company_list with initial_companies
    # Then: List contains exactly 10 companies
    # And: Company membership records are created
    # And: List statistics show correct count
```

#### Test 1.3: Create Dynamic List
```python
def test_create_dynamic_list():
    """Verify dynamic list creation and evaluation"""
    # Given: Dynamic rules for score > 8.0
    # When: create_company_list with dynamic_rules
    # Then: List auto-populates with matching companies
    # And: List updates when new companies match
    # And: Scheduled refresh is configured
```

### 2. Company Management Tests

#### Test 2.1: Add Companies to List
```python
def test_add_companies():
    """Verify adding companies to existing list"""
    # Given: List with 5 companies
    # When: add_companies_to_list with 3 new companies
    # Then: List contains 8 companies
    # And: No duplicates are added
    # And: Audit trail shows additions
```

#### Test 2.2: Bulk Move Companies
```python
def test_bulk_move_companies():
    """Verify moving companies between lists"""
    # Given: Source list with 20 companies, empty target
    # When: move_companies_between_lists with 10 companies
    # Then: Source has 10, target has 10
    # And: Company positions are preserved
    # And: Move is atomic (all or nothing)
```

#### Test 2.3: Remove Companies with Archival
```python
def test_remove_companies_archive():
    """Verify company removal with archive reason"""
    # Given: List with companies to remove
    # When: remove_companies_from_list with archive_reason
    # Then: Companies removed from active list
    # And: Archive record created with reason
    # And: Companies can be recovered
```

### 3. Search and Filter Tests

#### Test 3.1: Search Lists by Name
```python
def test_search_lists_by_name():
    """Verify list search functionality"""
    # Given: 50 lists with various names
    # When: search_lists with query "software"
    # Then: Returns all lists containing "software"
    # And: Results ordered by relevance
    # And: Response time < 500ms
```

#### Test 3.2: Filter Lists by Criteria
```python
def test_filter_lists():
    """Verify list filtering by multiple criteria"""
    # Given: Lists with different types and owners
    # When: get_company_lists with filters
    # Then: Only matching lists returned
    # And: Statistics included if requested
    # And: Pagination works correctly
```

### 4. Performance Tests

#### Test 4.1: Large List Performance
```python
def test_large_list_performance():
    """Verify performance with 1000-company list"""
    # Given: List with 1000 companies
    # When: get_list_companies with pagination
    # Then: First page loads in < 2 seconds
    # And: Subsequent pages load in < 1 second
    # And: Memory usage stays under 512MB
```

#### Test 4.2: Concurrent Operations
```python
def test_concurrent_list_operations():
    """Verify system handles concurrent updates"""
    # Given: Single list
    # When: 10 concurrent add/remove operations
    # Then: All operations succeed or fail cleanly
    # And: Final state is consistent
    # And: No data corruption occurs
```

### 5. Integration Tests

#### Test 5.1: Analysis Integration
```python
def test_bulk_analyze_integration():
    """Verify bulk analysis for list companies"""
    # Given: List with 10 companies
    # When: bulk_analyze_list is called
    # Then: All companies queued for analysis
    # And: Progress tracking available
    # And: List statistics update after completion
```

#### Test 5.2: Export Integration
```python
def test_list_export():
    """Verify list export functionality"""
    # Given: List with analyzed companies
    # When: Export list to Excel
    # Then: Excel contains all company data
    # And: List metadata included
    # And: Formatting is correct
```

### 6. Security Tests

#### Test 6.1: Permission Enforcement
```python
def test_permission_enforcement():
    """Verify access control works correctly"""
    # Given: User without write permission
    # When: Attempt to modify list
    # Then: Operation rejected with 403
    # And: Audit log shows attempt
    # And: List remains unchanged
```

#### Test 6.2: Data Validation
```python
def test_input_validation():
    """Verify all inputs are validated"""
    # Given: Various invalid inputs
    # When: Tools called with bad data
    # Then: Appropriate errors returned
    # And: No partial updates occur
    # And: System remains stable
```

## Manual Testing Procedures

### 1. User Workflow Testing

#### Workflow 1: New User Onboarding
1. User logs in for first time
2. System shows list creation tutorial
3. User creates first list from template
4. User imports companies from CSV
5. Verify smooth experience and clear guidance

#### Workflow 2: Weekly Review Process
1. User opens "Weekly Review" list
2. Triggers re-analysis for all companies
3. Reviews score changes in UI
4. Moves companies between pipeline stages
5. Exports updated list for team meeting

### 2. Edge Case Testing

#### Edge Case 1: Network Interruption
1. Start bulk operation (move 50 companies)
2. Simulate network disconnection mid-operation
3. Verify operation rolls back cleanly
4. Verify user sees clear error message
5. Verify retry succeeds

#### Edge Case 2: Concurrent Editing
1. Two users open same list
2. Both try to add same company
3. Verify only one addition succeeds
4. Verify both users see updated state
5. Verify no data inconsistency

### 3. Performance Testing

#### Load Test 1: Maximum Lists
1. Create 50 custom lists (user limit)
2. Add 1000 companies to each list
3. Verify system remains responsive
4. Verify search still works quickly
5. Monitor resource usage

#### Load Test 2: Simultaneous Users
1. Simulate 100 concurrent users
2. Each user performs list operations
3. Verify response times stay under SLA
4. Verify no errors or timeouts
5. Check for any data corruption

## Acceptance Criteria

### Functional Requirements
- [ ] All 10 MCP tools working correctly
- [ ] Dynamic lists update within 15 minutes
- [ ] Bulk operations handle 100 companies
- [ ] Search returns results in < 500ms
- [ ] Export completes in < 10 seconds

### Performance Requirements
- [ ] Page load time < 2 seconds
- [ ] API response time < 500ms (p95)
- [ ] Support 1000 companies per list
- [ ] Handle 100 concurrent users
- [ ] Cache hit rate > 80%

### Security Requirements
- [ ] RBAC fully implemented
- [ ] All inputs validated
- [ ] Audit trail complete
- [ ] No data leakage between users
- [ ] Secure sharing mechanism

### Data Integrity
- [ ] No data loss during operations
- [ ] Soft delete recovery working
- [ ] Atomic operations (all or nothing)
- [ ] Consistent state after failures
- [ ] Backup and restore functional

### User Experience
- [ ] Intuitive list creation flow
- [ ] Clear error messages
- [ ] Responsive UI updates
- [ ] Helpful empty states
- [ ] Undo available for destructive actions

## Monitoring and Alerts

### Key Metrics to Track
```yaml
metrics:
  - name: list_creation_rate
    threshold: < 10/minute alerts
  - name: api_response_time
    threshold: > 1s alerts
  - name: error_rate
    threshold: > 1% alerts
  - name: cache_hit_rate
    threshold: < 70% alerts
  - name: storage_usage
    threshold: > 80% capacity alerts
```

### Dashboard Requirements
1. Total lists and growth trend
2. Most active lists
3. API performance metrics
4. Error rate by operation
5. User adoption metrics

## Sign-off Criteria

### Development Team
- [ ] All tests passing
- [ ] Code coverage > 90%
- [ ] Performance benchmarks met
- [ ] Security review passed

### Product Team
- [ ] Feature demo approved
- [ ] UX review completed
- [ ] Documentation ready
- [ ] Training materials created

### Operations Team
- [ ] Monitoring configured
- [ ] Alerts tested
- [ ] Runbooks created
- [ ] Backup procedures verified

### Executive Sign-off
- [ ] Business value demonstrated
- [ ] Risk assessment completed
- [ ] Go-live plan approved
- [ ] Success metrics defined