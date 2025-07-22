"""
Enhanced research tools for comprehensive company analysis
"""

import logging
from typing import Any, Dict, List, Optional

from ..services.discovery.comprehensive_research_service import ComprehensiveResearchService
from ..services.discovery.google_search_service import GoogleSearchService
from ..services.discovery.public_filings_service import PublicFilingsService
from ..services.discovery.news_discovery_service import NewsDiscoveryService

logger = logging.getLogger(__name__)

# Initialize services
comprehensive_research_service = ComprehensiveResearchService()


async def conduct_comprehensive_research(
    company_name: str,
    website_url: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    research_depth: str = "standard",
    include_public_filings: bool = True,
    include_news_coverage: bool = True,
    include_location_extraction: bool = True,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Conduct comprehensive research on a company using multiple data sources
    
    Args:
        company_name: Name of the company to research
        website_url: Optional company website URL
        linkedin_url: Optional LinkedIn company page URL
        research_depth: Research depth - "basic", "standard", or "deep"
        include_public_filings: Whether to search for SEC and state filings
        include_news_coverage: Whether to search for news and media coverage
        include_location_extraction: Whether to extract location information
        timeout: Maximum time in seconds for research
    
    Returns:
        Comprehensive research results with aggregated insights
    """
    
    try:
        logger.info(f"Starting comprehensive research for {company_name} with depth: {research_depth}")
        
        # Conduct comprehensive research
        research_results = await comprehensive_research_service.conduct_comprehensive_research(
            company_name=company_name,
            website_url=website_url,
            linkedin_url=linkedin_url,
            research_depth=research_depth,
            timeout=timeout
        )
        
        # Filter results based on user preferences
        if not include_public_filings:
            research_results.pop('public_filings', None)
        
        if not include_news_coverage:
            research_results.pop('news_coverage', None)
        
        if not include_location_extraction:
            research_results.pop('location_info', None)
        
        # Add summary metrics
        research_summary = _generate_research_summary(research_results)
        research_results['research_summary'] = research_summary
        
        logger.info(f"Completed comprehensive research for {company_name}")
        
        return {
            "success": True,
            "company_name": company_name,
            "research_results": research_results,
            "research_depth": research_depth,
            "total_data_points": research_results.get('research_metadata', {}).get('total_data_points', 0),
            "confidence_score": research_results.get('research_metadata', {}).get('confidence_score', 0.0)
        }
        
    except Exception as e:
        logger.error(f"Comprehensive research failed for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "company_name": company_name
        }


async def search_company_web_presence(
    company_name: str,
    include_filings: bool = False,
    include_news: bool = False,
    include_reviews: bool = True,
    max_results: int = 15
) -> Dict[str, Any]:
    """
    Search for general company web presence and information
    
    Args:
        company_name: Name of the company to search for
        include_filings: Whether to include public filing results
        include_news: Whether to include news results
        include_reviews: Whether to include review and mention results
        max_results: Maximum number of results to return
    
    Returns:
        Web search results categorized by type
    """
    
    try:
        logger.info(f"Searching web presence for {company_name}")
        
        async with GoogleSearchService() as google_service:
            search_results = await google_service.search_company_information(
                company_name=company_name,
                include_filings=include_filings,
                include_news=include_news,
                include_reviews=include_reviews,
                max_results=max_results
            )
        
        # Calculate summary metrics
        total_results = sum(len(results) for results in search_results.values())
        
        return {
            "success": True,
            "company_name": company_name,
            "search_results": search_results,
            "total_results": total_results,
            "categories_found": len([k for k, v in search_results.items() if v])
        }
        
    except Exception as e:
        logger.error(f"Web presence search failed for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "company_name": company_name
        }


async def search_public_filings(
    company_name: str,
    include_sec: bool = True,
    include_state: bool = True,
    max_results_per_source: int = 10
) -> Dict[str, Any]:
    """
    Search for public filings and business registrations
    
    Args:
        company_name: Name of the company to search for
        include_sec: Whether to search SEC EDGAR database
        include_state: Whether to search state business registrations
        max_results_per_source: Maximum results per filing source
    
    Returns:
        Public filing search results
    """
    
    try:
        logger.info(f"Searching public filings for {company_name}")
        
        async with PublicFilingsService() as filings_service:
            filing_results = await filings_service.discover_public_filings(
                company_name=company_name,
                include_sec=include_sec,
                include_state=include_state,
                max_results_per_source=max_results_per_source
            )
        
        # Calculate summary metrics
        total_filings = sum(len(filings) for filings in filing_results.values())
        
        return {
            "success": True,
            "company_name": company_name,
            "filing_results": filing_results,
            "total_filings": total_filings,
            "sources_with_results": len([k for k, v in filing_results.items() if v])
        }
        
    except Exception as e:
        logger.error(f"Public filings search failed for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "company_name": company_name
        }


async def search_news_coverage(
    company_name: str,
    time_range: str = "1y",
    include_press_releases: bool = True,
    include_mentions: bool = True,
    max_results: int = 20
) -> Dict[str, Any]:
    """
    Search for news and media coverage about a company
    
    Args:
        company_name: Name of the company to search for
        time_range: Time range for news search ("1w", "1m", "3m", "6m", "1y")
        include_press_releases: Whether to include press release search
        include_mentions: Whether to include general company mentions
        max_results: Maximum number of news articles to return
    
    Returns:
        News and media coverage results
    """
    
    try:
        logger.info(f"Searching news coverage for {company_name}")
        
        async with NewsDiscoveryService() as news_service:
            coverage_results = await news_service.discover_news_coverage(
                company_name=company_name,
                time_range=time_range,
                include_press_releases=include_press_releases,
                include_mentions=include_mentions,
                max_results=max_results
            )
        
        # Calculate sentiment analysis
        all_articles = []
        for articles in coverage_results.values():
            all_articles.extend(articles)
        
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        for article in all_articles:
            sentiment = getattr(article, 'sentiment', 'neutral')
            sentiment_counts[sentiment] += 1
        
        return {
            "success": True,
            "company_name": company_name,
            "coverage_results": coverage_results,
            "total_articles": len(all_articles),
            "sentiment_analysis": sentiment_counts,
            "time_range": time_range
        }
        
    except Exception as e:
        logger.error(f"News coverage search failed for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "company_name": company_name
        }


def _generate_research_summary(research_results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a summary of research results"""
    
    summary = {
        'company_profile': {
            'has_website': False,
            'has_linkedin': False,
            'has_location': False,
            'web_presence_score': 0.0
        },
        'data_sources': {
            'sources_attempted': 0,
            'sources_successful': 0,
            'success_rate': 0.0
        },
        'content_discovered': {
            'web_results': 0,
            'news_articles': 0,
            'public_filings': 0,
            'location_mentions': 0
        },
        'key_insights': []
    }
    
    try:
        # Basic discovery info
        basic_discovery = research_results.get('basic_discovery', {})
        summary['company_profile']['has_website'] = bool(basic_discovery.get('website_url'))
        summary['company_profile']['has_linkedin'] = bool(basic_discovery.get('linkedin_url'))
        
        # Location info
        location_info = research_results.get('location_info', {})
        summary['company_profile']['has_location'] = bool(location_info.get('primary_location'))
        
        # Web presence
        aggregated_insights = research_results.get('aggregated_insights', {})
        company_profile = aggregated_insights.get('company_profile', {})
        summary['company_profile']['web_presence_score'] = company_profile.get('web_presence_score', 0.0)
        
        # Data sources
        metadata = research_results.get('research_metadata', {})
        summary['data_sources']['sources_attempted'] = len(metadata.get('sources_attempted', []))
        summary['data_sources']['sources_successful'] = len(metadata.get('sources_successful', []))
        if summary['data_sources']['sources_attempted'] > 0:
            summary['data_sources']['success_rate'] = (
                summary['data_sources']['sources_successful'] / 
                summary['data_sources']['sources_attempted']
            )
        
        # Content discovered
        web_research = research_results.get('web_research', {})
        summary['content_discovered']['web_results'] = web_research.get('total_results', 0)
        
        news_coverage = research_results.get('news_coverage', {})
        summary['content_discovered']['news_articles'] = news_coverage.get('total_articles', 0)
        
        public_filings = research_results.get('public_filings', {})
        summary['content_discovered']['public_filings'] = public_filings.get('total_filings', 0)
        
        summary['content_discovered']['location_mentions'] = len(location_info.get('additional_locations', []))
        
        # Key insights
        if summary['company_profile']['web_presence_score'] > 0.7:
            summary['key_insights'].append("Strong web presence detected")
        elif summary['company_profile']['web_presence_score'] < 0.3:
            summary['key_insights'].append("Limited web presence")
        
        if summary['content_discovered']['news_articles'] > 5:
            summary['key_insights'].append("Active media coverage")
        elif summary['content_discovered']['news_articles'] == 0:
            summary['key_insights'].append("No recent news coverage found")
        
        if summary['content_discovered']['public_filings'] > 0:
            summary['key_insights'].append("Public filing records found")
        
        if summary['data_sources']['success_rate'] < 0.5:
            summary['key_insights'].append("Limited data availability")
        
        # Sentiment insights from news
        sentiment_analysis = news_coverage.get('sentiment_analysis', {})
        if sentiment_analysis:
            positive = sentiment_analysis.get('positive', 0)
            negative = sentiment_analysis.get('negative', 0)
            if positive > negative and positive > 0:
                summary['key_insights'].append("Positive media sentiment")
            elif negative > positive and negative > 0:
                summary['key_insights'].append("Negative media sentiment")
        
    except Exception as e:
        logger.warning(f"Failed to generate research summary: {e}")
        summary['generation_error'] = str(e)
    
    return summary