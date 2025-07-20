# Company List Management - Technical Design

## Technical Architecture

### Data Models

#### CompanyList Model
```python
class CompanyList(BaseModel):
    list_id: str = Field(default_factory=lambda: f"list_{uuid4()}")
    list_name: str
    list_type: Literal["active", "future", "watchlist", "archived", "custom"]
    description: Optional[str] = None
    owner_id: str
    created_at: datetime
    updated_at: datetime
    
    # List configuration
    is_dynamic: bool = False
    dynamic_rules: Optional[Dict[str, Any]] = None
    auto_refresh_hours: Optional[int] = None
    
    # Metadata
    company_count: int = 0
    average_score: Optional[float] = None
    last_analysis_date: Optional[datetime] = None
    tags: List[str] = []
    
    # Access control
    visibility: Literal["private", "team", "public"] = "private"
    shared_with: List[str] = []
    permissions: Dict[str, List[str]] = {}  # user_id: ["read", "write", "admin"]
    
    # List statistics
    statistics: CompanyListStatistics

class CompanyListMembership(BaseModel):
    membership_id: str = Field(default_factory=lambda: f"mem_{uuid4()}")
    list_id: str
    company_name: str
    added_date: datetime
    added_by: str
    position: Optional[int] = None  # For ordered lists
    custom_notes: Optional[str] = None
    tags: List[str] = []
    
    # Cached company data for performance
    cached_score: Optional[float] = None
    cached_tier: Optional[str] = None
    cached_analysis_date: Optional[datetime] = None

class CompanyListStatistics(BaseModel):
    total_companies: int = 0
    score_distribution: Dict[str, int] = {}  # {"0-5": 10, "5-7": 20, "7-9": 15, "9-10": 5}
    tier_distribution: Dict[str, int] = {}  # {"VIP": 5, "High": 15, "Medium": 20, "Low": 10}
    geographic_distribution: Dict[str, int] = {}
    industry_distribution: Dict[str, int] = {}
    average_age_days: Optional[float] = None
    needs_refresh_count: int = 0
```

### MCP Tools

#### 1. create_company_list
```python
@mcp.tool
async def create_company_list(
    list_name: str,
    list_type: str = "custom",
    description: Optional[str] = None,
    initial_companies: Optional[List[str]] = None,
    dynamic_rules: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create a new company list with optional initial companies"""
```

#### 2. add_companies_to_list
```python
@mcp.tool
async def add_companies_to_list(
    list_id: str,
    company_names: List[str],
    import_source: Optional[str] = None,  # "manual", "csv", "analysis_results"
    custom_notes: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Add companies to an existing list"""
```

#### 3. remove_companies_from_list
```python
@mcp.tool
async def remove_companies_from_list(
    list_id: str,
    company_names: List[str],
    archive_reason: Optional[str] = None
) -> Dict[str, Any]:
    """Remove companies from a list"""
```

#### 4. move_companies_between_lists
```python
@mcp.tool
async def move_companies_between_lists(
    company_names: List[str],
    source_list_id: str,
    target_list_id: str,
    copy_instead_of_move: bool = False
) -> Dict[str, Any]:
    """Move or copy companies between lists"""
```

#### 5. get_company_lists
```python
@mcp.tool
async def get_company_lists(
    list_types: Optional[List[str]] = None,
    owner_id: Optional[str] = None,
    include_shared: bool = True,
    include_statistics: bool = True
) -> List[Dict[str, Any]]:
    """Get all available company lists with metadata"""
```

#### 6. get_list_companies
```python
@mcp.tool
async def get_list_companies(
    list_id: str,
    include_analysis_data: bool = False,
    sort_by: str = "added_date",
    sort_order: str = "desc",
    limit: Optional[int] = None,
    offset: int = 0
) -> Dict[str, Any]:
    """Get companies in a specific list"""
```

#### 7. update_list_metadata
```python
@mcp.tool
async def update_list_metadata(
    list_id: str,
    list_name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    visibility: Optional[str] = None,
    dynamic_rules: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Update list metadata and configuration"""
```

#### 8. delete_company_list
```python
@mcp.tool
async def delete_company_list(
    list_id: str,
    confirm_delete: bool = False,
    archive_instead: bool = True
) -> Dict[str, Any]:
    """Delete or archive a company list"""
```

#### 9. bulk_analyze_list
```python
@mcp.tool
async def bulk_analyze_list(
    list_id: str,
    force_refresh: bool = False,
    analysis_options: Optional[Dict[str, Any]] = None,
    max_parallel: int = 5
) -> Dict[str, Any]:
    """Trigger analysis for all companies in a list"""
```

#### 10. search_lists
```python
@mcp.tool
async def search_lists(
    query: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    include_company_names: bool = False
) -> List[Dict[str, Any]]:
    """Search across all lists and optionally their companies"""
```

