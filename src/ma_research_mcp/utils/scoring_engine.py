"""
Scoring engine for M&A Research Assistant
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..models import DEFAULT_SCORING_DIMENSIONS, ScoringDimension, ScoringSystem, ScoreDimension
from ..services import BedrockLLMService, S3Service

logger = logging.getLogger(__name__)


class ScoringEngine:
    """8-dimension scoring system with LLM evaluation"""
    
    def __init__(self):
        self.llm_service = BedrockLLMService()
        self.s3_service = S3Service()
        
        # Initialize default scoring system
        self.default_system = self._create_default_scoring_system()
        
        logger.info("Initialized scoring engine")
    
    def _create_default_scoring_system(self) -> ScoringSystem:
        """Create the default 8-dimension scoring system"""
        dimensions = []
        
        for dim_config in DEFAULT_SCORING_DIMENSIONS:
            dimension = ScoringDimension(
                dimension_id=dim_config["dimension_id"],
                dimension_name=dim_config["dimension_name"],
                description=dim_config["description"],
                weight=dim_config["weight"],
                min_score=dim_config.get("min_score", 0.0),
                max_score=dim_config["max_score"],
                scoring_criteria=dim_config["scoring_criteria"],
                prompt_template=self._get_dimension_prompt_template(dim_config["dimension_id"]),
                is_required=True
            )
            dimensions.append(dimension)
        
        return ScoringSystem(
            system_id="default",
            system_name="Default M&A Scoring System",
            description="Standard 8-dimension scoring system for M&A evaluation",
            owner="system",
            is_default=True,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            dimensions=dimensions,
            weights={dim.dimension_id: dim.weight for dim in dimensions},
            thresholds={
                "vip": 9.0,
                "high": 7.0,
                "medium": 5.0,
                "low": 0.0
            }
        )
    
    def _get_dimension_prompt_template(self, dimension_id: str) -> str:
        """Get LLM prompt template for specific dimension"""
        templates = {
            "vms_focus": """
Analyze how specialized this company's software is for specific vertical markets.

VMS (Vertical Market Software) characteristics to look for:
- Industry-specific terminology and features
- Compliance with industry regulations
- Workflow specific to the vertical
- Deep domain expertise requirements
- Industry-specific integrations

Score 1-5 where:
5 = Highly specialized for specific vertical (e.g., dental practice management)
4 = Mostly vertical with some horizontal features
3 = Mixed vertical/horizontal approach
2 = Mostly horizontal with vertical adaptations
1 = Pure horizontal solution (e.g., generic CRM)
""",
            
            "revenue_model": """
Analyze the company's revenue composition between software and services.

Look for indicators of:
- Software license revenue vs consulting/implementation fees
- Recurring subscription revenue vs one-time services
- Product revenue vs professional services
- SaaS model vs custom development

Score 1-5 where:
5 = 90%+ software revenue (pure SaaS/license model)
4 = 75-90% software revenue
3 = 60-75% software revenue
2 = 40-60% software revenue  
1 = Less than 40% software revenue (service-heavy)
""",
            
            "suite_vs_point": """
Analyze whether this is a comprehensive suite or point solution.

Suite characteristics:
- Multiple integrated modules/products
- End-to-end workflow coverage
- Unified platform approach
- Cross-module data sharing

Point solution characteristics:
- Single primary function/use case
- Narrow problem focus
- Standalone application

Score 1-5 where:
5 = Complete integrated suite covering entire workflow
4 = Suite with most core modules present
3 = Modular platform approach with key integrations
2 = Point solution with some integrations
1 = Pure point solution, single function
""",
            
            "customer_quality": """
Analyze the barriers to entry and customer stickiness in target markets.

High-quality customer indicators:
- Regulated industries with compliance requirements
- High switching costs
- Mission-critical applications
- Specialized expertise required
- Long implementation cycles

Score 1-5 where:
5 = Very high barriers, extremely sticky customers (healthcare, finance)
4 = High barriers, good retention (specialized professional services)
3 = Moderate barriers, average retention
2 = Low barriers, price-sensitive customers
1 = Commodity market, high churn potential
""",
            
            "pricing_levels": """
Analyze the annual pricing levels and value proposition.

Look for:
- Per-user/per-month pricing
- Enterprise license fees
- Annual contract values
- Premium pricing indicators

Score 5-10 where:
10 = $50K+ annual pricing (enterprise, mission-critical)
9 = $25-50K annual pricing
8 = $10-25K annual pricing
7 = $5-10K annual pricing
6 = $2-5K annual pricing
5 = Under $2K annual pricing
""",
            
            "funding_source": """
Analyze dependency on government vs private sector revenue.

Government/OPM indicators:
- Government contracts mentioned
- Public sector customers
- Grant funding
- Regulatory compliance focus

Private sector indicators:
- Commercial customers
- Private company clients
- Market-driven pricing
- Competitive differentiation

