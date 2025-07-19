"""
Company-related data models
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class CompanyMetadata(BaseModel):
    """Basic company metadata"""
    company_name: str
    website_url: str
    linkedin_url: Optional[str] = None
    headquarters_location: Optional[str] = None
    industry_vertical: Optional[str] = None
    founding_year: Optional[int] = None
    employee_count: Optional[int] = None
    estimated_revenue: Optional[float] = None
    funding_stage: Optional[str] = None
    last_funding_date: Optional[str] = None
    last_funding_amount: Optional[float] = None
    primary_business_model: Optional[str] = None
    target_market: Optional[str] = None
    primary_product: Optional[str] = None
    key_executives: List[Dict[str, str]] = []
    competitors: List[str] = []
    technology_stack: List[str] = []
    certifications: List[str] = []
    partnerships: List[str] = []
    awards: List[str] = []


class CompanyList(BaseModel):
    """Company list management"""
    list_type: str  # "active" or "future_candidate"
    company_name: str
    added_date: str
    added_by: str
    
    # Current status
    automated_tier: str
    automated_score: float
    manual_tier_override: Optional[str] = None
    override_reason: Optional[str] = None
    override_by: Optional[str] = None
    override_date: Optional[str] = None
    
    # Monitoring configuration
    monitoring_frequency: str  # "weekly", "monthly", "quarterly"
    alert_thresholds: Dict[str, float] = {}
    
    # Promotion tracking
    promotion_criteria_met: bool = False
    promotion_blockers: List[str] = []
    
    # Engagement tracking
    last_contact_date: Optional[str] = None
    next_contact_date: Optional[str] = None
    engagement_level: str = "low"  # "low", "medium", "high", "vip"
    contact_frequency_days: int = 30
    
    # Notes and history
    notes: List[Dict[str, Any]] = []
    status_history: List[Dict[str, Any]] = []
    
    # Performance metrics
    total_analyses: int = 0
    score_trend: List[float] = []
    last_analysis_date: Optional[str] = None