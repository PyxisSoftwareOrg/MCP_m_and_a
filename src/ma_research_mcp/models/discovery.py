"""
Data models for automated company discovery
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DiscoveryRequest(BaseModel):
    """Request model for company discovery"""
    company_name: str
    industry_hint: Optional[str] = None
    location_hint: Optional[str] = None
    company_type_hint: Optional[str] = None  # "software", "saas", etc.
    discovery_timeout: int = Field(default=30, description="Timeout in seconds")
    required_sources: List[str] = Field(
        default=["website", "linkedin"],
        description="Sources that must be attempted"
    )
    optional_sources: List[str] = Field(
        default=["crunchbase", "google_kg"],
        description="Additional sources to try"
    )


class WebsiteDiscoveryResult(BaseModel):
    """Result from website discovery attempt"""
    url: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)
    domain_verified: bool = False
    ssl_valid: bool = False
    company_name_match: bool = False
    discovery_method: Optional[str] = None  # "direct", "search", etc.


class LinkedInDiscoveryResult(BaseModel):
    """Result from LinkedIn discovery attempt"""
    url: Optional[str] = None
    company_id: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    employee_count: Optional[int] = None
    employee_range: Optional[str] = None
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    verified_badge: bool = False


class CrunchbaseData(BaseModel):
    """Crunchbase company information"""
    uuid: str
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    founded_year: Optional[int] = None
    employee_range: Optional[str] = None
    revenue_range: Optional[str] = None
    total_funding_usd: Optional[float] = None
    last_funding_date: Optional[str] = None
    investors: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    linkedin_url: Optional[str] = None
    exit_count: int = 0


class GoogleKnowledgeGraphData(BaseModel):
    """Google Knowledge Graph entity data"""
    entity_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    types: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    image_url: Optional[str] = None
    detailed_description: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class DiscoveryMetadata(BaseModel):
    """Metadata about the discovery process"""
    total_sources_checked: int = 0
    successful_sources: List[str] = Field(default_factory=list)
    failed_sources: Dict[str, str] = Field(default_factory=dict)  # source: error
    discovery_duration_seconds: float = 0.0
    api_calls_made: Dict[str, int] = Field(default_factory=dict)  # api: count
    estimated_cost_usd: float = 0.0
    cache_hits: Dict[str, bool] = Field(default_factory=dict)


class ValidationConflict(BaseModel):
    """Data conflict between sources"""
    field: str
    sources: Dict[str, Any]  # source: value
    severity: str = Field(default="low", pattern="^(low|medium|high)$")
    resolution: Optional[str] = None


class DiscoveryResult(BaseModel):
    """Complete discovery result for a company"""
    request_id: str = Field(default_factory=lambda: f"disc_{int(datetime.utcnow().timestamp())}")
    company_name: str
    normalized_name: str
    discovery_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Discovered URLs and data
    website_discovery: Optional[WebsiteDiscoveryResult] = None
    linkedin_discovery: Optional[LinkedInDiscoveryResult] = None
    
    # Additional sources
    crunchbase_url: Optional[str] = None
    crunchbase_data: Optional[CrunchbaseData] = None
    
    google_kg_data: Optional[GoogleKnowledgeGraphData] = None
    google_search_results: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Validation results
    cross_validation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    validation_conflicts: List[ValidationConflict] = Field(default_factory=list)
    
    # Metadata
    discovery_metadata: DiscoveryMetadata
    
    @property
    def website_url(self) -> Optional[str]:
        """Get the discovered website URL"""
        return self.website_discovery.url if self.website_discovery else None
    
    @property
    def linkedin_url(self) -> Optional[str]:
        """Get the discovered LinkedIn URL"""
        return self.linkedin_discovery.url if self.linkedin_discovery else None
    
    @property
    def has_sufficient_data(self) -> bool:
        """Check if enough data was discovered for analysis"""
        return bool(self.website_url or self.linkedin_url or self.crunchbase_data)