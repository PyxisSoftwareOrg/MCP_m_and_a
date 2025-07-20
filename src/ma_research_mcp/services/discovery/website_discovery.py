"""
Website discovery service for finding company websites
"""

import asyncio
import logging
import re
import ssl
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import dns.resolver
from tenacity import retry, stop_after_attempt, wait_exponential

from ...models.discovery import WebsiteDiscoveryResult

logger = logging.getLogger(__name__)


class WebsiteDiscoveryService:
    """Service for discovering company websites"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.max_concurrent_checks = 10
        self.request_delay = 0.5  # seconds between requests
        
        # Headers to appear as real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        }
        
        logger.info("Initialized website discovery service")
    
    async def discover_website(
        self,
        company_name: str,
        hints: Optional[Dict[str, Any]] = None
    ) -> WebsiteDiscoveryResult:
        """Discover company website using multiple strategies"""
        
        hints = hints or {}
        
        try:
            # Strategy 1: Direct domain guessing
            domain_result = await self._try_direct_domains(company_name)
            if domain_result.url:
                logger.info(f"Found website via direct domain: {domain_result.url}")
                return domain_result
            
            # Strategy 2: Search engine fallback (placeholder for now)
            # This would integrate with Google Custom Search API
            search_result = await self._try_search_discovery(company_name, hints)
            if search_result.url:
                logger.info(f"Found website via search: {search_result.url}")
                return search_result
            
            # No website found
            logger.info(f"No website found for {company_name}")
            return WebsiteDiscoveryResult(
                url=None,
                confidence=0.0,
                evidence=[f"No website found for {company_name}"],
                discovery_method="none"
            )
            
        except Exception as e:
            logger.error(f"Website discovery failed for {company_name}: {e}")
            return WebsiteDiscoveryResult(
                url=None,
                confidence=0.0,
                evidence=[f"Discovery failed: {str(e)}"],
                discovery_method="error"
            )
    
    async def _try_direct_domains(self, company_name: str) -> WebsiteDiscoveryResult:
        """Try to guess company domain directly"""
        
        # Generate potential domain names
        domain_candidates = self._generate_domain_candidates(company_name)
        
        # Check domains in parallel
        valid_domains = []
        semaphore = asyncio.Semaphore(self.max_concurrent_checks)
        
        async def check_domain(domain: str) -> Optional[Dict[str, Any]]:
            async with semaphore:
                return await self._validate_domain(domain, company_name)
        
        # Check all domains
        tasks = [check_domain(domain) for domain in domain_candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect valid results
        for result in results:
            if isinstance(result, dict) and result.get("valid"):
                valid_domains.append(result)
        
        if not valid_domains:
            return WebsiteDiscoveryResult(
                url=None,
                confidence=0.0,
                evidence=["No valid domains found in direct check"],
                discovery_method="direct"
            )
        
        # Select best domain
        best_domain = self._select_best_domain(valid_domains)
        
        return WebsiteDiscoveryResult(
            url=best_domain["url"],
            confidence=best_domain["confidence"],
            evidence=best_domain["evidence"],
            domain_verified=True,
            ssl_valid=best_domain["ssl_valid"],
            company_name_match=best_domain["name_match"],
            discovery_method="direct"
        )
    
    def _generate_domain_candidates(self, company_name: str) -> List[str]:
        """Generate potential domain names for a company"""
        
        # Normalize company name
        normalized = self._normalize_for_domain(company_name)
        
        domains = []
        tlds = ['.com', '.io', '.net', '.org', '.co', '.ai', '.tech']
        
        # Basic patterns
        for tld in tlds:
            domains.extend([
                f"https://{normalized}{tld}",
                f"https://www.{normalized}{tld}"
            ])
        
        # With hyphens for multi-word companies
        if ' ' in company_name or len(company_name.split()) > 1:
            hyphenated = normalized.replace('', '-') if '' in normalized else normalized
            for tld in tlds[:3]:  # Only try top TLDs for hyphens
                domains.extend([
                    f"https://{hyphenated}{tld}",
                    f"https://www.{hyphenated}{tld}"
                ])
        
        # Common software company patterns
        if 'software' not in normalized.lower():
            domains.extend([
                f"https://{normalized}software.com",
                f"https://{normalized}app.com"
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_domains = []
        for domain in domains:
            if domain not in seen:
                seen.add(domain)
                unique_domains.append(domain)
        
        return unique_domains[:25]  # Limit to prevent abuse
    
    def _normalize_for_domain(self, company_name: str) -> str:
        """Normalize company name for domain generation"""
        # Convert to lowercase
        normalized = company_name.lower()
        
        # Remove common business suffixes
        suffixes = ['inc', 'inc.', 'llc', 'ltd', 'ltd.', 'corporation', 'corp', 'corp.', 'company', 'co.']
        for suffix in suffixes:
            if normalized.endswith(f' {suffix}'):
                normalized = normalized[:-len(suffix)-1]
        
        # Remove special characters except spaces
        normalized = re.sub(r'[^a-z0-9\s-]', '', normalized)
        
        # Replace spaces with empty string for domains
        normalized = re.sub(r'\s+', '', normalized)
        
        return normalized.strip()
    
    async def _validate_domain(
        self,
        domain: str,
        company_name: str
    ) -> Optional[Dict[str, Any]]:
        """Validate if domain is a legitimate company website"""
        
        try:
            # Parse domain
            parsed = urlparse(domain)
            hostname = parsed.hostname
            
            if not hostname:
                return None
            
            # Check DNS resolution
            try:
                dns.resolver.resolve(hostname, 'A')
            except Exception:
                return None
            
            # Check HTTP response
            session = await self._get_session()
            
            try:
                async with session.get(
                    domain,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=True
                ) as response:
                    
                    if response.status != 200:
                        return None
                    
                    # Get page content
                    content = await response.text()
                    
                    # Validate this is actually the company's website
                    validation_result = self._validate_website_content(
                        content, company_name, str(response.url)
                    )
                    
                    if not validation_result["is_valid"]:
                        return None
                    
                    # Check SSL certificate
                    ssl_valid = self._check_ssl_certificate(response)
                    
                    return {
                        "valid": True,
                        "url": str(response.url),
                        "confidence": validation_result["confidence"],
                        "evidence": validation_result["evidence"],
                        "ssl_valid": ssl_valid,
                        "name_match": validation_result["name_match"],
                        "domain": hostname
                    }
                    
            except Exception as e:
                logger.debug(f"Failed to validate {domain}: {e}")
                return None
                
        except Exception as e:
            logger.debug(f"Domain validation error for {domain}: {e}")
            return None
    
    def _validate_website_content(
        self,
        content: str,
        company_name: str,
        final_url: str
    ) -> Dict[str, Any]:
        """Validate that website content matches the company"""
        
        content_lower = content.lower()
        company_lower = company_name.lower()
        
        evidence = []
        confidence = 0.0
        name_match = False
        
        # Check for exact company name in title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        if title_match and company_lower in title_match.group(1).lower():
            confidence += 0.4
            evidence.append("Company name found in page title")
            name_match = True
        
        # Check for company name in content
        if company_lower in content_lower:
            confidence += 0.3
            evidence.append("Company name found in page content")
            name_match = True
        
        # Check for software/business indicators
        business_indicators = [
            'about us', 'contact us', 'products', 'services', 'solutions',
            'software', 'platform', 'saas', 'enterprise', 'customers'
        ]
        
        found_indicators = [ind for ind in business_indicators if ind in content_lower]
        if found_indicators:
            confidence += min(0.2, len(found_indicators) * 0.05)
            evidence.append(f"Business indicators found: {', '.join(found_indicators[:3])}")
        
        # Check for red flags (parking pages, for sale, etc.)
        red_flags = [
            'domain for sale', 'this domain is for sale', 'parked domain',
            'domain parking', 'buy this domain', 'domain expired'
        ]
        
        if any(flag in content_lower for flag in red_flags):
            confidence = 0.0
            evidence = ["Appears to be a parked or for-sale domain"]
            return {
                "is_valid": False,
                "confidence": confidence,
                "evidence": evidence,
                "name_match": False
            }
        
        # Minimum confidence threshold
        is_valid = confidence >= 0.3 and name_match
        
        return {
            "is_valid": is_valid,
            "confidence": min(1.0, confidence),
            "evidence": evidence,
            "name_match": name_match
        }
    
    def _check_ssl_certificate(self, response: aiohttp.ClientResponse) -> bool:
        """Check if SSL certificate is valid"""
        try:
            # Basic check - if HTTPS worked, SSL is likely valid
            return str(response.url).startswith('https://')
        except Exception:
            return False
    
    def _select_best_domain(self, valid_domains: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best domain from valid candidates"""
        
        # Sort by confidence score, then prefer .com domains
        def domain_score(domain_info: Dict[str, Any]) -> float:
            score = domain_info["confidence"]
            
            # Bonus for .com domains
            if domain_info["url"].endswith('.com') or '.com/' in domain_info["url"]:
                score += 0.1
            
            # Bonus for SSL
            if domain_info["ssl_valid"]:
                score += 0.05
            
            # Bonus for www prefix (more established)
            if '://www.' in domain_info["url"]:
                score += 0.05
            
            return score
        
        best_domain = max(valid_domains, key=domain_score)
        return best_domain
    
    async def _try_search_discovery(
        self,
        company_name: str,
        hints: Dict[str, Any]
    ) -> WebsiteDiscoveryResult:
        """Try to find website using search engines (placeholder)"""
        
        # TODO: Implement Google Custom Search API integration
        # For now, return empty result
        
        logger.debug(f"Search discovery not implemented yet for {company_name}")
        
        return WebsiteDiscoveryResult(
            url=None,
            confidence=0.0,
            evidence=["Search discovery not implemented"],
            discovery_method="search"
        )
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent_checks,
                ssl=False  # We'll validate SSL separately
            )
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def close(self) -> None:
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()