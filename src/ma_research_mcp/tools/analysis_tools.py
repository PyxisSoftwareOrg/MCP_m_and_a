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
from ..services.discovery.comprehensive_research_service import ComprehensiveResearchService
from ..services.discovery.google_search_service import GoogleSearchService
from ..utils import ScoringEngine, LeadQualificationEngine
from .discovery_tools import discover_company_sources

logger = logging.getLogger(__name__)

# Initialize services
s3_service = S3Service()
llm_service = BedrockLLMService()
web_scraper = WebScrapingService()
apify_service = ApifyService()
comprehensive_research_service = ComprehensiveResearchService()
scoring_engine = ScoringEngine()
qualification_engine = LeadQualificationEngine()


def _create_fallback_scoring_result(combined_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create fallback scoring when LLM scoring fails"""
    from ..models.scoring import DEFAULT_SCORING_DIMENSIONS
    
    # Simple rule-based scoring
    dimension_scores = {}
    total_score = 0
    total_weight = 0
    
    for dim in DEFAULT_SCORING_DIMENSIONS:
        dim_id = dim["dimension_id"]
        max_score = dim.get("max_score", 10.0)
        min_score = dim.get("min_score", 0.0)
        weight = dim.get("weight", 1.0)
        
        # Simple heuristic scoring
        score = min_score + (max_score - min_score) * 0.5  # Default to middle
        
        dimension_scores[dim_id] = {
            "dimension_name": dim["dimension_name"],
            "score": score,
            "weight": weight,
            "weighted_score": score * weight,
            "reasoning": "Fallback scoring due to LLM timeout/failure",
            "evidence": ["Limited data available"],
            "confidence": 0.3
        }
        
        total_score += score * weight
        total_weight += weight
    
    overall_score = total_score / total_weight if total_weight > 0 else 5.0
    
    return {
        "success": True,
        "overall_score": overall_score,
        "dimension_scores": dimension_scores,
        "recommendation": "Requires manual review - automated scoring unavailable",
        "tier": "NEEDS_REVIEW",
        "insights": ["Automated scoring failed, using fallback values"],
        "scoring_system": "fallback",
        "total_possible_score": 10.0,
        "score_interpretation": {"fallback": True}
    }


def _enhance_data_for_qualification(combined_data: Dict[str, Any], comprehensive_research: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Enhance combined_data with proper field mapping for qualification engine"""
    
    # Extract location information and map to expected fields
    location_info = combined_data.get('location_info', {})
    if isinstance(location_info, dict):
        # Map primary location
        primary_location = location_info.get('primary_location', {})
        if primary_location:
            combined_data['headquarters'] = primary_location.get('address', '')
            combined_data['headquarters_location'] = primary_location.get('address', '')
        
        # Map additional locations
        additional_locations = location_info.get('additional_locations', [])
        if additional_locations:
            all_locations = []
            for loc in additional_locations:
                if isinstance(loc, dict) and 'address' in loc:
                    all_locations.append(loc['address'])
                elif isinstance(loc, str):
                    all_locations.append(loc)
            combined_data['location'] = '; '.join(all_locations)
        
        # Map addresses from location_info
        addresses = location_info.get('addresses', [])
        if addresses:
            address_list = []
            for addr in addresses:
                if isinstance(addr, dict) and 'full_address' in addr:
                    address_list.append(addr['full_address'])
                elif isinstance(addr, str):
                    address_list.append(addr)
            combined_data['address'] = '; '.join(address_list)
    
    # Extract location from comprehensive research if available
    if comprehensive_research:
        location_research = comprehensive_research.get('location_info', {})
        if location_research.get('primary_location'):
            primary = location_research['primary_location']
            if not combined_data.get('headquarters'):
                combined_data['headquarters'] = primary.get('address', '')
            if not combined_data.get('location'):
                combined_data['location'] = primary.get('address', '')
    
    # Extract and map contact information
    contact_info = combined_data.get('contact_info', {})
    if isinstance(contact_info, dict):
        # Map addresses from contact info
        for key, value in contact_info.items():
            if 'address' in key.lower() and value:
                if not combined_data.get('address'):
                    combined_data['address'] = str(value)
                else:
                    combined_data['address'] += f"; {value}"
    
    # Extract company information and enhance business model fields
    company_info = combined_data.get('company_info', {})
    if isinstance(company_info, dict):
        # Map industry mentions
        industry_mentions = company_info.get('industry_mentions', [])
        if industry_mentions:
            combined_data['industry'] = ', '.join(industry_mentions)
            combined_data['industry_vertical'] = industry_mentions[0] if industry_mentions else ''
        
        # Map employee count
        employee_mentions = company_info.get('employee_count_mentions', [])
        if employee_mentions:
            try:
                # Extract numeric values and use the largest
                employee_counts = [int(emp) for emp in employee_mentions if str(emp).isdigit()]
                if employee_counts:
                    combined_data['employee_count'] = max(employee_counts)
                    combined_data['employees'] = str(max(employee_counts))
            except (ValueError, TypeError):
                pass
        
        # Map founding year
        founding_mentions = company_info.get('founding_year_mentions', [])
        if founding_mentions:
            try:
                years = [int(year) for year in founding_mentions if str(year).isdigit() and 1800 <= int(year) <= 2024]
                if years:
                    combined_data['founding_year'] = min(years)  # Use earliest year
            except (ValueError, TypeError):
                pass
    
    # Extract product/solution information
    product_info = combined_data.get('product_info', [])
    if isinstance(product_info, list) and product_info:
        products = []
        solutions = []
        for product in product_info:
            if isinstance(product, dict):
                title = product.get('title', '')
                description = product.get('description', '')
                if title:
                    products.append(title)
                if description:
                    solutions.append(description)
        
        if products:
            combined_data['products'] = '; '.join(products)
        if solutions:
            combined_data['solutions'] = '; '.join(solutions)
    
    # Extract pricing information for revenue estimation
    pricing_info = combined_data.get('pricing_info', [])
    if isinstance(pricing_info, list) and pricing_info:
        pricing_amounts = []
        for price_item in pricing_info:
            if isinstance(price_item, dict) and 'amount' in price_item:
                amount = price_item['amount']
                # Clean and extract numeric value
                import re
                numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d{2})?', str(amount))
                if numbers:
                    try:
                        # Remove commas and convert to float
                        price = float(numbers[0].replace(',', ''))
                        pricing_amounts.append(price)
                    except ValueError:
                        pass
        
        if pricing_amounts:
            # Use highest pricing as revenue indicator
            combined_data['estimated_revenue'] = max(pricing_amounts)
    
    # Enhance text content for better business model detection
    text_sources = []
    
    # Collect text from various sources
    for field in ['text_content', 'description', 'title']:
        if combined_data.get(field):
            text_sources.append(str(combined_data[field]))
    
    # Add product and company descriptions
    if isinstance(product_info, list):
        for product in product_info:
            if isinstance(product, dict) and product.get('description'):
                text_sources.append(product['description'])
    
    # Combine all text for business model analysis
    if text_sources:
        combined_data['combined_text'] = ' '.join(text_sources)
    
    # Extract from comprehensive research web data
    if comprehensive_research:
        web_research = comprehensive_research.get('web_research', {})
        if web_research.get('general_info'):
            # Extract business information from search results
            for result in web_research['general_info']:
                if hasattr(result, 'snippet') and result.snippet:
                    if 'combined_text' in combined_data:
                        combined_data['combined_text'] += f" {result.snippet}"
                    else:
                        combined_data['combined_text'] = result.snippet
    
    # Map LinkedIn data with proper field names
    linkedin_company_name = combined_data.get('linkedin_company_name')
    if linkedin_company_name and not combined_data.get('company_name'):
        combined_data['company_name'] = linkedin_company_name
    
    linkedin_description = combined_data.get('linkedin_description')
    if linkedin_description:
        if combined_data.get('description'):
            combined_data['description'] += f" {linkedin_description}"
        else:
            combined_data['description'] = linkedin_description
    
    linkedin_industry = combined_data.get('linkedin_industry')
    if linkedin_industry and not combined_data.get('industry'):
        combined_data['industry'] = linkedin_industry
    
    linkedin_specialties = combined_data.get('linkedin_specialties')
    if linkedin_specialties:
        combined_data['specialties'] = linkedin_specialties
    
    linkedin_employee_count = combined_data.get('linkedin_employee_count')
    if linkedin_employee_count and not combined_data.get('employee_count'):
        try:
            combined_data['employee_count'] = int(linkedin_employee_count)
            combined_data['employees'] = str(linkedin_employee_count)
        except (ValueError, TypeError):
            pass
    
    linkedin_headquarters = combined_data.get('linkedin_headquarters')
    if linkedin_headquarters and not combined_data.get('headquarters'):
        combined_data['headquarters'] = linkedin_headquarters
        combined_data['headquarters_location'] = linkedin_headquarters
    
    # Ensure country/region detection from domain
    website_url = combined_data.get('website_url', '')
    if website_url:
        domain = website_url.lower()
        if '.uk' in domain or '.co.uk' in domain:
            combined_data['country'] = 'UK'
            combined_data['region'] = 'Europe'
        elif '.ca' in domain:
            combined_data['country'] = 'Canada'
            combined_data['region'] = 'North America'
        elif '.au' in domain:
            combined_data['country'] = 'Australia'
            combined_data['region'] = 'Asia Pacific'
        elif '.de' in domain:
            combined_data['country'] = 'Germany'
            combined_data['region'] = 'Europe'
        else:
            # Default to US if no other indicators
            combined_data['country'] = 'US'
            combined_data['region'] = 'North America'
    
    return combined_data


