"""
Scoring system data models
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ScoringDimension(BaseModel):
    """Individual scoring dimension configuration"""
    dimension_id: str
    dimension_name: str
    description: str
    weight: float
    min_score: float = 0.0
    max_score: float = 10.0
    scoring_criteria: Dict[str, Any]
    prompt_template: str
    evaluation_examples: List[Dict[str, Any]] = []
    is_required: bool = True


class ScoringSystem(BaseModel):
    """Complete scoring system configuration"""
    system_id: str
    system_name: str
    description: str
    owner: str
    is_active: bool = True
    is_default: bool = False
    created_at: str
    updated_at: str
    
    # Scoring configuration
    dimensions: List[ScoringDimension]
    weights: Dict[str, float]  # dimension_id -> weight
    thresholds: Dict[str, float]  # tier_name -> min_score
    
    # Customization
    custom_prompts: Dict[str, str] = {}
    custom_rules: Dict[str, Any] = {}
    preprocessing_rules: List[str] = []
    postprocessing_rules: List[str] = []
    
    # Metadata
    version: str = "1.0"
    tags: List[str] = []
    usage_stats: Dict[str, int] = {}


class ScoringSystemResult(BaseModel):
    """Results from a specific scoring system"""
    system_id: str
    system_name: str
    execution_timestamp: str
    
    # Individual dimension scores
    dimension_scores: Dict[str, "ScoreDimension"]
    
    # Overall results
    weighted_score: float
    unweighted_score: float
    confidence_score: float
    
    # Analysis
    key_insights: List[str]
    recommendation: str
    tier_assignment: str
    
    # Execution metadata
    execution_time_seconds: float
    tokens_used: int
    api_calls_made: int
    errors: List[str] = []


# Default scoring system dimensions
DEFAULT_SCORING_DIMENSIONS = [
    {
        "dimension_id": "vms_focus",
        "dimension_name": "Vertical Market Software Focus",
        "description": "How tailored the software is to specific industries",
        "weight": 1.0,
        "max_score": 5.0,
        "scoring_criteria": {
            "5": "Highly specialized for specific vertical",
            "4": "Mostly vertical with some horizontal features", 
            "3": "Mixed vertical/horizontal approach",
            "2": "Mostly horizontal with vertical adaptations",
            "1": "Pure horizontal solution"
        }
    },
    {
        "dimension_id": "revenue_model", 
        "dimension_name": "Revenue Model",
        "description": "Percentage of revenue from software licenses vs services",
        "weight": 1.0,
        "max_score": 5.0,
        "scoring_criteria": {
            "5": "90%+ software revenue",
            "4": "75-90% software revenue",
            "3": "60-75% software revenue", 
            "2": "40-60% software revenue",
            "1": "Less than 40% software revenue"
        }
    },
    {
        "dimension_id": "suite_vs_point",
        "dimension_name": "Suite vs Point Solution", 
        "description": "Solution comprehensiveness",
        "weight": 1.0,
        "max_score": 5.0,
        "scoring_criteria": {
            "5": "Complete integrated suite",
            "4": "Suite with most core modules",
            "3": "Modular platform approach",
            "2": "Point solution with integrations", 
            "1": "Pure point solution"
        }
    },
    {
        "dimension_id": "customer_quality",
        "dimension_name": "Customer Base Quality",
        "description": "Barriers to entry in target industries", 
        "weight": 1.0,
        "max_score": 5.0,
        "scoring_criteria": {
            "5": "Very high barriers, sticky customers",
            "4": "High barriers, good retention",
            "3": "Moderate barriers, average retention",
            "2": "Low barriers, price-sensitive",
            "1": "Commodity market, high churn"
        }
    },
    {
        "dimension_id": "pricing_levels",
        "dimension_name": "Pricing Levels",
        "description": "Annual pricing tiers",
        "weight": 1.0,
        "min_score": 5.0,
        "max_score": 10.0,
        "scoring_criteria": {
            "10": "$50K+ annual pricing",
            "9": "$25-50K annual pricing", 
            "8": "$10-25K annual pricing",
            "7": "$5-10K annual pricing",
            "6": "$2-5K annual pricing",
            "5": "Under $2K annual pricing"
        }
    },
    {
        "dimension_id": "funding_source",
        "dimension_name": "Funding Source (OPM)",
        "description": "Government vs private sector dependency",
        "weight": 1.0,
        "min_score": 5.0,
        "max_score": 10.0,
        "scoring_criteria": {
            "10": "100% private sector revenue",
            "8": "Mostly private with some government",
            "6": "Mixed private/government revenue",
            "5": "Heavily dependent on government funding"
        }
    },
    {
        "dimension_id": "company_maturity",
        "dimension_name": "Company Maturity",
        "description": "Size, growth rate, and age",
        "weight": 1.0,
        "min_score": 5.0,
        "max_score": 9.0,
        "scoring_criteria": {
            "9": "Mature, stable, profitable growth",
            "8": "Growth stage, strong metrics",
            "7": "Established with good fundamentals",
            "6": "Developing stage, showing progress",
            "5": "Early stage, high potential"
        }
    },
    {
        "dimension_id": "ownership_profile",
        "dimension_name": "Ownership Profile", 
        "description": "Funding vs revenue ratio",
        "weight": 1.0,
        "min_score": 5.0,
        "max_score": 9.0,
        "scoring_criteria": {
            "9": "Bootstrapped or profitable",
            "8": "Minimal funding, strong revenue",
            "7": "Moderate funding, good revenue growth",
            "6": "Well-funded, proving revenue model",
            "5": "Heavy funding, developing revenue"
        }
    }
]