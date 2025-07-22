"""
Public filings discovery service for finding SEC and state business filings
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote_plus, urljoin

import aiohttp
from bs4 import BeautifulSoup

from ...core.config import get_config
from ...models.discovery import PublicFilingResult

logger = logging.getLogger(__name__)


class PublicFilingsService:
    """Service for discovering public filings and business registrations"""
    
    def __init__(self):
        self.config = get_config()
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 2.0
        
        # Known filing sources
        self.filing_sources = {
            'sec_edgar': {
                'base_url': 'https://www.sec.gov/edgar/search/',
                'search_pattern': 'https://www.sec.gov/edgar/search/#/q={query}&dateRange=all',
                'filing_types': ['10-K', '10-Q', '8-K', 'S-1', 'DEF 14A']
            },
            'delaware_corp': {
                'base_url': 'https://icis.corp.delaware.gov/',
                'search_pattern': 'https://icis.corp.delaware.gov/Ecorp/EntitySearch/ByName.aspx'
            },
            'california_sos': {
                'base_url': 'https://bizfileonline.sos.ca.gov/',
                'search_pattern': 'https://bizfileonline.sos.ca.gov/search/business'
            }
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=self.headers
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def discover_public_filings(
        self, 
        company_name: str,
        include_sec: bool = True,
        include_state: bool = True,
        max_results_per_source: int = 10
    ) -> Dict[str, List[PublicFilingResult]]:
        """Discover public filings for a company"""
        
        results = {
            'sec_filings': [],
            'state_filings': [],
            'other_filings': []
        }
        
        try:
            # Search SEC EDGAR database
            if include_sec:
                sec_results = await self._search_sec_edgar(company_name, max_results_per_source)
                results['sec_filings'] = sec_results
            
            # Search state business registrations
            if include_state:
                state_results = await self._search_state_filings(company_name, max_results_per_source)
                results['state_filings'] = state_results
            
            # Search additional sources via Google
            google_results = await self._search_filings_via_google(company_name, max_results_per_source)
            results['other_filings'] = google_results
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to discover public filings for {company_name}: {e}")
            return results
    
    async def _search_sec_edgar(self, company_name: str, max_results: int) -> List[PublicFilingResult]:
        """Search SEC EDGAR database"""
        filings = []
        
        if not self.session:
            return filings
        
        try:
            # Rate limiting
            await self._rate_limit('sec.gov')
            
            # Search via SEC EDGAR API (if available) or scraping
            search_terms = [
                company_name,
                company_name.replace(' ', '+'),
                company_name.replace(' Inc', '').replace(' LLC', '').replace(' Corp', '').strip()
            ]
            
            for term in search_terms:
                try:
                    # Try SEC search endpoint
                    search_url = f"https://efts.sec.gov/LATEST/search-index"
                    params = {
                        'q': term,
                        'dateRange': 'all',
                        'category': 'custom',
                        'forms': '10-K,10-Q,8-K'
                    }
                    
                    async with self.session.get(search_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            sec_filings = self._parse_sec_response(data, company_name)
                            filings.extend(sec_filings)
                            
                except Exception as e:
                    logger.debug(f"SEC search failed for term {term}: {e}")
                    continue
                
                if len(filings) >= max_results:
                    break
            
            # Fallback: Search via Google for SEC filings
            if not filings:
                google_sec = await self._google_search_sec_filings(company_name, max_results)
                filings.extend(google_sec)
            
            return filings[:max_results]
            
        except Exception as e:
            logger.error(f"SEC EDGAR search failed: {e}")
            return filings
    
    def _parse_sec_response(self, data: Dict, company_name: str) -> List[PublicFilingResult]:
        """Parse SEC API response"""
        filings = []
        
        try:
            hits = data.get('hits', {}).get('hits', [])
            
            for hit in hits:
                source = hit.get('_source', {})
                
                # Extract filing information
                filing = PublicFilingResult(
                    filing_type='SEC',
                    filing_url=f"https://www.sec.gov/Archives/edgar/data/{source.get('cik')}/{source.get('accession_number')}/{source.get('file_name')}",
                    filing_title=f"{source.get('form')} - {source.get('company_name')}",
                    filing_date=source.get('filed_date'),
                    jurisdiction='Federal (SEC)',
                    confidence=self._calculate_sec_confidence(source, company_name)
                )
                
                filings.append(filing)
                
        except Exception as e:
            logger.debug(f"Failed to parse SEC response: {e}")
        
        return filings
    
    def _calculate_sec_confidence(self, filing_data: Dict, company_name: str) -> float:
        """Calculate confidence score for SEC filing match"""
        score = 0.0
        
        # Company name match
        filing_company = filing_data.get('company_name', '').lower()
        search_company = company_name.lower()
        
        if search_company in filing_company:
            score += 0.6
        elif any(word in filing_company for word in search_company.split()):
            score += 0.3
        
        # Recent filings get higher score
        form_type = filing_data.get('form', '')
        if form_type in ['10-K', '10-Q']:
            score += 0.3
        elif form_type in ['8-K']:
            score += 0.2
        
        return min(score, 1.0)
    
    async def _search_state_filings(self, company_name: str, max_results: int) -> List[PublicFilingResult]:
        """Search state business registrations"""
        filings = []
        
        # Common state searches
        state_searches = [
            ('Delaware', self._search_delaware_filings),
            ('California', self._search_california_filings),
            ('Nevada', self._search_nevada_filings),
            ('New York', self._search_newyork_filings)
        ]
        
        for state_name, search_func in state_searches:
            try:
                state_results = await search_func(company_name, max_results // len(state_searches))
                filings.extend(state_results)
                
                if len(filings) >= max_results:
                    break
                    
            except Exception as e:
                logger.debug(f"State search failed for {state_name}: {e}")
                continue
        
        return filings[:max_results]
    
    async def _search_delaware_filings(self, company_name: str, max_results: int) -> List[PublicFilingResult]:
        """Search Delaware Division of Corporations"""
        filings = []
        
        try:
            await self._rate_limit('corp.delaware.gov')
            
            # Delaware corporate search (simplified - actual implementation would need form submission)
            search_url = "https://icis.corp.delaware.gov/Ecorp/EntitySearch/ByName.aspx"
            
            # For demo purposes, return placeholder results
            # Real implementation would scrape the search form and results
            
            # Google search as fallback
            google_query = f'"{company_name}" site:corp.delaware.gov'
            google_results = await self._google_search_filings(google_query, 'Delaware', max_results)
            filings.extend(google_results)
            
        except Exception as e:
            logger.debug(f"Delaware search failed: {e}")
        
        return filings
    
    async def _search_california_filings(self, company_name: str, max_results: int) -> List[PublicFilingResult]:
        """Search California Secretary of State"""
        filings = []
        
        try:
            # Google search for CA SOS filings
            google_query = f'"{company_name}" site:sos.ca.gov OR site:bizfileonline.sos.ca.gov'
            google_results = await self._google_search_filings(google_query, 'California', max_results)
            filings.extend(google_results)
            
        except Exception as e:
            logger.debug(f"California search failed: {e}")
        
        return filings
    
    async def _search_nevada_filings(self, company_name: str, max_results: int) -> List[PublicFilingResult]:
        """Search Nevada Secretary of State"""
        filings = []
        
        try:
            google_query = f'"{company_name}" site:nvsos.gov'
            google_results = await self._google_search_filings(google_query, 'Nevada', max_results)
            filings.extend(google_results)
            
        except Exception as e:
            logger.debug(f"Nevada search failed: {e}")
        
        return filings
    
    async def _search_newyork_filings(self, company_name: str, max_results: int) -> List[PublicFilingResult]:
        """Search New York Department of State"""
        filings = []
        
        try:
            google_query = f'"{company_name}" site:dos.ny.gov'
            google_results = await self._google_search_filings(google_query, 'New York', max_results)
            filings.extend(google_results)
            
        except Exception as e:
            logger.debug(f"New York search failed: {e}")
        
        return filings
    
    async def _google_search_sec_filings(self, company_name: str, max_results: int) -> List[PublicFilingResult]:
        """Search for SEC filings via Google"""
        filings = []
        
        sec_queries = [
            f'"{company_name}" site:sec.gov "10-K"',
            f'"{company_name}" site:sec.gov "10-Q"',
            f'"{company_name}" site:sec.gov "8-K"',
            f'"{company_name}" site:edgar.sec.gov'
        ]
        
        for query in sec_queries:
            try:
                results = await self._google_search_filings(query, 'Federal (SEC)', max_results // len(sec_queries))
                filings.extend(results)
                
            except Exception as e:
                logger.debug(f"Google SEC search failed for query {query}: {e}")
        
        return filings[:max_results]
    
    async def _search_filings_via_google(self, company_name: str, max_results: int) -> List[PublicFilingResult]:
        """Search for other filings via Google"""
        filings = []
        
        other_queries = [
            f'"{company_name}" "articles of incorporation"',
            f'"{company_name}" "certificate of formation"',
            f'"{company_name}" "business license"',
            f'"{company_name}" "corporate registration"'
        ]
        
        for query in other_queries:
            try:
                results = await self._google_search_filings(query, 'Other', max_results // len(other_queries))
                filings.extend(results)
                
            except Exception as e:
                logger.debug(f"Google other filings search failed: {e}")
        
        return filings[:max_results]
    
    async def _google_search_filings(self, query: str, jurisdiction: str, max_results: int) -> List[PublicFilingResult]:
        """Perform Google search for filings"""
        filings = []
        
        if not self.session:
            return filings
        
        try:
            await self._rate_limit('google.com')
            
            # Construct Google search URL
            encoded_query = quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded_query}&num={max_results}"
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    return filings
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Parse search results
                result_containers = soup.find_all('div', class_='g')
                
                for container in result_containers:
                    try:
                        # Extract title and URL
                        title_elem = container.find('h3')
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
                        snippet_elem = container.find('span', class_='aCOpRe')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        
                        # Determine filing type
                        filing_type = self._classify_filing_type(title, snippet, url)
                        
                        # Calculate confidence
                        confidence = self._calculate_filing_confidence(title, snippet, query)
                        
                        filing = PublicFilingResult(
                            filing_type=filing_type,
                            filing_url=url,
                            filing_title=title,
                            filing_date=None,  # Would need additional parsing
                            jurisdiction=jurisdiction,
                            confidence=confidence
                        )
                        
                        filings.append(filing)
                        
                    except Exception as e:
                        logger.debug(f"Failed to parse filing result: {e}")
                        continue
                
        except Exception as e:
            logger.error(f"Google filing search failed: {e}")
        
        return filings
    
    def _classify_filing_type(self, title: str, snippet: str, url: str) -> str:
        """Classify the type of filing based on content"""
        content = f"{title} {snippet} {url}".lower()
        
        if 'sec.gov' in url or 'edgar' in url:
            if '10-k' in content:
                return 'SEC 10-K'
            elif '10-q' in content:
                return 'SEC 10-Q'
            elif '8-k' in content:
                return 'SEC 8-K'
            else:
                return 'SEC'
        elif 'sos.ca.gov' in url:
            return 'CA State'
        elif 'corp.delaware.gov' in url:
            return 'DE State'
        elif 'nvsos.gov' in url:
            return 'NV State'
        elif 'dos.ny.gov' in url:
            return 'NY State'
        elif any(term in content for term in ['incorporation', 'formation', 'license']):
            return 'Business Registration'
        else:
            return 'Other'
    
    def _calculate_filing_confidence(self, title: str, snippet: str, query: str) -> float:
        """Calculate confidence score for filing result"""
        score = 0.0
        
        content = f"{title} {snippet}".lower()
        query_lower = query.lower()
        
        # Check for query term matches
        query_terms = set(re.findall(r'\w+', query_lower))
        content_terms = set(re.findall(r'\w+', content))
        
        overlap = len(query_terms.intersection(content_terms))
        if len(query_terms) > 0:
            score += (overlap / len(query_terms)) * 0.6
        
        # Bonus for official domains
        if any(domain in snippet.lower() for domain in ['sec.gov', 'sos.', '.gov']):
            score += 0.3
        
        # Bonus for filing-related terms
        filing_terms = ['filing', 'form', 'registration', 'incorporation', 'certificate']
        if any(term in content for term in filing_terms):
            score += 0.1
        
        return min(score, 1.0)
    
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