async def _search_for_missing_urls(company_name: str, website_url: Optional[str], linkedin_url: Optional[str]) -> Dict[str, Optional[str]]:
    """Search Google to find missing website or LinkedIn URLs for a company"""
    
    result = {
        'website_url': website_url,
        'linkedin_url': linkedin_url,
        'search_performed': False
    }
    
    try:
        async with GoogleSearchService() as google_service:
            # Search for website URL if missing
            if not website_url:
                logger.info(f"Searching for website URL for {company_name}")
                
                # Try multiple search strategies for better results
                search_queries = [
                    f'"{company_name}" SaaS software official website',
                    f'"{company_name}" software company',
                    f'"{company_name}" official site'
                ]
                
                for query in search_queries:
                    website_results = await google_service._perform_search(query, max_results=5)
                    
                    for search_result in website_results:
                        domain = search_result.domain.lower()
                        title = search_result.title.lower()
                        snippet = search_result.snippet.lower()
                        
                        # Skip social media, directories, and review sites
                        skip_domains = [
                            'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
                            'crunchbase.com', 'glassdoor.com', 'indeed.com', 'wikipedia.org',
                            'bloomberg.com', 'reuters.com', 'techcrunch.com', 'angel.co'
                        ]
                        
                        if any(skip in domain for skip in skip_domains):
                            continue
                        
                        # Score potential websites
                        score = 0
                        company_words = company_name.lower().split()
                        
                        # High score for company name in domain
                        if any(word in domain for word in company_words):
                            score += 5
                        
                        # Medium score for exact company name match in title/snippet
                        if company_name.lower() in title:
                            score += 3
                        if company_name.lower() in snippet:
                            score += 2
                        
                        # Bonus for SaaS/software indicators
                        saas_indicators = ['software', 'saas', 'platform', 'solution', 'app', 'cloud']
                        if any(indicator in title + ' ' + snippet for indicator in saas_indicators):
                            score += 2
                        
                        # Bonus for official site indicators
                        official_indicators = ['official', 'homepage', 'home page', 'main site']
                        if any(indicator in title + ' ' + snippet for indicator in official_indicators):
                            score += 1
                        
                        # Must have minimum score to be considered
                        if score >= 3:
                            result['website_url'] = search_result.url
                            logger.info(f"Found website URL (score: {score}): {search_result.url}")
                            break
                    
                    if result['website_url']:
                        break
            
            # Search for LinkedIn URL if missing
            if not linkedin_url:
                logger.info(f"Searching for LinkedIn URL for {company_name}")
                linkedin_query = f'"{company_name}" site:linkedin.com/company'
                linkedin_results = await google_service._perform_search(linkedin_query, max_results=3)
                
                for search_result in linkedin_results:
                    if 'linkedin.com/company' in search_result.url.lower():
                        result['linkedin_url'] = search_result.url
                        logger.info(f"Found LinkedIn URL: {search_result.url}")
                        break
            
            result['search_performed'] = True
            
    except Exception as e:
        logger.warning(f"URL search failed for {company_name}: {e}")
        result['search_error'] = str(e)
    
    return result


