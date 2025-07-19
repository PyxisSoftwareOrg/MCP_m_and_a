"""
Analysis-related data models
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AnalysisMetadata(BaseModel):
    """Metadata for analysis execution"""
    analysis_id: str
    created_at: str
    analysis_duration_seconds: float
    bedrock_tokens_used: int
    bedrock_requests_made: int
    apify_requests_made: int
    pages_scraped: int
    data_sources_used: List[str]
    errors_encountered: List[str] = []
    warnings: List[str] = []
    cost_estimate_usd: float = 0.0


class ExportMetadata(BaseModel):
    """Metadata for exports"""
    export_id: str
    export_format: str
    created_at: str
    expires_at: str
    file_size_bytes: int
    pre_signed_url: Optional[str] = None
    download_count: int = 0


class ScoreDimension(BaseModel):
    """Individual dimension score"""
    dimension_name: str
    score: float
    confidence: float
    evidence: List[str]
    reasoning: str
    data_sources: List[str]


class QualificationResult(BaseModel):
    """Lead qualification results"""
    is_qualified: bool
    qualification_score: float
    disqualification_reasons: List[str]
    geographic_qualification: bool
    business_model_qualification: bool
    size_maturity_qualification: bool
    q1_horizontal_vs_vertical: str
    q2_point_vs_suite: str
    q3_mission_critical: str
    q4_opm_vs_private: str
    q5_arpu_level: str
    qualification_confidence: float


class FilteringResult(BaseModel):
    """Company filtering results"""
    passed_geographic_filter: bool
    passed_business_model_filter: bool
    passed_size_maturity_filter: bool
    overall_filter_result: bool
    filter_notes: List[str]
    geographic_region: str
    business_model_type: str
    estimated_revenue: Optional[float] = None
    estimated_employees: Optional[int] = None
    company_age_years: Optional[int] = None


class OverrideMetadata(BaseModel):
    """Tier override metadata"""
    override_by: str
    override_date: str
    override_reason: str
    approval_status: str
    approved_by: Optional[str] = None
    approval_date: Optional[str] = None


class InvestmentThesis(BaseModel):
    """AI-generated investment thesis"""
    thesis_type: str
    strategic_rationale: str
    vms_alignment_score: float
    financial_profile: Dict[str, Any]
    growth_trajectory: str
    execution_factors: List[str]
    integration_complexity: str
    risk_assessment: Dict[str, Any]
    mitigation_strategies: List[str]
    recommendation: str
    confidence_level: float
    generated_at: str


class NurturingPlan(BaseModel):
    """Lead nurturing plan"""
    current_tier: str
    engagement_frequency: str
    next_contact_date: str
    planned_activities: List[str]
    contact_history: List[Dict[str, Any]]
    escalation_triggers: List[str]
    success_metrics: Dict[str, Any]


class LikelihoodFactors(BaseModel):
    """Likelihood assessment factors"""
    market_position: Optional[str] = None
    competitive_landscape: Optional[str] = None
    team_quality: Optional[str] = None
    location_factors: Optional[str] = None
    operational_challenges: Optional[str] = None
    timing_indicators: Optional[str] = None
    motivation_signals: Optional[str] = None
    valuation_expectations: Optional[str] = None
    transaction_readiness: Optional[str] = None
    cultural_fit: Optional[str] = None


class AnalysisResult(BaseModel):
    """Complete analysis result for a company"""
    company_name: str
    analysis_timestamp: str
    website_url: str
    linkedin_url: Optional[str] = None
    list_type: str  # "active" or "future_candidate"
    
    # Qualification and filtering
    qualification_result: QualificationResult
    filtering_result: FilteringResult
    
    # Scoring results
    scoring_results: Dict[str, Any]  # Results from different scoring systems
    default_scores: Dict[str, ScoreDimension]
    overall_score: float
    
    # Analysis outputs
    recommendation: str
    key_strengths: List[str]
    key_concerns: List[str]
    
    # Tier management
    automated_tier: str
    manual_tier_override: Optional[str] = None
    override_metadata: Optional[OverrideMetadata] = None
    effective_tier: str
    
    # Additional assessments
    likelihood_factors: LikelihoodFactors
    investment_thesis: Optional[InvestmentThesis] = None
    nurturing_plan: Optional[NurturingPlan] = None
    
    # Metadata
    metadata: AnalysisMetadata
    export_metadata: Optional[ExportMetadata] = None