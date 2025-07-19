"""
Core analysis tools for M&A Research Assistant
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import AnalysisMetadata, AnalysisResult
from ..services import S3Service, BedrockLLMService, WebScrapingService, ApifyService
from ..utils import ScoringEngine, LeadQualificationEngine

logger = logging.getLogger(__name__)

# Initialize services
s3_service = S3Service()
llm_service = BedrockLLMService()
web_scraper = WebScrapingService()
apify_service = ApifyService()
scoring_engine = ScoringEngine()
qualification_engine = LeadQualificationEngine()


async def analyze_company(
    company_name: str,
    website_url: str,
    linkedin_url: str = "",
    force_refresh: bool = False,
    skip_filtering: bool = False,
    manual_override: bool = False
) -> Dict[str, Any]:
    """Orchestrates complete company analysis with scoring and qualification"""
    analysis_start_time = time.time()
    
    try:
        logger.info(f"Starting analysis for company: {company_name}")
        
        # Generate analysis ID and timestamp
        analysis_timestamp = datetime.utcnow().isoformat() + 'Z'
        analysis_id = f"{company_name.lower().replace(' ', '-')}_{int(time.time())}"
        
        # Check for existing analysis if not forcing refresh
        if not force_refresh:
            existing_analysis = await s3_service.get_analysis_result(company_name)
            if existing_analysis:
                logger.info(f"Found existing analysis for {company_name}")
                return {
                    "success": True,
                    "is_qualified": existing_analysis.qualification_result.is_qualified,
                    "filtering_result": existing_analysis.filtering_result.dict(),
                    "s3_path": f"s3://{s3_service.bucket_name}/companies/{s3_service._sanitize_company_name(company_name)}/latest",
                    "analysis_summary": {
                        "overall_score": existing_analysis.overall_score,
                        "automated_tier": existing_analysis.automated_tier,
                        "recommendation": existing_analysis.recommendation
                    },
                    "from_cache": True
                }
        
        # Step 1: Scrape website
        logger.info(f"Scraping website: {website_url}")
        website_data = await scrape_website(website_url, max_pages=5)
        
        if not website_data["success"]:
            logger.warning(f"Website scraping failed: {website_data.get('error', 'Unknown error')}")
            website_data = {"success": False, "error": "Website scraping failed"}
        
        # Step 2: Get LinkedIn data if provided
        linkedin_data = None
        if linkedin_url:
            logger.info(f"Getting LinkedIn data: {linkedin_url}")
            linkedin_result = await get_linkedin_data(linkedin_url, force_refresh)
            if linkedin_result["success"]:
                linkedin_data = linkedin_result["company_data"]
            else:
                logger.warning(f"LinkedIn data retrieval failed: {linkedin_result.get('error', 'Unknown error')}")
        
        # Step 3: Combine all data for analysis
        combined_data = {
            "company_name": company_name,
            "website_url": website_url,
            "linkedin_url": linkedin_url,
            "website_data": website_data,
            "linkedin_data": linkedin_data,
            "analysis_timestamp": analysis_timestamp
        }
        
        # Add website content to combined data for scoring
        if website_data.get("success") and "scraped_pages" in website_data:
            for page in website_data["scraped_pages"]:
                for key, value in page.items():
                    if key not in combined_data:
                        combined_data[key] = value
                    elif isinstance(value, str):
                        combined_data[key] = f"{combined_data.get(key, '')} {value}"
        
        # Add LinkedIn data to combined data
        if linkedin_data:
            for key, value in linkedin_data.items():
                combined_data[f"linkedin_{key}"] = value
        
        # Step 4: Lead qualification (unless skipped)
        qualification_result = None
        filtering_result = None
        
        if not skip_filtering and not manual_override:
            logger.info("Performing lead qualification")
            qualification_response = await qualify_lead(company_name, combined_data)
            
            if qualification_response["success"]:
                qualification_result = qualification_response["qualification_result"]
                filtering_result = qualification_response["filtering_result"]
                
                if not qualification_response["is_qualified"]:
                    logger.info(f"Company {company_name} did not pass qualification")
                    # Still save partial analysis
                    partial_analysis = create_partial_analysis_result(
                        company_name, analysis_timestamp, website_url, linkedin_url,
                        qualification_result, filtering_result, combined_data
                    )
                    
                    s3_path = await s3_service.save_analysis_result(
                        partial_analysis,
                        website_data if website_data["success"] else None,
                        linkedin_data
                    )
                    
                    return {
                        "success": True,
                        "is_qualified": False,
                        "filtering_result": filtering_result.dict(),
                        "s3_path": s3_path,
                        "analysis_summary": {
                            "overall_score": 0.0,
                            "automated_tier": "DISQUALIFIED",
                            "recommendation": "Does not meet qualification criteria"
                        },
                        "disqualification_reasons": qualification_result.disqualification_reasons
                    }
            else:
                logger.warning(f"Qualification failed: {qualification_response.get('error', 'Unknown error')}")
        
        # Step 5: Score company using default scoring system
        logger.info("Scoring company")
        scoring_result = await scoring_engine.score_company(combined_data)
        
        if not scoring_result["success"]:
            logger.error(f"Scoring failed: {scoring_result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": f"Scoring failed: {scoring_result.get('error', 'Unknown error')}"
            }
        
        # Step 6: Generate investment thesis
        logger.info("Generating investment thesis")
        thesis_result = await generate_investment_thesis(company_name, combined_data, scoring_result)
        investment_thesis = thesis_result.get("investment_thesis") if thesis_result.get("success") else None
        
        # Step 7: Create complete analysis result
        analysis_duration = time.time() - analysis_start_time
        
        metadata = AnalysisMetadata(
            analysis_id=analysis_id,
            created_at=analysis_timestamp,
            analysis_duration_seconds=analysis_duration,
            bedrock_tokens_used=0,  # Will be populated by actual usage
            bedrock_requests_made=0,
            apify_requests_made=1 if linkedin_data else 0,
            pages_scraped=len(website_data.get("scraped_pages", [])) if website_data.get("success") else 0,
            data_sources_used=["website"] + (["linkedin"] if linkedin_data else []),
            errors_encountered=[],
            warnings=[],
            cost_estimate_usd=0.0
        )
        
        # Create dimension scores from scoring result
        dimension_scores = {}
        if "dimension_scores" in scoring_result:
            from ..models import ScoreDimension
            for dim_id, dim_data in scoring_result["dimension_scores"].items():
                dimension_scores[dim_id] = ScoreDimension(**dim_data)
        
        analysis_result = AnalysisResult(
            company_name=company_name,
            analysis_timestamp=analysis_timestamp,
            website_url=website_url,
            linkedin_url=linkedin_url,
            list_type="active",  # Default to active list
            qualification_result=qualification_result,
            filtering_result=filtering_result,
            scoring_results={"default": scoring_result},
            default_scores=dimension_scores,
            overall_score=scoring_result.get("overall_score", 0.0),
            recommendation=scoring_result.get("recommendation", "No recommendation available"),
            key_strengths=scoring_result.get("insights", [])[:3],
            key_concerns=[],
            automated_tier=scoring_result.get("tier", "LOW"),
            manual_tier_override=None,
            override_metadata=None,
            effective_tier=scoring_result.get("tier", "LOW"),
            likelihood_factors={},  # Could be populated from additional analysis
            investment_thesis=investment_thesis,
            nurturing_plan=None,
            metadata=metadata
        )
        
        # Step 8: Save to S3
        logger.info("Saving analysis results to S3")
        s3_path = await s3_service.save_analysis_result(
            analysis_result,
            website_data if website_data["success"] else None,
            linkedin_data
        )
        
        logger.info(f"Analysis completed for {company_name} in {analysis_duration:.1f}s")
        
        return {
            "success": True,
            "is_qualified": qualification_result.is_qualified if qualification_result else True,
            "filtering_result": filtering_result.dict() if filtering_result else {},
            "s3_path": s3_path,
            "analysis_summary": {
                "overall_score": analysis_result.overall_score,
                "automated_tier": analysis_result.automated_tier,
                "recommendation": analysis_result.recommendation,
                "key_strengths": analysis_result.key_strengths,
                "analysis_duration": analysis_duration
            }
        }
        
    except Exception as e:
        logger.error(f"Error in company analysis: {e}")
        return {
            "success": False,
            "error": str(e),
            "is_qualified": False
        }


def create_partial_analysis_result(
    company_name: str,
    analysis_timestamp: str,
    website_url: str,
    linkedin_url: str,
    qualification_result,
    filtering_result,
    combined_data: Dict[str, Any]
) -> AnalysisResult:
    """Create partial analysis result for disqualified companies"""
    from ..models import AnalysisMetadata
    
    metadata = AnalysisMetadata(
        analysis_id=f"{company_name.lower().replace(' ', '-')}_{int(time.time())}",
        created_at=analysis_timestamp,
        analysis_duration_seconds=0.0,
        bedrock_tokens_used=0,
        bedrock_requests_made=0,
        apify_requests_made=1 if linkedin_url else 0,
        pages_scraped=0,
        data_sources_used=["website"] + (["linkedin"] if linkedin_url else []),
        errors_encountered=[],
        warnings=[]
    )
    
    return AnalysisResult(
        company_name=company_name,
        analysis_timestamp=analysis_timestamp,
        website_url=website_url,
        linkedin_url=linkedin_url,
        list_type="future_candidate",
        qualification_result=qualification_result,
        filtering_result=filtering_result,
        scoring_results={},
        default_scores={},
        overall_score=0.0,
        recommendation="Disqualified during initial screening",
        key_strengths=[],
        key_concerns=qualification_result.disqualification_reasons,
        automated_tier="DISQUALIFIED",
        manual_tier_override=None,
        override_metadata=None,
        effective_tier="DISQUALIFIED",
        likelihood_factors={},
        investment_thesis=None,
        nurturing_plan=None,
        metadata=metadata
    )


async def scrape_website(
    website_url: str,
    max_pages: int = 5,
    priority_keywords: List[str] = None
) -> Dict[str, Any]:
    """Intelligent website scraping with priority keyword targeting"""
    try:
        logger.info(f"Scraping website: {website_url}")
        
        result = await web_scraper.scrape_website(
            website_url=website_url,
            max_pages=max_pages,
            priority_keywords=priority_keywords or []
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error scraping website {website_url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "website_url": website_url
        }


async def get_linkedin_data(
    linkedin_url: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """Fetches LinkedIn company data via Apify API"""
    try:
        logger.info(f"Getting LinkedIn data: {linkedin_url}")
        
        result = await apify_service.get_linkedin_company_data(
            linkedin_url=linkedin_url,
            force_refresh=force_refresh
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn data for {linkedin_url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "linkedin_url": linkedin_url
        }


async def score_dimension(
    dimension_name: str,
    company_data: Dict[str, Any],
    scoring_system_id: str = "default"
) -> Dict[str, Any]:
    """Generic scoring function for any dimension"""
    try:
        logger.info(f"Scoring dimension: {dimension_name}")
        
        # Get scoring system
        if scoring_system_id == "default":
            scoring_system = scoring_engine.default_system
        else:
            scoring_system = await s3_service.get_scoring_system(scoring_system_id)
            if not scoring_system:
                return {
                    "success": False,
                    "error": f"Scoring system {scoring_system_id} not found"
                }
        
        # Find the dimension
        dimension = None
        for dim in scoring_system.dimensions:
            if dim.dimension_name.lower() == dimension_name.lower() or dim.dimension_id == dimension_name:
                dimension = dim
                break
        
        if not dimension:
            return {
                "success": False,
                "error": f"Dimension {dimension_name} not found in scoring system {scoring_system_id}"
            }
        
        # Score the dimension
        result = await scoring_engine._score_dimension(dimension, company_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error scoring dimension {dimension_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def enrich_company_data(
    company_name: str,
    base_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Enhance company data from additional sources"""
    try:
        logger.info(f"Enriching data for company: {company_name}")
        
        enriched_data = base_data.copy()
        enrichment_sources = []
        
        # TODO: Add additional data source integrations here
        # For now, return the base data with metadata about enrichment
        
        return {
            "success": True,
            "company_name": company_name,
            "enriched_data": enriched_data,
            "enrichment_sources": enrichment_sources,
            "enrichment_timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error enriching data for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "company_name": company_name
        }