### S3 Storage Structure

```
s3://ma-research-bucket/
├── lists/
│   ├── metadata/
│   │   ├── all_lists.json          # Index of all lists
│   │   └── {list_id}/
│   │       ├── config.json         # List configuration
│   │       ├── permissions.json    # Access control
│   │       └── statistics.json     # Cached statistics
│   ├── memberships/
│   │   └── {list_id}/
│   │       ├── companies.json      # Full membership data
│   │       └── companies_lite.json # Lightweight version
│   ├── templates/
│   │   ├── default_lists.json      # System templates
│   │   └── user_{user_id}/         # User templates
│   └── archives/
│       └── {timestamp}/
│           └── {list_id}.json       # Archived lists
```

### API Endpoints (Internal)

```python
# List Management
GET    /lists                      # Get all lists
POST   /lists                      # Create new list
GET    /lists/{list_id}           # Get list details
PUT    /lists/{list_id}           # Update list
DELETE /lists/{list_id}           # Delete list

# Company Management
GET    /lists/{list_id}/companies  # Get companies in list
POST   /lists/{list_id}/companies  # Add companies
DELETE /lists/{list_id}/companies  # Remove companies
PUT    /lists/{list_id}/companies  # Update company metadata

# Bulk Operations
POST   /lists/bulk/move           # Move companies between lists
POST   /lists/bulk/analyze        # Analyze all in list
POST   /lists/bulk/export         # Export list data

# Search and Filter
GET    /lists/search              # Search lists
POST   /lists/dynamic/evaluate    # Evaluate dynamic rules
```

### Performance Optimizations

#### Caching Strategy
```python
CACHE_CONFIG = {
    "list_metadata": {
        "ttl_seconds": 300,  # 5 minutes
        "key_pattern": "list:metadata:{list_id}"
    },
    "list_companies": {
        "ttl_seconds": 60,   # 1 minute
        "key_pattern": "list:companies:{list_id}:{page}"
    },
    "list_statistics": {
        "ttl_seconds": 900,  # 15 minutes
        "key_pattern": "list:stats:{list_id}"
    },
    "user_lists": {
        "ttl_seconds": 180,  # 3 minutes
        "key_pattern": "user:lists:{user_id}"
    }
}
```

#### Database Indexes
- `lists.owner_id` - For user's lists queries
- `lists.list_type` - For filtering by type
- `lists.created_at` - For sorting
- `memberships.list_id` - For company lookups
- `memberships.company_name` - For cross-list search

#### Batch Processing
```python
class ListBatchProcessor:
    def __init__(self, max_batch_size: int = 100):
        self.max_batch_size = max_batch_size
        self.queue = asyncio.Queue()
        
    async def process_batch(self, operations: List[Dict]):
        """Process operations in batches for efficiency"""
        # Group by operation type
        # Execute in parallel where possible
        # Update caches after completion
```

### Security Considerations

#### Access Control
```python
class ListPermissionChecker:
    @staticmethod
    async def can_read(user_id: str, list_id: str) -> bool:
        """Check if user can read list"""
        
    @staticmethod
    async def can_write(user_id: str, list_id: str) -> bool:
        """Check if user can modify list"""
        
    @staticmethod
    async def can_admin(user_id: str, list_id: str) -> bool:
        """Check if user can delete/share list"""
```

#### Data Validation
- List name: 1-100 characters, alphanumeric + spaces
- Description: Maximum 1000 characters
- Tags: Maximum 20 tags, 50 characters each
- Dynamic rules: JSON schema validation
- Company names: Must exist in system

### Error Handling

```python
class ListManagementError(Exception):
    """Base exception for list operations"""

class ListNotFoundError(ListManagementError):
    """List does not exist"""

class ListPermissionError(ListManagementError):
    """User lacks required permissions"""

class ListSizeLimitError(ListManagementError):
    """List exceeds size limits"""

class DuplicateCompanyError(ListManagementError):
    """Company already exists in list"""
```

### Monitoring and Metrics

```python
METRICS = {
    "list_operations": {
        "create_list": Counter,
        "update_list": Counter,
        "delete_list": Counter,
        "add_companies": Histogram,
        "remove_companies": Histogram
    },
    "performance": {
        "list_load_time": Histogram,
        "bulk_operation_time": Histogram,
        "cache_hit_rate": Gauge
    },
    "usage": {
        "total_lists": Gauge,
        "total_companies_in_lists": Gauge,
        "active_dynamic_lists": Gauge
    }
}
```

### Integration Points

#### With Core Analysis
- Subscribe to analysis completion events
- Update cached scores automatically
- Trigger re-analysis from list view

#### With Export System
- Export list as CSV/Excel
- Include list metadata in exports
- Bulk export multiple lists

#### With Notification System
- List update notifications
- Dynamic list match alerts
- Scheduled summary emails