Score 5-10 where:
10 = 100% private sector revenue
8 = Mostly private with some government
6 = Mixed private/government revenue  
5 = Heavily dependent on government funding
""",
            
            "company_maturity": """
Analyze company size, growth trajectory, and operational maturity.

Maturity indicators:
- Years in business
- Employee count and growth
- Revenue scale and growth
- Market position
- Operational sophistication

Score 5-9 where:
9 = Mature, stable, profitable growth (10+ years, 100+ employees)
8 = Growth stage, strong metrics (5-10 years, 50+ employees)
7 = Established with good fundamentals (3-7 years, 25+ employees)
6 = Developing stage, showing progress (2-5 years, 10+ employees)
5 = Early stage, high potential (1-3 years, small team)
""",
            
            "ownership_profile": """
Analyze the funding vs revenue relationship and ownership structure.

Evaluate:
- Funding raised vs revenue generated
- Bootstrap vs venture-backed
- Debt vs equity financing
- Revenue sustainability

Score 5-9 where:
9 = Bootstrapped or profitable, minimal external funding
8 = Minimal funding, strong revenue base
7 = Moderate funding, good revenue growth trajectory
6 = Well-funded, proving revenue model
5 = Heavy funding, still developing sustainable revenue
"""
        }
        
        return templates.get(dimension_id, "Analyze this dimension and provide a score with evidence.")
    
    async def score_company(
        self,
        company_data: Dict[str, Any],
        scoring_system_id: str = "default"
    ) -> Dict[str, Any]:
        """Score company using specified scoring system"""
        try:
            # Get scoring system
            if scoring_system_id == "default":
                scoring_system = self.default_system
            else:
                scoring_system = await self.s3_service.get_scoring_system(scoring_system_id)
                if not scoring_system:
                    return {
                        "success": False,
                        "error": f"Scoring system {scoring_system_id} not found"
                    }
            
            logger.info(f"Scoring company with system: {scoring_system.system_name}")
            
            # Score each dimension
            dimension_scores = {}
            total_weighted_score = 0.0
            total_weights = 0.0
            errors = []
            
            # Process dimensions in parallel for efficiency
            tasks = []
            for dimension in scoring_system.dimensions:
                task = self._score_dimension(dimension, company_data)
                tasks.append((dimension.dimension_id, task))
            
            # Wait for all scoring tasks
            for dimension_id, task in tasks:
                try:
                    score_result = await task
                    if score_result["success"]:
                        dimension_score = score_result["dimension_score"]
                        dimension_scores[dimension_id] = ScoreDimension(
                            dimension_name=dimension_score.get("dimension_name", dimension_id),
                            score=dimension_score["score"],
                            confidence=dimension_score["confidence"],
                            evidence=dimension_score["evidence"],
                            reasoning=dimension_score["reasoning"],
                            data_sources=dimension_score["data_sources"]
                        )
                        
                        # Calculate weighted contribution
                        weight = scoring_system.weights.get(dimension_id, 1.0)
                        total_weighted_score += dimension_score["score"] * weight
                        total_weights += weight
                    else:
                        errors.append(f"Failed to score {dimension_id}: {score_result.get('error', 'Unknown error')}")
                        logger.error(f"Failed to score dimension {dimension_id}")
                
                except Exception as e:
                    errors.append(f"Error scoring {dimension_id}: {str(e)}")
                    logger.error(f"Error scoring dimension {dimension_id}: {e}")
            
            # Calculate overall score
            if total_weights > 0:
                overall_score = total_weighted_score / total_weights
            else:
                overall_score = 0.0
            
            # Determine tier
            tier = self._determine_tier(overall_score, scoring_system.thresholds)
            
            # Generate insights and recommendation
            insights = self._generate_insights(dimension_scores, overall_score)
            recommendation = self._generate_recommendation(overall_score, tier, insights)
            
            return {
                "success": True,
                "scoring_system_id": scoring_system_id,
                "scoring_system_name": scoring_system.system_name,
                "dimension_scores": {k: v.dict() for k, v in dimension_scores.items()},
                "overall_score": round(overall_score, 2),
                "weighted_score": round(total_weighted_score, 2),
                "total_weights": total_weights,
                "tier": tier,
                "insights": insights,
                "recommendation": recommendation,
                "errors": errors,
                "dimensions_scored": len(dimension_scores),
                "dimensions_total": len(scoring_system.dimensions)
            }
            
        except Exception as e:
            logger.error(f"Error in company scoring: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _score_dimension(
        self,
        dimension: ScoringDimension,
        company_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Score individual dimension using LLM"""
        try:
            result = await self.llm_service.score_dimension(
                dimension_name=dimension.dimension_name,
                dimension_description=dimension.description,
                scoring_criteria=dimension.scoring_criteria,
                company_data=company_data,
                min_score=dimension.min_score,
                max_score=dimension.max_score
            )
            
            if result["success"]:
                # Add dimension name to result
                result["dimension_score"]["dimension_name"] = dimension.dimension_name
            
            return result
            
        except Exception as e:
            logger.error(f"Error scoring dimension {dimension.dimension_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _determine_tier(self, score: float, thresholds: Dict[str, float]) -> str:
        """Determine tier based on score and thresholds"""
        if score >= thresholds.get("vip", 9.0):
            return "VIP"
        elif score >= thresholds.get("high", 7.0):
            return "HIGH"
        elif score >= thresholds.get("medium", 5.0):
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_insights(
        self,
        dimension_scores: Dict[str, ScoreDimension],
        overall_score: float
    ) -> List[str]:
        """Generate key insights from scoring results"""
        insights = []
        
        # Find highest and lowest scoring dimensions
        if dimension_scores:
            scores_list = [(k, v.score) for k, v in dimension_scores.items()]
            scores_list.sort(key=lambda x: x[1], reverse=True)
            
            highest = scores_list[0]
            lowest = scores_list[-1]
            
            insights.append(f"Strongest dimension: {highest[0]} (score: {highest[1]:.1f})")
            insights.append(f"Weakest dimension: {lowest[0]} (score: {lowest[1]:.1f})")
            
            # Identify high-scoring dimensions (above 8.0)
            high_scores = [item for item in scores_list if item[1] >= 8.0]
            if high_scores:
                high_dims = [item[0] for item in high_scores]
                insights.append(f"Excellent scores in: {', '.join(high_dims)}")
            
            # Identify concerning dimensions (below 5.0)
            low_scores = [item for item in scores_list if item[1] < 5.0]
            if low_scores:
                low_dims = [item[0] for item in low_scores]
                insights.append(f"Areas of concern: {', '.join(low_dims)}")
        
        # Overall assessment
        if overall_score >= 8.0:
            insights.append("Strong overall acquisition candidate")
        elif overall_score >= 6.0:
            insights.append("Solid acquisition potential with some considerations")
        elif overall_score >= 4.0:
            insights.append("Mixed signals, requires deeper evaluation")
        else:
            insights.append("Significant challenges identified")
        
        return insights
    
    def _generate_recommendation(
        self,
        overall_score: float,
        tier: str,
        insights: List[str]
    ) -> str:
        """Generate overall recommendation"""
        if overall_score >= 8.5:
            return f"STRONG RECOMMEND - Tier {tier}: Excellent strategic fit with high scores across multiple dimensions. Priority target for acquisition discussions."
        elif overall_score >= 7.0:
            return f"RECOMMEND - Tier {tier}: Good acquisition candidate with strong fundamentals. Proceed with due diligence."
        elif overall_score >= 5.5:
            return f"CONDITIONAL - Tier {tier}: Mixed results indicate potential but with notable concerns. Deeper analysis recommended before proceeding."
        elif overall_score >= 4.0:
            return f"CAUTION - Tier {tier}: Significant concerns identified. Consider only if strategic rationale is compelling."
        else:
            return f"NOT RECOMMENDED - Tier {tier}: Poor fit based on current criteria. Not suitable for acquisition at this time."
    
    async def score_multiple_systems(
        self,
        company_data: Dict[str, Any],
        system_ids: List[str]
    ) -> Dict[str, Any]:
        """Score company using multiple scoring systems in parallel"""
        try:
            logger.info(f"Scoring company with {len(system_ids)} systems")
            
            # Create scoring tasks
            tasks = []
            for system_id in system_ids:
                task = self.score_company(company_data, system_id)
                tasks.append((system_id, task))
            
            # Execute in parallel
            results = {}
            for system_id, task in tasks:
                try:
                    result = await task
                    results[system_id] = result
                except Exception as e:
                    logger.error(f"Error scoring with system {system_id}: {e}")
                    results[system_id] = {
                        "success": False,
                        "error": str(e)
                    }
            
            # Calculate summary statistics
            successful_results = [r for r in results.values() if r.get("success")]
            
            summary = {
                "systems_requested": len(system_ids),
                "systems_successful": len(successful_results),
                "average_score": 0.0,
                "score_range": {"min": 0.0, "max": 0.0},
                "consensus_tier": "LOW"
            }
            
            if successful_results:
                scores = [r["overall_score"] for r in successful_results]
                summary["average_score"] = sum(scores) / len(scores)
                summary["score_range"] = {"min": min(scores), "max": max(scores)}
                
                # Determine consensus tier
                tiers = [r["tier"] for r in successful_results]
                tier_counts = {tier: tiers.count(tier) for tier in set(tiers)}
                summary["consensus_tier"] = max(tier_counts.items(), key=lambda x: x[1])[0]
            
            return {
                "success": True,
                "results": results,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error in multi-system scoring: {e}")
            return {
                "success": False,
                "error": str(e)
            }