async def get_company_history(
    company_name: str,
    limit: int = 10
) -> Dict[str, Any]:
    """Retrieves historical analyses for a company"""
    try:
        logger.info(f"Getting history for company: {company_name}")
        
        history = await s3_service.get_company_history(company_name, limit)
        
        return {
            "success": True,
            "company_name": company_name,
            "history_count": len(history),
            "history": history
        }
        
    except Exception as e:
        logger.error(f"Error getting history for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "company_name": company_name
        }


async def compare_analyses(
    company_name: str,
    analysis1_timestamp: str,
    analysis2_timestamp: str
) -> Dict[str, Any]:
    """Compares two analyses of the same company"""
    try:
        logger.info(f"Comparing analyses for {company_name}: {analysis1_timestamp} vs {analysis2_timestamp}")
        
        # Get both analyses
        analysis1 = await s3_service.get_analysis_result(company_name, analysis1_timestamp)
        analysis2 = await s3_service.get_analysis_result(company_name, analysis2_timestamp)
        
        if not analysis1:
            return {
                "success": False,
                "error": f"Analysis not found for timestamp {analysis1_timestamp}"
            }
        
        if not analysis2:
            return {
                "success": False,
                "error": f"Analysis not found for timestamp {analysis2_timestamp}"
            }
        
        # Compare key metrics
        comparison = {
            "company_name": company_name,
            "analysis1_timestamp": analysis1_timestamp,
            "analysis2_timestamp": analysis2_timestamp,
            "score_change": analysis2.overall_score - analysis1.overall_score,
            "tier_change": {
                "from": analysis1.automated_tier,
                "to": analysis2.automated_tier,
                "changed": analysis1.automated_tier != analysis2.automated_tier
            },
            "qualification_change": {
                "from": analysis1.qualification_result.is_qualified,
                "to": analysis2.qualification_result.is_qualified,
                "changed": analysis1.qualification_result.is_qualified != analysis2.qualification_result.is_qualified
            },
            "dimension_changes": {},
            "key_differences": []
        }
        
        # Compare dimension scores
        for dim_id in analysis1.default_scores:
            if dim_id in analysis2.default_scores:
                score_diff = analysis2.default_scores[dim_id].score - analysis1.default_scores[dim_id].score
                comparison["dimension_changes"][dim_id] = {
                    "score_change": score_diff,
                    "from": analysis1.default_scores[dim_id].score,
                    "to": analysis2.default_scores[dim_id].score
                }
                
                if abs(score_diff) > 1.0:
                    comparison["key_differences"].append(
                        f"{dim_id}: {score_diff:+.1f} points"
                    )
        
        # Add summary
        if comparison["score_change"] > 1.0:
            comparison["summary"] = f"Overall improvement of {comparison['score_change']:+.1f} points"
        elif comparison["score_change"] < -1.0:
            comparison["summary"] = f"Overall decline of {comparison['score_change']:.1f} points"
        else:
            comparison["summary"] = "Minimal change in overall score"
        
        return {
            "success": True,
            "comparison": comparison
        }
        
    except Exception as e:
        logger.error(f"Error comparing analyses for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def bulk_analyze(
    companies: List[Dict[str, str]],
    max_parallel: int = 3
) -> Dict[str, Any]:
    """Parallel analysis of multiple companies"""
    try:
        logger.info(f"Starting bulk analysis of {len(companies)} companies")
        
        # Limit parallelism
        max_parallel = min(max_parallel, 5)  # Safety limit
        
        results = []
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def analyze_single_company(company_info: Dict[str, str]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result = await analyze_company(
                        company_name=company_info["company_name"],
                        website_url=company_info["website_url"],
                        linkedin_url=company_info.get("linkedin_url", ""),
                        force_refresh=company_info.get("force_refresh", False)
                    )
                    result["company_name"] = company_info["company_name"]
                    return result
                except Exception as e:
                    logger.error(f"Error analyzing {company_info.get('company_name', 'Unknown')}: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "company_name": company_info.get("company_name", "Unknown")
                    }
        
        # Execute analyses in parallel
        tasks = [analyze_single_company(company) for company in companies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_analyses = []
        failed_analyses = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_analyses.append({
                    "error": str(result),
                    "company_name": "Unknown"
                })
            elif result.get("success"):
                successful_analyses.append(result)
            else:
                failed_analyses.append(result)
        
        # Generate summary
        qualified_companies = [r for r in successful_analyses if r.get("is_qualified")]
        
        summary = {
            "total_requested": len(companies),
            "successful_analyses": len(successful_analyses),
            "failed_analyses": len(failed_analyses),
            "qualified_companies": len(qualified_companies),
            "qualification_rate": len(qualified_companies) / len(successful_analyses) if successful_analyses else 0.0
        }
        
        if qualified_companies:
            scores = [r["analysis_summary"]["overall_score"] for r in qualified_companies]
            summary["average_score"] = sum(scores) / len(scores)
            summary["top_company"] = max(qualified_companies, key=lambda x: x["analysis_summary"]["overall_score"])["company_name"]
        
        return {
            "success": True,
            "summary": summary,
            "successful_analyses": successful_analyses,
            "failed_analyses": failed_analyses
        }
        
    except Exception as e:
        logger.error(f"Error in bulk analysis: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def bulk_filter(
    companies: List[str],
    criteria: Dict[str, Any]
) -> Dict[str, Any]:
    """Filter multiple companies against qualification criteria"""
    try:
        logger.info(f"Filtering {len(companies)} companies against criteria")
        
        filtered_results = []
        
        for company_name in companies:
            try:
                # Get latest analysis
                analysis = await s3_service.get_analysis_result(company_name)
                
                if not analysis:
                    filtered_results.append({
                        "company_name": company_name,
                        "matches_criteria": False,
                        "reason": "No analysis found"
                    })
                    continue
                
                # Check criteria
                matches = True
                reasons = []
                
                # Check score criteria
                if "min_score" in criteria:
                    if analysis.overall_score < criteria["min_score"]:
                        matches = False
                        reasons.append(f"Score {analysis.overall_score} < {criteria['min_score']}")
                
                if "max_score" in criteria:
                    if analysis.overall_score > criteria["max_score"]:
                        matches = False
                        reasons.append(f"Score {analysis.overall_score} > {criteria['max_score']}")
                
                # Check tier criteria
                if "tier" in criteria:
                    if analysis.effective_tier != criteria["tier"]:
                        matches = False
                        reasons.append(f"Tier {analysis.effective_tier} != {criteria['tier']}")
                
                # Check qualification criteria
                if "qualified" in criteria:
                    if analysis.qualification_result.is_qualified != criteria["qualified"]:
                        matches = False
                        reasons.append(f"Qualified {analysis.qualification_result.is_qualified} != {criteria['qualified']}")
                
                filtered_results.append({
                    "company_name": company_name,
                    "matches_criteria": matches,
                    "overall_score": analysis.overall_score,
                    "tier": analysis.effective_tier,
                    "qualified": analysis.qualification_result.is_qualified,
                    "reasons": reasons if not matches else []
                })
                
            except Exception as e:
                logger.error(f"Error filtering company {company_name}: {e}")
                filtered_results.append({
                    "company_name": company_name,
                    "matches_criteria": False,
                    "reason": f"Error: {str(e)}"
                })
        
        # Generate summary
        matching_companies = [r for r in filtered_results if r["matches_criteria"]]
        
        return {
            "success": True,
            "criteria": criteria,
            "total_companies": len(companies),
            "matching_companies": len(matching_companies),
            "match_rate": len(matching_companies) / len(companies) if companies else 0.0,
            "results": filtered_results
        }
        
    except Exception as e:
        logger.error(f"Error in bulk filtering: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def run_custom_scoring(
    company_name: str,
    scoring_system_ids: List[str]
) -> Dict[str, Any]:
    """Run specific scoring systems on a company"""
    try:
        logger.info(f"Running custom scoring for {company_name} with systems: {scoring_system_ids}")
        
        # Get company data
        analysis = await s3_service.get_analysis_result(company_name)
        if not analysis:
            return {
                "success": False,
                "error": f"No analysis found for company {company_name}"
            }
        
        # Reconstruct company data for scoring
        # This is a simplified approach - in production you'd want to store raw data
        company_data = {
            "company_name": company_name,
            "website_url": analysis.website_url,
            "linkedin_url": analysis.linkedin_url,
            "analysis_timestamp": analysis.analysis_timestamp
        }
        
        # Run scoring with multiple systems
        result = await scoring_engine.score_multiple_systems(
            company_data=company_data,
            system_ids=scoring_system_ids
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error running custom scoring for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def search_companies(
    criteria: Dict[str, Any],
    sort_by: str = "overall_score",
    limit: int = 50
) -> Dict[str, Any]:
    """Search analyzed companies by various criteria"""
    try:
        logger.info(f"Searching companies with criteria: {criteria}")
        
        results = await s3_service.search_companies(criteria, sort_by, limit)
        
        return {
            "success": True,
            "criteria": criteria,
            "sort_by": sort_by,
            "limit": limit,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def qualify_lead(
    company_name: str,
    company_data: Optional[Dict[str, Any]] = None,
    force_requalification: bool = False
) -> Dict[str, Any]:
    """Complete multi-tier lead qualification"""
    try:
        logger.info(f"Qualifying lead: {company_name}")
        
        # If no company data provided, try to get from existing analysis
        if not company_data:
            analysis = await s3_service.get_analysis_result(company_name)
            if not analysis:
                return {
                    "success": False,
                    "error": f"No company data available for {company_name}"
                }
            
            # Use data from existing analysis
            company_data = {
                "company_name": company_name,
                "website_url": analysis.website_url,
                "linkedin_url": analysis.linkedin_url
            }
        
        # Perform qualification
        result = await qualification_engine.qualify_lead(
            company_data=company_data,
            force_requalification=force_requalification
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error qualifying lead {company_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "is_qualified": False
        }


async def generate_investment_thesis(
    company_name: str,
    company_data: Optional[Dict[str, Any]] = None,
    analysis_results: Optional[Dict[str, Any]] = None,
    thesis_type: str = "standard"
) -> Dict[str, Any]:
    """AI-powered investment thesis generation"""
    try:
        logger.info(f"Generating investment thesis for {company_name}")
        
        # Get company and analysis data if not provided
        if not company_data or not analysis_results:
            analysis = await s3_service.get_analysis_result(company_name)
            if not analysis:
                return {
                    "success": False,
                    "error": f"No analysis data available for {company_name}"
                }
            
            if not company_data:
                company_data = {
                    "company_name": company_name,
                    "website_url": analysis.website_url,
                    "linkedin_url": analysis.linkedin_url,
                    "overall_score": analysis.overall_score,
                    "tier": analysis.effective_tier
                }
            
            if not analysis_results:
                analysis_results = {
                    "overall_score": analysis.overall_score,
                    "dimension_scores": {k: v.dict() for k, v in analysis.default_scores.items()},
                    "tier": analysis.effective_tier,
                    "qualification_result": analysis.qualification_result.dict()
                }
        
        # Generate thesis using LLM
        result = await llm_service.generate_investment_thesis(
            company_data=company_data,
            analysis_results=analysis_results,
            thesis_type=thesis_type
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating investment thesis for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def manage_lead_nurturing(
    company_name: str,
    action: str,
    tier: str = None,
    notes: str = ""
) -> Dict[str, Any]:
    """Update lead tier and nurturing activities"""
    try:
        logger.info(f"Managing lead nurturing for {company_name}: {action}")
        
        # TODO: Implement nurturing management logic
        # This would typically update company list status, tier overrides, etc.
        
        return {
            "success": True,
            "company_name": company_name,
            "action": action,
            "tier": tier,
            "notes": notes,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error managing lead nurturing for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }