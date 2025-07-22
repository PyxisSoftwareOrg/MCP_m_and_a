"""
News and media coverage discovery service for comprehensive company research
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote_plus, urlparse

import aiohttp
from bs4 import BeautifulSoup

from ...core.config import get_config
from ...models.discovery import NewsResult

logger = logging.getLogger(__name__)


class NewsDiscoveryService:
    """Service for discovering news and media coverage about companies"""
    
    def __init__(self):
        self.config = get_config()
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 2.0
        
        # News source domains to prioritize
        self.news_domains = {
            'tier1': [
                'reuters.com', 'bloomberg.com', 'wsj.com', 'nytimes.com',
                'ft.com', 'forbes.com', 'businessinsider.com', 'cnbc.com'
            ],
            'tech': [
                'techcrunch.com', 'venturebeat.com', 'techcrunchy.com', 'arstechnica.com',
                'wired.com', 'theverge.com', 'zdnet.com', 'computerworld.com'
            ],
            'business': [
                'inc.com', 'entrepreneur.com', 'fastcompany.com', 'harvard.edu',
                'knowledge.wharton.upenn.edu', 'strategy-business.com'
            ],
            'industry': [
                'informationweek.com', 'cio.com', 'computerweekly.com',
                'silicon.com', 'govtech.com', 'industryweek.com'
            ]
        }
        
        # Sentiment keywords
        self.positive_keywords = [
            'success', 'growth', 'expansion', 'funding', 'investment', 'acquisition',
            'partnership', 'innovation', 'breakthrough', 'award', 'recognition',
            'milestone', 'achievement', 'launch', 'expansion'
        ]
        
        self.negative_keywords = [
            'lawsuit', 'fine', 'penalty', 'investigation', 'fraud', 'scandal',
            'bankruptcy', 'layoffs', 'closure', 'violation', 'breach', 'hack',
            'data breach', 'security', 'decline', 'loss'
        ]
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=self.headers
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def discover_news_coverage(
        self, 
        company_name: str,
        time_range: str = "1y",  # 1y, 6m, 3m, 1m, 1w
        include_press_releases: bool = True,
        include_mentions: bool = True,
        max_results: int = 20
    ) -> Dict[str, List[NewsResult]]:
        """Discover news and media coverage for a company"""
        
        results = {
            'recent_news': [],
            'press_releases': [],
            'funding_news': [],
            'leadership_news': [],
            'product_news': [],
            'mentions': []
        }
        
        try:
            # Search for recent news
            recent_news = await self._search_recent_news(company_name, time_range, max_results // 2)
            results['recent_news'] = recent_news
            
            # Search for press releases
            if include_press_releases:
                press_releases = await self._search_press_releases(company_name, max_results // 4)
                results['press_releases'] = press_releases
            
            # Search for specific types of news
            funding_news = await self._search_funding_news(company_name, max_results // 6)
            results['funding_news'] = funding_news
            
            leadership_news = await self._search_leadership_news(company_name, max_results // 6)
            results['leadership_news'] = leadership_news
            
            product_news = await self._search_product_news(company_name, max_results // 6)
            results['product_news'] = product_news
            
            # Search for general mentions
            if include_mentions:
                mentions = await self._search_company_mentions(company_name, max_results // 4)
                results['mentions'] = mentions
            
            # Remove duplicates across categories
            results = self._deduplicate_news_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to discover news coverage for {company_name}: {e}")
            return results
    
    async def _search_recent_news(self, company_name: str, time_range: str, max_results: int) -> List[NewsResult]:
        """Search for recent news about the company"""
        news_results = []
        
        # Time range mapping
        time_filters = {
            '1w': 'week',
            '1m': 'month', 
            '3m': 'past3months',
            '6m': 'past6months',
            '1y': 'pastyear'
        }
        
        time_filter = time_filters.get(time_range, 'pastyear')
        
        # Search queries for recent news
        news_queries = [
            f'"{company_name}" news',
            f'"{company_name}" announcement',
            f'"{company_name}" update',
            f'"{company_name}" software company'
        ]
        
        for query in news_queries:
            try:
                results = await self._google_news_search(
                    query, 
                    time_filter=time_filter,
                    max_results=max_results // len(news_queries)
                )
                news_results.extend(results)
                
            except Exception as e:
                logger.debug(f"News search failed for query {query}: {e}")
        
        return self._rank_and_filter_news(news_results, company_name, max_results)
    
    async def _search_press_releases(self, company_name: str, max_results: int) -> List[NewsResult]:
        """Search for company press releases"""
        press_releases = []
        
        pr_queries = [
            f'"{company_name}" "press release"',
            f'"{company_name}" "announces" OR "announcement"',
            f'"{company_name}" site:prnewswire.com OR site:businesswire.com',
            f'"{company_name}" "PR Newswire" OR "Business Wire"'
        ]
        
        for query in pr_queries:
            try:
                results = await self._google_news_search(
                    query,
                    max_results=max_results // len(pr_queries)
                )
                press_releases.extend(results)
                
            except Exception as e:
                logger.debug(f"Press release search failed: {e}")
        
        return press_releases[:max_results]
    
    async def _search_funding_news(self, company_name: str, max_results: int) -> List[NewsResult]:
        """Search for funding and investment news"""
        funding_results = []
        
        funding_queries = [
            f'"{company_name}" funding OR investment OR "series A" OR "series B"',
            f'"{company_name}" "raised" OR "secured" OR "closes"',
            f'"{company_name}" venture capital OR VC OR investor',
            f'"{company_name}" acquisition OR merger OR "acquired by"'
        ]
        
        for query in funding_queries:
            try:
                results = await self._google_news_search(
                    query,
                    max_results=max_results // len(funding_queries)
                )
                funding_results.extend(results)
                
            except Exception as e:
                logger.debug(f"Funding news search failed: {e}")
        
        return funding_results[:max_results]
    
    async def _search_leadership_news(self, company_name: str, max_results: int) -> List[NewsResult]:
        """Search for leadership and personnel news"""
        leadership_results = []
        
        leadership_queries = [
            f'"{company_name}" CEO OR "chief executive"',
            f'"{company_name}" founder OR co-founder',
            f'"{company_name}" "new hire" OR "joins" OR "appointed"',
            f'"{company_name}" leadership OR management OR executive'
        ]
        
        for query in leadership_queries:
            try:
                results = await self._google_news_search(
                    query,
                    max_results=max_results // len(leadership_queries)
                )
                leadership_results.extend(results)
                
            except Exception as e:
                logger.debug(f"Leadership news search failed: {e}")
        
        return leadership_results[:max_results]
    
    async def _search_product_news(self, company_name: str, max_results: int) -> List[NewsResult]:
        """Search for product and technology news"""
        product_results = []
        
        product_queries = [
            f'"{company_name}" "product launch" OR "new product"',
            f'"{company_name}" "software" OR "platform" OR "solution"',
            f'"{company_name}" "feature" OR "update" OR "release"',
            f'"{company_name}" technology OR innovation OR development'
        ]
        
        for query in product_queries:
            try:
                results = await self._google_news_search(
                    query,
                    max_results=max_results // len(product_queries)
                )
                product_results.extend(results)
                
            except Exception as e:
                logger.debug(f"Product news search failed: {e}")
        
        return product_results[:max_results]
    
    async def _search_company_mentions(self, company_name: str, max_results: int) -> List[NewsResult]:
        """Search for general company mentions"""
        mentions = []
        
        mention_queries = [
            f'"{company_name}" software OR SaaS OR technology',
            f'"{company_name}" industry OR market OR sector',
            f'"{company_name}" business OR company OR startup',
            f'"{company_name}" customers OR clients OR users'
        ]
        
        for query in mention_queries:
            try:
                results = await self._google_news_search(
                    query,
                    max_results=max_results // len(mention_queries)
                )
                mentions.extend(results)
                
            except Exception as e:
                logger.debug(f"Company mentions search failed: {e}")
        
        return mentions[:max_results]
    
    async def _google_news_search(
        self, 
        query: str, 
        time_filter: str = "pastyear",
        max_results: int = 10
    ) -> List[NewsResult]:
        """Perform Google News search"""
        news_results = []
        
        if not self.session:
            return news_results
        
        try:
            await self._rate_limit('google.com')
            
            # Construct Google News search URL
            encoded_query = quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded_query}&tbm=nws&tbs=qdr:{time_filter}&num={max_results}"
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    return news_results
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Parse news results
                news_containers = soup.find_all('div', class_='SoaBEf')
                
                for container in news_containers:
                    try:
                        # Extract title and URL
                        title_elem = container.find('div', class_='MBeuO')
                        if not title_elem:
                            continue
                        title = title_elem.get_text(strip=True)
                        
                        link_elem = container.find('a')
                        if not link_elem:
                            continue
                        url = link_elem.get('href', '')
                        
                        # Clean URL
                        if url.startswith('/url?q='):
                            url = url.split('/url?q=')[1].split('&')[0]
                        
                        # Extract snippet
                        snippet_elem = container.find('div', class_='GI74Re')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        
                        # Extract source
                        source_elem = container.find('div', class_='CEMjEf')
                        source = source_elem.get_text(strip=True) if source_elem else self._extract_domain(url)
                        
                        # Extract date
                        date_elem = container.find('span', class_='r0bn4c')
                        publish_date = date_elem.get_text(strip=True) if date_elem else None
                        
                        # Calculate relevance and sentiment
                        relevance_score = self._calculate_news_relevance(title, snippet, query)
                        sentiment = self._analyze_sentiment(title, snippet)
                        
                        news_result = NewsResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            source=source,
                            publish_date=publish_date,
                            sentiment=sentiment,
                            relevance_score=relevance_score
                        )
                        
                        news_results.append(news_result)
                        
                    except Exception as e:
                        logger.debug(f"Failed to parse news result: {e}")
                        continue
                
        except Exception as e:
            logger.error(f"Google News search failed: {e}")
        
        return news_results
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc
        except:
            return "Unknown"
    
    def _calculate_news_relevance(self, title: str, snippet: str, query: str) -> float:
        """Calculate relevance score for news result"""
        score = 0.0
        
        content = f"{title} {snippet}".lower()
        query_lower = query.lower()
        
        # Extract query terms
        query_terms = set(re.findall(r'\w+', query_lower))
        content_terms = set(re.findall(r'\w+', content))
        
        # Calculate term overlap
        overlap = len(query_terms.intersection(content_terms))
        if len(query_terms) > 0:
            score += (overlap / len(query_terms)) * 0.6
        
        # Bonus for title matches
        if any(term in title.lower() for term in query_terms):
            score += 0.2
        
        # Bonus for exact phrase matches
        if query.strip('"').lower() in content:
            score += 0.2
        
        return min(score, 1.0)
    
    def _analyze_sentiment(self, title: str, snippet: str) -> str:
        """Analyze sentiment of news content"""
        content = f"{title} {snippet}".lower()
        
        positive_count = sum(1 for keyword in self.positive_keywords if keyword in content)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in content)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _rank_and_filter_news(self, news_results: List[NewsResult], company_name: str, max_results: int) -> List[NewsResult]:
        """Rank and filter news results"""
        
        # Remove duplicates by URL
        seen_urls = set()
        filtered = []
        
        for result in news_results:
            if result.url in seen_urls:
                continue
            seen_urls.add(result.url)
            
            # Filter for relevance
            if self._is_relevant_news(result, company_name):
                filtered.append(result)
        
        # Apply source scoring
        for result in filtered:
            source_bonus = self._get_source_bonus(result.source)
            result.relevance_score = min(result.relevance_score + source_bonus, 1.0)
        
        # Sort by relevance score
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return filtered[:max_results]
    
    def _is_relevant_news(self, result: NewsResult, company_name: str) -> bool:
        """Check if news result is relevant"""
        
        # Minimum relevance threshold
        if result.relevance_score < 0.3:
            return False
        
        # Must mention company name
        content = f"{result.title} {result.snippet}".lower()
        company_words = company_name.lower().split()
        
        if not any(word in content for word in company_words):
            return False
        
        return True
    
    def _get_source_bonus(self, source: str) -> float:
        """Get bonus score based on news source quality"""
        source_lower = source.lower()
        
        # Check tier 1 sources
        for domain in self.news_domains['tier1']:
            if domain in source_lower:
                return 0.3
        
        # Check tech sources
        for domain in self.news_domains['tech']:
            if domain in source_lower:
                return 0.2
        
        # Check business sources
        for domain in self.news_domains['business']:
            if domain in source_lower:
                return 0.15
        
        # Check industry sources
        for domain in self.news_domains['industry']:
            if domain in source_lower:
                return 0.1
        
        return 0.0
    
    def _deduplicate_news_results(self, results: Dict[str, List[NewsResult]]) -> Dict[str, List[NewsResult]]:
        """Remove duplicate news results across categories"""
        
        seen_urls = set()
        deduplicated = {}
        
        # Process in order of importance
        category_order = ['recent_news', 'funding_news', 'press_releases', 'leadership_news', 'product_news', 'mentions']
        
        for category in category_order:
            if category not in results:
                continue
                
            filtered_results = []
            for result in results[category]:
                if result.url not in seen_urls:
                    seen_urls.add(result.url)
                    filtered_results.append(result)
            
            deduplicated[category] = filtered_results
        
        return deduplicated
    
    async def _rate_limit(self, domain: str):
        """Implement rate limiting"""
        import time
        
        current_time = time.time()
        if domain in self.last_request_time:
            time_since_last = current_time - self.last_request_time[domain]
            if time_since_last < self.min_request_interval:
                wait_time = self.min_request_interval - time_since_last
                await asyncio.sleep(wait_time)
        
        self.last_request_time[domain] = time.time()