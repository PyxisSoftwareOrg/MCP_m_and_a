"""
Comprehensive research service that aggregates data from multiple sources
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ...core.config import get_config
from ...models.discovery import (
    DiscoveryRequest, 
    DiscoveryResult,
    GoogleSearchResult,
    PublicFilingResult,
    NewsResult,
    LocationInfo
)
from .discovery_orchestrator import DiscoveryOrchestrator
from .google_search_service import GoogleSearchService
from .public_filings_service import PublicFilingsService
from .news_discovery_service import NewsDiscoveryService
from .location_extractor import LocationExtractor

logger = logging.getLogger(__name__)


class ComprehensiveResearchService:
    """Service that orchestrates comprehensive company research across multiple sources"""
    
    def __init__(self):
        self.config = get_config()
        self.discovery_orchestrator = DiscoveryOrchestrator()
        self.location_extractor = LocationExtractor()
        
    async def conduct_comprehensive_research(
        self,
        company_name: str,
        website_url: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        research_depth: str = "standard",  # "basic", "standard", "deep"
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Conduct comprehensive research on a company"""
        
        research_results = {
            'company_name': company_name,
            'research_timestamp': asyncio.get_event_loop().time(),
            'research_depth': research_depth,
            'basic_discovery': {},
            'web_research': {},
            'public_filings': {},
            'news_coverage': {},
            'location_info': {},
            'aggregated_insights': {},
            'research_metadata': {
                'sources_attempted': [],
                'sources_successful': [],
                'total_data_points': 0,
                'confidence_score': 0.0
            }
        }
        
        try:
            # Phase 1: Basic Discovery (website, LinkedIn)
            logger.info(f"Starting basic discovery for {company_name}")
            basic_discovery = await self._basic_discovery_phase(
                company_name, website_url, linkedin_url
            )
            research_results['basic_discovery'] = basic_discovery
            research_results['research_metadata']['sources_attempted'].extend(['website', 'linkedin'])
            
            if basic_discovery.get('website_url'):
                research_results['research_metadata']['sources_successful'].append('website')
            if basic_discovery.get('linkedin_url'):
                research_results['research_metadata']['sources_successful'].append('linkedin')
            
            # Phase 2: Web Research (Google search, general info)
            if research_depth in ["standard", "deep"]:
                logger.info(f"Starting web research for {company_name}")
                web_research = await self._web_research_phase(company_name)
                research_results['web_research'] = web_research
                research_results['research_metadata']['sources_attempted'].append('google_search')
                if web_research.get('search_successful'):
                    research_results['research_metadata']['sources_successful'].append('google_search')
            
            # Phase 3: Public Filings Research
            if research_depth in ["standard", "deep"]:
                logger.info(f"Starting public filings research for {company_name}")
                filings_research = await self._public_filings_phase(company_name)
                research_results['public_filings'] = filings_research
                research_results['research_metadata']['sources_attempted'].append('public_filings')
                if filings_research.get('search_successful'):
                    research_results['research_metadata']['sources_successful'].append('public_filings')
            
            # Phase 4: News and Media Coverage
            if research_depth == "deep":
                logger.info(f"Starting news research for {company_name}")
                news_research = await self._news_research_phase(company_name)
                research_results['news_coverage'] = news_research
                research_results['research_metadata']['sources_attempted'].append('news_coverage')
                if news_research.get('search_successful'):
                    research_results['research_metadata']['sources_successful'].append('news_coverage')
            
            # Phase 5: Location Information Extraction
            location_info = await self._extract_location_information(research_results)
            research_results['location_info'] = location_info
            
            # Phase 6: Data Aggregation and Insights
            aggregated_insights = await self._aggregate_insights(research_results)
            research_results['aggregated_insights'] = aggregated_insights
            
            # Calculate final metrics
            research_results['research_metadata'] = self._calculate_research_metrics(research_results)
            
            logger.info(f"Completed comprehensive research for {company_name}")
            return research_results
            
        except Exception as e:
            logger.error(f"Comprehensive research failed for {company_name}: {e}")
            research_results['error'] = str(e)
            return research_results
    
    async def _basic_discovery_phase(
        self, 
        company_name: str, 
        website_url: Optional[str], 
        linkedin_url: Optional[str]
    ) -> Dict[str, Any]:
        """Phase 1: Basic website and LinkedIn discovery"""
        
        discovery_results = {
            'website_url': website_url,
            'linkedin_url': linkedin_url,
            'discovery_attempted': False,
            'discovery_successful': False
        }
        
        # Only attempt discovery if URLs are missing
        if not website_url or not linkedin_url:
            try:
                discovery_request = DiscoveryRequest(
                    company_name=company_name,
                    discovery_timeout=30,
                    required_sources=["website", "linkedin"]
                )
                
                discovery_result = await self.discovery_orchestrator.discover_company_sources(
                    discovery_request
                )
                
                discovery_results['discovery_attempted'] = True
                
                if discovery_result.website_result and discovery_result.website_result.url:
                    discovery_results['website_url'] = discovery_result.website_result.url
                    discovery_results['website_confidence'] = discovery_result.website_result.confidence
                
                if discovery_result.linkedin_result and discovery_result.linkedin_result.url:
                    discovery_results['linkedin_url'] = discovery_result.linkedin_result.url
                    discovery_results['linkedin_confidence'] = discovery_result.linkedin_result.confidence
                
                discovery_results['discovery_successful'] = (
                    discovery_result.website_result is not None or 
                    discovery_result.linkedin_result is not None
                )
                
            except Exception as e:
                logger.warning(f"Basic discovery failed: {e}")
                discovery_results['discovery_error'] = str(e)
        
        return discovery_results
    
    async def _web_research_phase(self, company_name: str) -> Dict[str, Any]:
        """Phase 2: Google search for general company information"""
        
        web_results = {
            'general_info': [],
            'about_pages': [],
            'company_mentions': [],
            'search_attempted': False,
            'search_successful': False
        }
        
        try:
            async with GoogleSearchService() as google_service:
                search_results = await google_service.search_company_information(
                    company_name=company_name,
                    include_filings=False,  # Handle separately
                    include_news=False,     # Handle separately
                    include_reviews=True,
                    max_results=15
                )
                
                web_results['search_attempted'] = True
                web_results['general_info'] = search_results.get('general', [])
                web_results['about_pages'] = search_results.get('about', [])
                web_results['company_mentions'] = search_results.get('reviews', [])
                
                web_results['search_successful'] = len(search_results.get('general', [])) > 0
                web_results['total_results'] = sum(len(results) for results in search_results.values())
                
        except Exception as e:
            logger.warning(f"Web research failed: {e}")
            web_results['search_error'] = str(e)
        
        return web_results
    
    async def _public_filings_phase(self, company_name: str) -> Dict[str, Any]:
        """Phase 3: Public filings research"""
        
        filings_results = {
            'sec_filings': [],
            'state_filings': [],
            'other_filings': [],
            'search_attempted': False,
            'search_successful': False
        }
        
        try:
            async with PublicFilingsService() as filings_service:
                filing_results = await filings_service.discover_public_filings(
                    company_name=company_name,
                    include_sec=True,
                    include_state=True,
                    max_results_per_source=5
                )
                
                filings_results['search_attempted'] = True
                filings_results['sec_filings'] = filing_results.get('sec_filings', [])
                filings_results['state_filings'] = filing_results.get('state_filings', [])
                filings_results['other_filings'] = filing_results.get('other_filings', [])
                
                total_filings = sum(len(filings) for filings in filing_results.values())
                filings_results['search_successful'] = total_filings > 0
                filings_results['total_filings'] = total_filings
                
        except Exception as e:
            logger.warning(f"Public filings research failed: {e}")
            filings_results['search_error'] = str(e)
        
        return filings_results
    
    async def _news_research_phase(self, company_name: str) -> Dict[str, Any]:
        """Phase 4: News and media coverage research"""
        
        news_results = {
            'recent_news': [],
            'press_releases': [],
            'funding_news': [],
            'leadership_news': [],
            'search_attempted': False,
            'search_successful': False
        }
        
        try:
            async with NewsDiscoveryService() as news_service:
                coverage_results = await news_service.discover_news_coverage(
                    company_name=company_name,
                    time_range="1y",
                    include_press_releases=True,
                    include_mentions=True,
                    max_results=20
                )
                
                news_results['search_attempted'] = True
                news_results['recent_news'] = coverage_results.get('recent_news', [])
                news_results['press_releases'] = coverage_results.get('press_releases', [])
                news_results['funding_news'] = coverage_results.get('funding_news', [])
                news_results['leadership_news'] = coverage_results.get('leadership_news', [])
                
                total_news = sum(len(news) for news in coverage_results.values())
                news_results['search_successful'] = total_news > 0
                news_results['total_articles'] = total_news
                
                # Analyze sentiment distribution
                all_news = []
                for news_list in coverage_results.values():
                    all_news.extend(news_list)
                
                sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
                for article in all_news:
                    sentiment = getattr(article, 'sentiment', 'neutral')
                    sentiment_counts[sentiment] += 1
                
                news_results['sentiment_analysis'] = sentiment_counts
                
        except Exception as e:
            logger.warning(f"News research failed: {e}")
            news_results['search_error'] = str(e)
        
        return news_results
    
    async def _extract_location_information(self, research_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 5: Extract and consolidate location information"""
        
        location_info = {
            'primary_location': None,
            'additional_locations': [],
            'confidence': 0.0,
            'sources': []
        }
        
        try:
            # Check if we have website content with location data
            basic_discovery = research_results.get('basic_discovery', {})
            website_url = basic_discovery.get('website_url')
            
            if website_url:
                location_info['sources'].append('website_extraction')
                location_info['extraction_attempted'] = True
            
            # Extract location hints from news and filings
            news_coverage = research_results.get('news_coverage', {})
            if news_coverage.get('recent_news'):
                # Look for location mentions in news
                location_mentions = self._extract_location_from_news(news_coverage['recent_news'])
                if location_mentions:
                    location_info['additional_locations'].extend(location_mentions)
                    location_info['sources'].append('news_mentions')
            
            # Extract from LinkedIn data if available
            linkedin_data = basic_discovery.get('linkedin_data')
            if linkedin_data and isinstance(linkedin_data, dict):
                headquarters = linkedin_data.get('headquarters')
                if headquarters:
                    location_info['primary_location'] = {
                        'address': headquarters,
                        'source': 'linkedin',
                        'confidence': 0.8
                    }
                    location_info['sources'].append('linkedin')
            
            # Calculate overall confidence
            if location_info['primary_location'] or location_info['additional_locations']:
                location_info['confidence'] = 0.7 if location_info['primary_location'] else 0.4
                
        except Exception as e:
            logger.warning(f"Location extraction failed: {e}")
            location_info['extraction_error'] = str(e)
        
        return location_info
    
    def _extract_location_from_news(self, news_articles: List[NewsResult]) -> List[Dict[str, Any]]:
        """Extract location information from news articles"""
        locations = []
        
        # Common location patterns in news
        location_patterns = [
            r'based in ([A-Za-z\s]+)',
            r'headquartered in ([A-Za-z\s,]+)',
            r'([A-Za-z\s]+)-based company',
            r'located in ([A-Za-z\s,]+)'
        ]
        
        for article in news_articles:
            content = f"{article.title} {article.snippet}".lower()
            
            for pattern in location_patterns:
                import re
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    location = match.strip()
                    if len(location) > 2 and len(location) < 50:  # Reasonable location length
                        locations.append({
                            'location': location,
                            'source': f'news_article',
                            'confidence': 0.5,
                            'article_title': article.title
                        })
        
        return locations[:5]  # Limit to top 5
    
    async def _aggregate_insights(self, research_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 6: Aggregate insights from all research phases"""
        
        insights = {
            'company_profile': {},
            'business_indicators': {},
            'public_presence': {},
            'risk_factors': {},
            'opportunities': {},
            'data_quality': {}
        }
        
        try:
            # Company Profile
            insights['company_profile'] = {
                'has_website': bool(research_results['basic_discovery'].get('website_url')),
                'has_linkedin': bool(research_results['basic_discovery'].get('linkedin_url')),
                'has_location_info': bool(research_results['location_info'].get('primary_location')),
                'web_presence_score': self._calculate_web_presence_score(research_results)
            }
            
            # Business Indicators
            web_research = research_results.get('web_research', {})
            insights['business_indicators'] = {
                'search_result_count': web_research.get('total_results', 0),
                'about_pages_found': len(web_research.get('about_pages', [])),
                'general_mentions': len(web_research.get('general_info', []))
            }
            
            # Public Presence
            filings = research_results.get('public_filings', {})
            news = research_results.get('news_coverage', {})
            
            insights['public_presence'] = {
                'sec_filings_count': len(filings.get('sec_filings', [])),
                'state_filings_count': len(filings.get('state_filings', [])),
                'news_articles_count': news.get('total_articles', 0),
                'recent_news_count': len(news.get('recent_news', [])),
                'press_releases_count': len(news.get('press_releases', [])),
                'has_public_filings': bool(filings.get('sec_filings') or filings.get('state_filings')),
                'media_sentiment': news.get('sentiment_analysis', {})
            }
            
            # Risk Factors
            insights['risk_factors'] = {
                'low_web_presence': insights['company_profile']['web_presence_score'] < 0.3,
                'no_recent_news': len(news.get('recent_news', [])) == 0,
                'negative_sentiment': (
                    news.get('sentiment_analysis', {}).get('negative', 0) > 
                    news.get('sentiment_analysis', {}).get('positive', 0)
                )
            }
            
            # Opportunities
            insights['opportunities'] = {
                'funding_news_present': len(news.get('funding_news', [])) > 0,
                'leadership_news_present': len(news.get('leadership_news', [])) > 0,
                'recent_activity': len(news.get('recent_news', [])) > 2,
                'positive_sentiment': (
                    news.get('sentiment_analysis', {}).get('positive', 0) > 
                    news.get('sentiment_analysis', {}).get('negative', 0)
                )
            }
            
            # Data Quality Assessment
            successful_sources = research_results['research_metadata']['sources_successful']
            attempted_sources = research_results['research_metadata']['sources_attempted']
            
            insights['data_quality'] = {
                'source_success_rate': len(successful_sources) / max(len(attempted_sources), 1),
                'data_completeness_score': self._calculate_data_completeness(research_results),
                'research_confidence': self._calculate_research_confidence(research_results)
            }
            
        except Exception as e:
            logger.error(f"Insights aggregation failed: {e}")
            insights['aggregation_error'] = str(e)
        
        return insights
    
    def _calculate_web_presence_score(self, research_results: Dict[str, Any]) -> float:
        """Calculate overall web presence score"""
        score = 0.0
        
        # Website presence
        if research_results['basic_discovery'].get('website_url'):
            score += 0.3
        
        # LinkedIn presence  
        if research_results['basic_discovery'].get('linkedin_url'):
            score += 0.2
        
        # Search result volume
        web_research = research_results.get('web_research', {})
        result_count = web_research.get('total_results', 0)
        if result_count > 10:
            score += 0.3
        elif result_count > 5:
            score += 0.2
        elif result_count > 0:
            score += 0.1
        
        # News presence
        news_count = research_results.get('news_coverage', {}).get('total_articles', 0)
        if news_count > 5:
            score += 0.2
        elif news_count > 0:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_data_completeness(self, research_results: Dict[str, Any]) -> float:
        """Calculate data completeness score"""
        completeness_factors = [
            research_results['basic_discovery'].get('website_url') is not None,
            research_results['basic_discovery'].get('linkedin_url') is not None,
            research_results['location_info'].get('primary_location') is not None,
            len(research_results.get('web_research', {}).get('general_info', [])) > 0,
            len(research_results.get('news_coverage', {}).get('recent_news', [])) > 0
        ]
        
        return sum(completeness_factors) / len(completeness_factors)
    
    def _calculate_research_confidence(self, research_results: Dict[str, Any]) -> float:
        """Calculate overall research confidence"""
        confidence_factors = []
        
        # Website discovery confidence
        website_conf = research_results['basic_discovery'].get('website_confidence', 0)
        if website_conf > 0:
            confidence_factors.append(website_conf)
        
        # LinkedIn discovery confidence
        linkedin_conf = research_results['basic_discovery'].get('linkedin_confidence', 0)
        if linkedin_conf > 0:
            confidence_factors.append(linkedin_conf)
        
        # Search result relevance
        web_research = research_results.get('web_research', {})
        if web_research.get('search_successful'):
            confidence_factors.append(0.7)  # Base confidence for successful search
        
        # Data source diversity
        source_count = len(research_results['research_metadata']['sources_successful'])
        source_diversity_score = min(source_count / 4.0, 1.0)  # Max 4 main sources
        confidence_factors.append(source_diversity_score)
        
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
    
    def _calculate_research_metrics(self, research_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate final research metrics"""
        metadata = research_results['research_metadata'].copy()
        
        # Count total data points
        total_data_points = 0
        
        # Basic discovery data points
        if research_results['basic_discovery'].get('website_url'):
            total_data_points += 1
        if research_results['basic_discovery'].get('linkedin_url'):
            total_data_points += 1
        
        # Web research data points
        web_research = research_results.get('web_research', {})
        total_data_points += web_research.get('total_results', 0)
        
        # Filing data points
        filings = research_results.get('public_filings', {})
        total_data_points += filings.get('total_filings', 0)
        
        # News data points
        news = research_results.get('news_coverage', {})
        total_data_points += news.get('total_articles', 0)
        
        # Location data points
        location = research_results.get('location_info', {})
        if location.get('primary_location'):
            total_data_points += 1
        total_data_points += len(location.get('additional_locations', []))
        
        metadata['total_data_points'] = total_data_points
        metadata['confidence_score'] = self._calculate_research_confidence(research_results)
        
        return metadata