"""
Discovery orchestrator for coordinating company discovery across multiple sources
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ...models.discovery import (
    DiscoveryRequest,
    DiscoveryResult,
    DiscoveryMetadata,
    WebsiteDiscoveryResult,
    LinkedInDiscoveryResult,
    CrunchbaseData,
    GoogleKnowledgeGraphData
)
from .website_discovery import WebsiteDiscoveryService
from .linkedin_discovery import LinkedInDiscoveryService
from .crunchbase_service import CrunchbaseService
from .google_discovery import GoogleDiscoveryService
from .validation_engine import ValidationEngine
from .discovery_cache import DiscoveryCacheService

logger = logging.getLogger(__name__)


class DiscoveryOrchestrator:
    """Orchestrates discovery across multiple sources"""
    
    def __init__(self):
        # Initialize discovery services
        self.website_discovery = WebsiteDiscoveryService()
        self.linkedin_discovery = LinkedInDiscoveryService()
        self.crunchbase_service = CrunchbaseService()
        self.google_discovery = GoogleDiscoveryService()
        self.validation_engine = ValidationEngine()
        self.cache_service = DiscoveryCacheService()
        
        # Discovery configuration
        self.max_parallel_sources = 4
        self.default_timeout = 30
        
        logger.info("Initialized discovery orchestrator")
    
    async def discover_company(
        self, 
        request: DiscoveryRequest
    ) -> DiscoveryResult:
        """Main discovery coordination method"""
        start_time = time.time()
        
        try:
            logger.info(f"Starting discovery for: {request.company_name}")
            
            # Normalize company name
            normalized_name = self._normalize_company_name(request.company_name)
            
            # Check cache first
            cached_result = await self._check_cache(normalized_name)
            if cached_result and not self._is_stale(cached_result):
                logger.info(f"Using cached discovery for {request.company_name}")
                return cached_result
            
            # Initialize result
            result = DiscoveryResult(
                company_name=request.company_name,
                normalized_name=normalized_name,
                discovery_metadata=DiscoveryMetadata()
            )
            
            # Run discovery with timeout
            try:
                async with asyncio.timeout(request.discovery_timeout):
                    await self._run_parallel_discovery(request, result)
            except asyncio.TimeoutError:
                logger.warning(f"Discovery timeout for {request.company_name}")
                result.discovery_metadata.failed_sources["timeout"] = "Discovery exceeded timeout"
            
            # Cross-validate results
            if result.has_sufficient_data:
                validation_result = await self.validation_engine.validate_discovery(result)
                result.cross_validation_score = validation_result.score
                result.validation_conflicts = validation_result.conflicts
            
            # Calculate metadata
            result.discovery_metadata.discovery_duration_seconds = time.time() - start_time
            
            # Cache successful discoveries
            if result.has_sufficient_data:
                await self._cache_result(result)
            
            logger.info(
                f"Discovery completed for {request.company_name} "
                f"in {result.discovery_metadata.discovery_duration_seconds:.1f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Discovery failed for {request.company_name}: {e}")
            # Return partial result with error
            return DiscoveryResult(
                company_name=request.company_name,
                normalized_name=self._normalize_company_name(request.company_name),
                discovery_metadata=DiscoveryMetadata(
                    failed_sources={"orchestrator": str(e)},
                    discovery_duration_seconds=time.time() - start_time
                )
            )
    
    async def _run_parallel_discovery(
        self,
        request: DiscoveryRequest,
        result: DiscoveryResult
    ) -> None:
        """Run discovery tasks in parallel"""
        
        # Create discovery tasks
        tasks = []
        
        # Website discovery (always run)
        if "website" in request.required_sources + request.optional_sources:
            tasks.append(self._discover_website(request, result))
        
        # LinkedIn discovery
        if "linkedin" in request.required_sources + request.optional_sources:
            tasks.append(self._discover_linkedin(request, result))
        
        # Crunchbase discovery
        if "crunchbase" in request.optional_sources:
            tasks.append(self._discover_crunchbase(request, result))
        
        # Google discovery
        if "google_kg" in request.optional_sources:
            tasks.append(self._discover_google(request, result))
        
        # Execute tasks with exception handling
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _discover_website(
        self,
        request: DiscoveryRequest,
        result: DiscoveryResult
    ) -> None:
        """Discover company website"""
        try:
            logger.info(f"Discovering website for {request.company_name}")
            
            website_result = await self.website_discovery.discover_website(
                company_name=request.company_name,
                hints={
                    "industry": request.industry_hint,
                    "location": request.location_hint,
                    "type": request.company_type_hint
                }
            )
            
            if website_result.url:
                result.website_discovery = website_result
                result.discovery_metadata.successful_sources.append("website")
                logger.info(f"Found website: {website_result.url}")
            else:
                result.discovery_metadata.failed_sources["website"] = "No website found"
                
            result.discovery_metadata.total_sources_checked += 1
            
        except Exception as e:
            logger.error(f"Website discovery failed: {e}")
            result.discovery_metadata.failed_sources["website"] = str(e)
    
    async def _discover_linkedin(
        self,
        request: DiscoveryRequest,
        result: DiscoveryResult
    ) -> None:
        """Discover LinkedIn company profile"""
        try:
            logger.info(f"Discovering LinkedIn for {request.company_name}")
            
            linkedin_result = await self.linkedin_discovery.discover_linkedin(
                company_name=request.company_name,
                hints={
                    "industry": request.industry_hint,
                    "location": request.location_hint
                }
            )
            
            if linkedin_result.url:
                result.linkedin_discovery = linkedin_result
                result.discovery_metadata.successful_sources.append("linkedin")
                logger.info(f"Found LinkedIn: {linkedin_result.url}")
            else:
                result.discovery_metadata.failed_sources["linkedin"] = "No LinkedIn profile found"
                
            result.discovery_metadata.total_sources_checked += 1
            
        except Exception as e:
            logger.error(f"LinkedIn discovery failed: {e}")
            result.discovery_metadata.failed_sources["linkedin"] = str(e)
    
    async def _discover_crunchbase(
        self,
        request: DiscoveryRequest,
        result: DiscoveryResult
    ) -> None:
        """Discover Crunchbase company data"""
        try:
            logger.info(f"Discovering Crunchbase for {request.company_name}")
            
            crunchbase_data = await self.crunchbase_service.search_company(
                company_name=request.company_name,
                location=request.location_hint
            )
            
            if crunchbase_data:
                result.crunchbase_data = crunchbase_data
                result.crunchbase_url = f"https://www.crunchbase.com/organization/{crunchbase_data.uuid}"
                result.discovery_metadata.successful_sources.append("crunchbase")
                result.discovery_metadata.api_calls_made["crunchbase"] = 1
                logger.info(f"Found Crunchbase data for {crunchbase_data.name}")
            else:
                result.discovery_metadata.failed_sources["crunchbase"] = "No Crunchbase data found"
                
            result.discovery_metadata.total_sources_checked += 1
            
        except Exception as e:
            logger.error(f"Crunchbase discovery failed: {e}")
            result.discovery_metadata.failed_sources["crunchbase"] = str(e)
    
    async def _discover_google(
        self,
        request: DiscoveryRequest,
        result: DiscoveryResult
    ) -> None:
        """Discover Google Knowledge Graph data"""
        try:
            logger.info(f"Discovering Google data for {request.company_name}")
            
            google_result = await self.google_discovery.discover_google_data(
                company_name=request.company_name
            )
            
            if google_result.knowledge_graph_data:
                result.google_kg_data = google_result.knowledge_graph_data
                result.discovery_metadata.successful_sources.append("google_kg")
                result.discovery_metadata.api_calls_made["google_kg"] = 1
                logger.info(f"Found Google Knowledge Graph data")
            
            if google_result.search_results:
                result.google_search_results = google_result.search_results[:5]
                result.discovery_metadata.api_calls_made["google_search"] = 1
            
            if not google_result.knowledge_graph_data and not google_result.search_results:
                result.discovery_metadata.failed_sources["google"] = "No Google data found"
                
            result.discovery_metadata.total_sources_checked += 1
            
        except Exception as e:
            logger.error(f"Google discovery failed: {e}")
            result.discovery_metadata.failed_sources["google"] = str(e)
    
    def _normalize_company_name(self, company_name: str) -> str:
        """Normalize company name for consistent processing"""
        # Remove common suffixes
        suffixes = ["Inc", "Inc.", "LLC", "Ltd", "Ltd.", "Corporation", "Corp", "Corp."]
        normalized = company_name.strip()
        
        for suffix in suffixes:
            if normalized.endswith(f" {suffix}"):
                normalized = normalized[:-len(suffix)-1]
        
        return normalized.strip()
    
    async def _check_cache(self, normalized_name: str) -> Optional[DiscoveryResult]:
        """Check if discovery is cached"""
        try:
            return await self.cache_service.get_cached_discovery(normalized_name)
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            return None
    
    def _is_stale(self, cached_result: DiscoveryResult) -> bool:
        """Check if cached result is stale (older than 24 hours)"""
        from datetime import timedelta
        age = datetime.utcnow() - cached_result.discovery_timestamp
        return age > timedelta(hours=24)
    
    async def _cache_result(self, result: DiscoveryResult) -> None:
        """Cache successful discovery result"""
        try:
            await self.cache_service.cache_discovery(result)
            result.discovery_metadata.cache_hits["stored"] = True
        except Exception as e:
            logger.warning(f"Failed to cache discovery result: {e}")
    
    async def close(self) -> None:
        """Close all discovery services"""
        try:
            await self.website_discovery.close()
            await self.linkedin_discovery.close()
            await self.crunchbase_service.close()
            await self.google_discovery.close()
            await self.cache_service.close()
        except Exception as e:
            logger.error(f"Error closing discovery services: {e}")