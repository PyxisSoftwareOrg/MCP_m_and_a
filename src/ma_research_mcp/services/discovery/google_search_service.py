"""
Google Search service for comprehensive company research
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote_plus, urlparse

import aiohttp
from bs4 import BeautifulSoup

from ...core.config import get_config
from ...models.discovery import GoogleSearchResult, SearchQuery

logger = logging.getLogger(__name__)


class GoogleSearchService:
    """Google search service for company research"""
    
    def __init__(self):
        self.config = get_config()
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=self.headers
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_company_information(
        self, 
        company_name: str,
        include_filings: bool = True,
        include_news: bool = True,
        include_reviews: bool = True,
        max_results: int = 10
    ) -> Dict[str, List[GoogleSearchResult]]:
        """Search for comprehensive company information"""
        
        results = {
            'general': [],
            'filings': [],
            'news': [],
            'reviews': [],
            'about': []
        }
        
        try:
            # General company information
            general_query = f'"{company_name}" company business software'
            results['general'] = await self._perform_search(general_query, max_results)
            
            # About/overview pages
            about_query = f'"{company_name}" about company overview'
            results['about'] = await self._perform_search(about_query, max_results // 2)
            
            if include_filings:
                # SEC filings
                sec_query = f'"{company_name}" site:sec.gov OR site:edgar.sec.gov'
                results['filings'].extend(await self._perform_search(sec_query, 5))
                
                # State business filings
                state_query = f'"{company_name}" "business filing" OR "corporation" OR "LLC"'
                results['filings'].extend(await self._perform_search(state_query, 5))
            
            if include_news:
                # News and press coverage
                news_query = f'"{company_name}" news OR press OR announcement'
                results['news'] = await self._perform_search(news_query, max_results)
            
            if include_reviews:
                # Reviews and mentions
                review_query = f'"{company_name}" review OR rating OR testimonial'
                results['reviews'] = await self._perform_search(review_query, max_results // 2)
            
            # Remove duplicates and filter relevant results
            for category in results:
                results[category] = self._filter_and_deduplicate(results[category], company_name)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search company information for {company_name}: {e}")
            return results
    
    async def _perform_search(self, query: str, max_results: int = 10) -> List[GoogleSearchResult]:
        """Perform a Google search and parse results"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        try:
            # Rate limiting
            await self._rate_limit()
            
            # Construct search URL
            encoded_query = quote_plus(query)
            url = f"https://www.google.com/search?q={encoded_query}&num={max_results}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Google search returned status {response.status}")
                    return []
                
                html = await response.text()
                return self._parse_search_results(html, query)
                
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
    
    def _parse_search_results(self, html: str, query: str) -> List[GoogleSearchResult]:
        """Parse Google search results HTML"""
        results = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find search result containers
            result_containers = soup.find_all('div', class_='g')
            
            for container in result_containers:
                try:
                    # Extract title
                    title_elem = container.find('h3')
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    
                    # Extract URL
                    link_elem = container.find('a')
                    if not link_elem or not link_elem.get('href'):
                        continue
                    url = link_elem['href']
                    
                    # Clean up URL (remove Google redirect)
                    if url.startswith('/url?q='):
                        url = url.split('/url?q=')[1].split('&')[0]
                    
                    # Extract snippet
                    snippet_elem = container.find('span', class_='aCOpRe') or container.find('div', class_='VwiC3b')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # Extract domain
                    try:
                        domain = urlparse(url).netloc
                    except:
                        domain = ""
                    
                    # Calculate relevance score
                    relevance_score = self._calculate_relevance(title, snippet, query)
                    
                    result = GoogleSearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        domain=domain,
                        query=query,
                        relevance_score=relevance_score
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.debug(f"Failed to parse search result: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to parse search results: {e}")
        
        return results
    
    def _calculate_relevance(self, title: str, snippet: str, query: str) -> float:
        """Calculate relevance score for search result"""
        score = 0.0
        
        # Extract query terms
        query_terms = set(re.findall(r'\w+', query.lower()))
        
        # Check title matches
        title_words = set(re.findall(r'\w+', title.lower()))
        title_matches = len(query_terms.intersection(title_words))
        score += title_matches * 2.0
        
        # Check snippet matches
        snippet_words = set(re.findall(r'\w+', snippet.lower()))
        snippet_matches = len(query_terms.intersection(snippet_words))
        score += snippet_matches * 1.0
        
        # Bonus for exact phrase matches
        if any(term in title.lower() for term in query_terms):
            score += 1.0
        
        # Normalize score
        max_possible = len(query_terms) * 3.0 + 1.0
        return min(score / max_possible, 1.0) if max_possible > 0 else 0.0
    
    def _filter_and_deduplicate(
        self, 
        results: List[GoogleSearchResult], 
        company_name: str
    ) -> List[GoogleSearchResult]:
        """Filter and deduplicate search results"""
        
        # Remove duplicates by URL
        seen_urls = set()
        filtered = []
        
        for result in results:
            if result.url in seen_urls:
                continue
            seen_urls.add(result.url)
            
            # Filter out irrelevant results
            if self._is_relevant_result(result, company_name):
                filtered.append(result)
        
        # Sort by relevance score
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return filtered
    
    def _is_relevant_result(self, result: GoogleSearchResult, company_name: str) -> bool:
        """Check if search result is relevant to company"""
        
        # Skip if no content
        if not result.title and not result.snippet:
            return False
        
        # Skip common irrelevant domains
        irrelevant_domains = {
            'wikipedia.org', 'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'linkedin.com', 'glassdoor.com', 'indeed.com'
        }
        
        if result.domain in irrelevant_domains:
            return False
        
        # Check for company name mention
        content = f"{result.title} {result.snippet}".lower()
        company_words = company_name.lower().split()
        
        # Require at least one company name word to appear
        if not any(word in content for word in company_words):
            return False
        
        return True
    
    async def _rate_limit(self):
        """Implement rate limiting"""
        import time
        
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def search_public_filings(self, company_name: str) -> List[GoogleSearchResult]:
        """Search for public filings specifically"""
        results = []
        
        # SEC EDGAR database
        sec_queries = [
            f'"{company_name}" site:sec.gov',
            f'"{company_name}" site:edgar.sec.gov',
            f'"{company_name}" "form 10-K" OR "form 10-Q" OR "form 8-K"'
        ]
        
        for query in sec_queries:
            search_results = await self._perform_search(query, 5)
            results.extend(search_results)
        
        # State business registrations
        state_queries = [
            f'"{company_name}" "secretary of state" registration',
            f'"{company_name}" "business license" OR "corporation filing"',
            f'"{company_name}" "articles of incorporation"'
        ]
        
        for query in state_queries:
            search_results = await self._perform_search(query, 3)
            results.extend(search_results)
        
        return self._filter_and_deduplicate(results, company_name)
    
    async def search_news_coverage(self, company_name: str) -> List[GoogleSearchResult]:
        """Search for news and media coverage"""
        news_queries = [
            f'"{company_name}" news',
            f'"{company_name}" press release',
            f'"{company_name}" announcement',
            f'"{company_name}" funding OR investment OR acquisition',
            f'"{company_name}" CEO OR founder OR leadership'
        ]
        
        results = []
        for query in news_queries:
            search_results = await self._perform_search(query, 5)
            results.extend(search_results)
        
        return self._filter_and_deduplicate(results, company_name)