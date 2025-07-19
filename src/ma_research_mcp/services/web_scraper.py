"""
Intelligent web scraping service for M&A Research Assistant
"""

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import aiohttp
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.config import get_config

logger = logging.getLogger(__name__)


class WebScrapingService:
    """Intelligent web scraping with priority keyword targeting"""
    
    def __init__(self):
        self.config = get_config()
        self.session = None
        
        # Rate limiting
        self.requests_per_second = self.config.WEB_SCRAPING_REQUESTS_PER_SECOND
        self.concurrent_domains = self.config.WEB_SCRAPING_CONCURRENT_DOMAINS
        self.last_request_time = {}
        
        # Resource limits
        self.max_pages_per_company = self.config.MAX_PAGES_PER_COMPANY
        self.max_content_size = self._parse_size(self.config.MAX_WEBSITE_CONTENT_SIZE)
        
        # Priority keywords for content discovery
        self.priority_keywords = [
            'pricing', 'products', 'solutions', 'about', 'customers', 'case studies',
            'industries', 'vertical', 'enterprise', 'software', 'platform', 'suite',
            'team', 'company', 'management', 'leadership', 'contact', 'features'
        ]
        
        # Headers to appear as a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        }
        
        logger.info("Initialized web scraping service")
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes"""
        size_str = size_str.upper()
        if 'MB' in size_str:
            return int(size_str.replace('MB', '')) * 1024 * 1024
        elif 'KB' in size_str:
            return int(size_str.replace('KB', '')) * 1024
        else:
            return int(size_str)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=self.concurrent_domains)
            )
        return self.session
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _check_robots_txt(self, base_url: str) -> bool:
        """Check if scraping is allowed by robots.txt"""
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            
            # Use synchronous requests for robots.txt check
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                return rp.can_fetch(self.headers['User-Agent'], base_url)
            return True  # If no robots.txt, assume allowed
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {base_url}: {e}")
            return True  # Default to allowed if check fails
    
    async def _rate_limit_check(self, domain: str) -> None:
        """Enforce rate limiting per domain"""
        current_time = time.time()
        
        if domain in self.last_request_time:
            time_since_last = current_time - self.last_request_time[domain]
            min_interval = 1.0 / self.requests_per_second
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                await asyncio.sleep(sleep_time)
        
        self.last_request_time[domain] = time.time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _fetch_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch single page with error handling"""
        try:
            domain = urlparse(url).netloc
            await self._rate_limit_check(domain)
            
            session = await self._get_session()
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > self.max_content_size:
                    logger.warning(f"Content too large for {url}: {content_length} bytes")
                    return None
                
                html_content = await response.text()
                
                if len(html_content) > self.max_content_size:
                    logger.warning(f"HTML content too large for {url}: {len(html_content)} bytes")
                    html_content = html_content[:self.max_content_size]
                
                return {
                    'url': url,
                    'status_code': response.status,
                    'html_content': html_content,
                    'content_type': response.headers.get('Content-Type', ''),
                    'content_length': len(html_content),
                    'fetch_time': time.time()
                }
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {url}")
            return None
        except aiohttp.ClientError as e:
            logger.warning(f"Client error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None
    
    def _extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract links from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                full_url = urljoin(base_url, href)
                
                # Only include links from same domain
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    links.append(full_url)
            
            return list(set(links))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting links: {e}")
            return []
    
    def _score_link_priority(self, url: str, link_text: str) -> float:
        """Score link priority based on keywords and patterns"""
        score = 0.0
        url_lower = url.lower()
        text_lower = link_text.lower()
        
        # Check for priority keywords in URL
        for keyword in self.priority_keywords:
            if keyword in url_lower:
                score += 2.0
            if keyword in text_lower:
                score += 1.5
        
        # Bonus for common valuable pages
        valuable_patterns = [
            r'/about', r'/products', r'/solutions', r'/pricing', 
            r'/customers', r'/industries', r'/platform', r'/features',
            r'/team', r'/company', r'/leadership'
        ]
        
        for pattern in valuable_patterns:
            if re.search(pattern, url_lower):
                score += 3.0
                break
        
        # Penalty for low-value pages
        avoid_patterns = [
            r'/blog', r'/news', r'/support', r'/help', r'/docs',
            r'/privacy', r'/terms', r'/legal', r'/careers'
        ]
        
        for pattern in avoid_patterns:
            if re.search(pattern, url_lower):
                score -= 1.0
        
        # Penalty for very long URLs (likely dynamic)
        if len(url) > 100:
            score -= 0.5
        
        return max(0.0, score)
    
    def _extract_structured_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract structured content from HTML"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            content = {
                'url': url,
                'title': '',
                'description': '',
                'headings': [],
                'text_content': '',
                'key_phrases': [],
                'contact_info': {},
                'pricing_info': [],
                'product_info': [],
                'company_info': {}
            }
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                content['title'] = title_tag.get_text().strip()
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                content['description'] = meta_desc.get('content', '').strip()
            
            # Extract headings
            for i in range(1, 7):
                headings = soup.find_all(f'h{i}')
                for heading in headings:
                    text = heading.get_text().strip()
                    if text:
                        content['headings'].append({
                            'level': i,
                            'text': text
                        })
            
            # Extract main text content
            content['text_content'] = soup.get_text()
            
            # Clean up text content
            lines = [line.strip() for line in content['text_content'].splitlines()]
            content['text_content'] = '\n'.join(line for line in lines if line)
            
            # Extract contact information
            content['contact_info'] = self._extract_contact_info(soup)
            
            # Extract pricing information
            content['pricing_info'] = self._extract_pricing_info(soup)
            
            # Extract product information
            content['product_info'] = self._extract_product_info(soup)
            
            # Extract company information
            content['company_info'] = self._extract_company_info(soup)
            
            return content
            
        except Exception as e:
            logger.error(f"Error extracting structured content from {url}: {e}")
            return {'url': url, 'error': str(e)}
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract contact information"""
        contact_info = {}
        text = soup.get_text()
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info['emails'] = list(set(emails))
        
        # Phone patterns
        phone_pattern = r'[\+]?[1-9]?[\s\-\.]?\(?[0-9]{3}\)?[\s\-\.]?[0-9]{3}[\s\-\.]?[0-9]{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact_info['phones'] = [phone.strip() for phone in phones if len(phone.strip()) > 7]
        
        # Address patterns (basic)
        address_indicators = ['address', 'location', 'office', 'headquarters']
        for indicator in address_indicators:
            pattern = rf'{indicator}[:\s]*([^.!?]*?)(?:\.|!|\?|$)'
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                contact_info[f'{indicator}_text'] = matches[0].strip()
        
        return contact_info
    
    def _extract_pricing_info(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract pricing information"""
        pricing_info = []
        text = soup.get_text()
        
        # Price patterns
        price_patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,000.00
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|dollars?)',  # 1000 USD
            r'from\s*\$(\d+)',  # from $99
            r'starting\s*(?:at\s*)?\$(\d+)',  # starting at $99
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                pricing_info.append({
                    'amount': match,
                    'context': 'extracted_from_text'
                })
        
        # Look for pricing tables
        tables = soup.find_all('table')
        for table in tables:
            table_text = table.get_text().lower()
            if any(word in table_text for word in ['price', 'cost', 'plan', 'subscription']):
                pricing_info.append({
                    'type': 'pricing_table',
                    'content': table.get_text().strip()
                })
        
        return pricing_info
    
    def _extract_product_info(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract product information"""
        product_info = []
        
        # Look for product sections
        product_sections = soup.find_all(['div', 'section'], 
                                       class_=re.compile(r'product|solution|feature', re.I))
        
        for section in product_sections:
            title_elem = section.find(['h1', 'h2', 'h3', 'h4'])
            title = title_elem.get_text().strip() if title_elem else 'Product'
            
            description = section.get_text().strip()
            
            product_info.append({
                'title': title,
                'description': description[:500],  # Limit length
                'type': 'product_section'
            })
        
        return product_info
    
    def _extract_company_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract company information"""
        company_info = {}
        text = soup.get_text()
        
        # Look for company size indicators
        size_patterns = [
            r'(\d+)\s*(?:\+)?\s*employees',
            r'team\s*of\s*(\d+)',
            r'(\d+)\s*(?:\+)?\s*people',
        ]
        
        for pattern in size_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                company_info['employee_count_mentions'] = matches
        
        # Look for founding year
        year_pattern = r'(?:founded|established|since)\s*(?:in\s*)?(\d{4})'
        year_matches = re.findall(year_pattern, text, re.IGNORECASE)
        if year_matches:
            company_info['founding_year_mentions'] = year_matches
        
        # Look for industry/vertical mentions
        industry_keywords = [
            'healthcare', 'education', 'finance', 'retail', 'manufacturing',
            'sports', 'fitness', 'hospitality', 'real estate', 'legal',
            'construction', 'automotive', 'agriculture', 'logistics'
        ]
        
        found_industries = []
        for keyword in industry_keywords:
            if keyword in text.lower():
                found_industries.append(keyword)
        
        if found_industries:
            company_info['industry_mentions'] = found_industries
        
        return company_info
    
    async def scrape_website(
        self,
        website_url: str,
        max_pages: int = 5,
        priority_keywords: List[str] = None
    ) -> Dict[str, Any]:
        """Main method to scrape website with intelligent prioritization"""
        try:
            # Parse and validate URL
            parsed_url = urlparse(website_url)
            if not parsed_url.scheme:
                website_url = f"https://{website_url}"
                parsed_url = urlparse(website_url)
            
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Check robots.txt
            if not await self._check_robots_txt(base_url):
                logger.warning(f"Robots.txt disallows scraping {base_url}")
                return {
                    'success': False,
                    'error': 'Scraping disallowed by robots.txt'
                }
            
            # Combine priority keywords
            all_keywords = self.priority_keywords.copy()
            if priority_keywords:
                all_keywords.extend(priority_keywords)
            
            scraped_pages = []
            visited_urls = set()
            
            # Start with main page
            logger.info(f"Starting to scrape {website_url}")
            main_page = await self._fetch_page(website_url)
            
            if not main_page:
                return {
                    'success': False,
                    'error': 'Failed to fetch main page'
                }
            
            # Process main page
            main_content = self._extract_structured_content(
                main_page['html_content'], 
                website_url
            )
            scraped_pages.append(main_content)
            visited_urls.add(website_url)
            
            # Extract and prioritize links
            if max_pages > 1:
                links = self._extract_links(main_page['html_content'], base_url)
                
                # Score and sort links
                link_scores = []
                soup = BeautifulSoup(main_page['html_content'], 'html.parser')
                
                for link in links:
                    if link not in visited_urls:
                        # Find link text
                        link_elem = soup.find('a', href=lambda x: x and link.endswith(x))
                        link_text = link_elem.get_text().strip() if link_elem else ''
                        
                        score = self._score_link_priority(link, link_text)
                        link_scores.append((link, score, link_text))
                
                # Sort by score and take top pages
                link_scores.sort(key=lambda x: x[1], reverse=True)
                priority_links = link_scores[:max_pages-1]
                
                # Scrape priority pages
                for link, score, link_text in priority_links:
                    if len(scraped_pages) >= max_pages:
                        break
                    
                    logger.info(f"Scraping priority page: {link} (score: {score:.1f})")
                    page_data = await self._fetch_page(link)
                    
                    if page_data:
                        page_content = self._extract_structured_content(
                            page_data['html_content'], 
                            link
                        )
                        page_content['priority_score'] = score
                        page_content['link_text'] = link_text
                        scraped_pages.append(page_content)
                        visited_urls.add(link)
            
            # Compile results
            result = {
                'success': True,
                'website_url': website_url,
                'base_url': base_url,
                'pages_scraped': len(scraped_pages),
                'total_content_length': sum(len(page.get('text_content', '')) for page in scraped_pages),
                'scraped_pages': scraped_pages,
                'scraping_metadata': {
                    'scrape_timestamp': time.time(),
                    'max_pages_requested': max_pages,
                    'priority_keywords_used': all_keywords,
                    'visited_urls': list(visited_urls)
                }
            }
            
            logger.info(f"Successfully scraped {len(scraped_pages)} pages from {website_url}")
            return result
            
        except Exception as e:
            logger.error(f"Error scraping website {website_url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'website_url': website_url
            }
        finally:
            # Clean up session if needed
            pass
    
    def __del__(self):
        """Cleanup when service is destroyed"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            # Note: This is not ideal for async cleanup, but serves as fallback
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.session.close())
            except:
                pass