# System prompt for SaaS focus
SAAS_ANALYSIS_CONTEXT = """
ANALYSIS CONTEXT: This analysis is specifically focused on evaluating SaaS (Software as a Service) companies as potential M&A targets.

KEY FOCUS AREAS:
- SaaS business model characteristics (subscription revenue, cloud-based delivery)
- Software vertical market specialization
- Recurring revenue patterns and predictability
- Customer retention and churn metrics
- Market positioning within specific industries
- Technology stack and platform capabilities
- Scalability and growth potential
- Competitive advantages in software markets

When analyzing content, prioritize:
1. Software products and solutions offered
2. Target industries and customer segments
3. Pricing models (subscription, per-seat, usage-based)
4. Technology platform and infrastructure
5. Customer testimonials and case studies
6. Market positioning against competitors
7. Growth indicators and business metrics

This context should inform all scoring, qualification, and analysis decisions.
"""


async def analyze_company(
    company_name: str,
    website_url: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    auto_discover: bool = True,
    discovery_hints: Optional[Dict[str, Any]] = None,
    force_refresh: bool = False,
    skip_filtering: bool = False,
    manual_override: bool = False,
    research_depth: str = "standard",  # "basic", "standard", "deep"
    include_public_filings: bool = True,
    include_news_analysis: bool = True,
    include_location_extraction: bool = True
) -> Dict[str, Any]:
    """Orchestrates complete company analysis with scoring and qualification"""
    analysis_start_time = time.time()
    
    try:
        logger.info(f"Starting SaaS company analysis for: {company_name}")
        logger.info(f"Analysis Context: {SAAS_ANALYSIS_CONTEXT}")
        
        # Generate analysis ID and timestamp
        analysis_timestamp = datetime.utcnow().isoformat() + 'Z'
        analysis_id = f"{company_name.lower().replace(' ', '-')}_{int(time.time())}"
        
        # Step 0: Search for missing URLs using Google if not provided (temporarily disabled to avoid rate limits)
        if not website_url or not linkedin_url:
            logger.info(f"URL search temporarily disabled for {company_name} to avoid rate limits")
            # Provide some common URLs for testing
            if company_name.lower() == "whip around" and not website_url:
                website_url = "https://whiparound.com"
                logger.info(f"Using known website URL: {website_url}")
            # url_search_result = await _search_for_missing_urls(company_name, website_url, linkedin_url)
            # 
            # if url_search_result.get('website_url') and not website_url:
            #     website_url = url_search_result['website_url']
            #     logger.info(f"Found website via Google search: {website_url}")
            # 
            # if url_search_result.get('linkedin_url') and not linkedin_url:
            #     linkedin_url = url_search_result['linkedin_url']
            #     logger.info(f"Found LinkedIn via Google search: {linkedin_url}")
        
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
        
        # Step 1: Auto-discovery if enabled and URLs not provided
        discovery_data = None
        if auto_discover and (not website_url or not linkedin_url):
            logger.info(f"Starting auto-discovery for {company_name}")
            
            discovery_result = await discover_company_sources(
                company_name=company_name,
                industry_hint=discovery_hints.get("industry") if discovery_hints else None,
                location_hint=discovery_hints.get("location") if discovery_hints else None,
                company_type_hint=discovery_hints.get("type") if discovery_hints else None
            )
            
            if discovery_result["success"]:
                # Use discovered URLs if not provided
                if not website_url and discovery_result["website_url"]:
                    website_url = discovery_result["website_url"]
                    logger.info(f"Discovered website: {website_url}")
                    
                if not linkedin_url and discovery_result["linkedin_url"]:
                    linkedin_url = discovery_result["linkedin_url"]
                    logger.info(f"Discovered LinkedIn: {linkedin_url}")
                
                # Store discovery data for enrichment
                discovery_data = discovery_result
            else:
                logger.warning(f"Discovery failed: {discovery_result.get('error', 'Unknown error')}")
        
        # Step 2: Comprehensive Research (replaces separate website/LinkedIn steps)
        comprehensive_research = None
        if research_depth != "basic":
            logger.info(f"Starting comprehensive research with depth: {research_depth}")
            # Use shorter timeout for quick responses  
            timeout = 60 if research_depth == "basic" else 300
            try:
                comprehensive_research = await comprehensive_research_service.conduct_comprehensive_research(
                    company_name=company_name,
                    website_url=website_url,
                    linkedin_url=linkedin_url,
                    research_depth=research_depth,
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Comprehensive research timed out after {timeout}s, proceeding with basic analysis")
                comprehensive_research = None
            
            # Update URLs from comprehensive research if found
            if comprehensive_research.get('basic_discovery', {}).get('website_url'):
                website_url = comprehensive_research['basic_discovery']['website_url']
            if comprehensive_research.get('basic_discovery', {}).get('linkedin_url'):
                linkedin_url = comprehensive_research['basic_discovery']['linkedin_url']
        
        # Step 2b: Fallback to basic scraping if comprehensive research not used
        website_data = {"success": False, "error": "No website URL available"}
        if research_depth == "basic" and website_url:
            logger.info(f"Basic website scraping: {website_url}")
            website_data = await scrape_website(website_url, max_pages=5)
        elif comprehensive_research:
            # Extract website data from comprehensive research
            website_data = {
                "success": True,
                "website_url": website_url,
                "comprehensive_research": comprehensive_research
            }
        
        # Step 2c: Basic LinkedIn data if not in comprehensive research
        linkedin_data = None
        if research_depth == "basic" and linkedin_url:
            logger.info(f"Getting LinkedIn data: {linkedin_url}")
            linkedin_result = await get_linkedin_data(linkedin_url, force_refresh)
            if linkedin_result["success"]:
                linkedin_data = linkedin_result["company_data"]
            else:
                logger.warning(f"LinkedIn data retrieval failed: {linkedin_result.get('error', 'Unknown error')}")
        elif comprehensive_research:
            # Extract LinkedIn data from comprehensive research if available
            linkedin_data = comprehensive_research.get('basic_discovery', {}).get('linkedin_data')
        
        # Step 3: Combine all data for analysis
        combined_data = {
            "company_name": company_name,
            "website_url": website_url,
            "linkedin_url": linkedin_url,
            "website_data": website_data,
            "linkedin_data": linkedin_data,
            "analysis_timestamp": analysis_timestamp,
            "comprehensive_research": comprehensive_research,
            "discovery_data": discovery_data,
            "research_depth": research_depth
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
        
        # Enhanced data mapping for qualification engine compatibility
        combined_data = _enhance_data_for_qualification(combined_data, comprehensive_research)
        
        # Add SaaS analysis context to guide all LLM-based analysis
        combined_data['analysis_context'] = SAAS_ANALYSIS_CONTEXT
        combined_data['business_focus'] = 'SaaS Software'
        combined_data['target_market'] = 'Vertical Software Markets'
        
        # Step 4: Score company using default scoring system (always perform full analysis)
        logger.info("Scoring company")
        try:
            scoring_result = await asyncio.wait_for(
                scoring_engine.score_company(combined_data), 
                timeout=120  # 2 minutes max for scoring
            )
        except asyncio.TimeoutError:
            logger.warning("Scoring timed out, using fallback scoring")
            scoring_result = _create_fallback_scoring_result(combined_data)
        
        if not scoring_result["success"]:
            logger.warning(f"Scoring failed: {scoring_result.get('error', 'Unknown error')}, using fallback")
            scoring_result = _create_fallback_scoring_result(combined_data)
        
        # Step 5: Generate investment thesis
        logger.info("Generating investment thesis")
        try:
            thesis_result = await asyncio.wait_for(
                generate_investment_thesis(company_name, combined_data, scoring_result),
                timeout=60  # 1 minute max for thesis
            )
            investment_thesis = thesis_result.get("investment_thesis") if thesis_result.get("success") else None
        except asyncio.TimeoutError:
            logger.warning("Investment thesis generation timed out")
            investment_thesis = None
        
        # Step 6: Lead qualification (performed after analysis, used as flags)
        qualification_result = None
        filtering_result = None
        qualification_flags = []
        
        if not skip_filtering and not manual_override:
            logger.info("Performing lead qualification (as flags)")
            qualification_response = await qualify_lead(company_name, combined_data)
            
            if qualification_response["success"]:
                qualification_result = qualification_response["qualification_result"]
                filtering_result = qualification_response["filtering_result"]
                
                # Add qualification flags but don't block analysis
                if not qualification_response["is_qualified"]:
                    qualification_flags.append("Does not meet standard qualification criteria")
                    if qualification_result.disqualification_reasons:
                        qualification_flags.extend(qualification_result.disqualification_reasons)
                    logger.info(f"Company {company_name} flagged with qualification concerns: {qualification_flags}")
                else:
                    logger.info(f"Company {company_name} passed qualification checks")
            else:
                qualification_flags.append(f"Qualification assessment failed: {qualification_response.get('error', 'Unknown error')}")
                logger.warning(f"Qualification failed: {qualification_response.get('error', 'Unknown error')}")
        
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
            key_concerns=qualification_flags,
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
        
        # Extract all dimension scores for return
        all_dimension_scores = {}
        if "dimension_scores" in scoring_result:
            for dim_id, dim_data in scoring_result["dimension_scores"].items():
                all_dimension_scores[dim_id] = {
                    "dimension_name": dim_data.get("dimension_name", dim_id),
                    "score": dim_data.get("score", 0.0),
                    "weight": dim_data.get("weight", 1.0),
                    "weighted_score": dim_data.get("weighted_score", 0.0),
                    "reasoning": dim_data.get("reasoning", ""),
                    "evidence": dim_data.get("evidence", []),
                    "confidence": dim_data.get("confidence", 0.0)
                }
        
        # Combine filtering and qualification results for API response
        combined_filtering_result = filtering_result.dict() if filtering_result else {}
        if qualification_result:
            # Add Q1-Q5 assessments to the filtering result
            combined_filtering_result.update({
                "q1_horizontal_vs_vertical": qualification_result.q1_horizontal_vs_vertical,
                "q2_point_vs_suite": qualification_result.q2_point_vs_suite,
                "q3_mission_critical": qualification_result.q3_mission_critical,
                "q4_opm_vs_private": qualification_result.q4_opm_vs_private,
                "q5_arpu_level": qualification_result.q5_arpu_level,
                "qualification_score": qualification_result.qualification_score,
                "qualification_confidence": qualification_result.qualification_confidence
            })

        return {
            "success": True,
            "is_qualified": qualification_result.is_qualified if qualification_result else True,
            "qualification_flags": qualification_flags,
            "filtering_result": combined_filtering_result,
            "s3_path": s3_path,
            "analysis_summary": {
                "overall_score": analysis_result.overall_score,
                "automated_tier": analysis_result.automated_tier,
                "recommendation": analysis_result.recommendation,
                "key_strengths": analysis_result.key_strengths,
                "key_concerns": qualification_flags,
                "analysis_duration": analysis_duration
            },
            "dimension_scores": all_dimension_scores,
            "scoring_details": {
                "scoring_system_used": scoring_result.get("scoring_system", "default"),
                "total_possible_score": scoring_result.get("total_possible_score", 10.0),
                "score_interpretation": scoring_result.get("score_interpretation", {}),
                "tier_thresholds": scoring_result.get("tier_thresholds", {})
            },
            "company_data_summary": {
                "website_found": bool(website_url),
                "linkedin_found": bool(linkedin_url),
                "location_extracted": bool(combined_data.get("headquarters") or combined_data.get("location")),
                "industry_identified": bool(combined_data.get("industry")),
                "employee_count": combined_data.get("employee_count"),
                "founding_year": combined_data.get("founding_year"),
                "products_identified": bool(combined_data.get("products")),
                "pricing_found": bool(combined_data.get("pricing_info"))
            },
            "comprehensive_research": comprehensive_research if comprehensive_research else {}
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