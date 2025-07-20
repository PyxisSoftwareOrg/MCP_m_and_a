"""
Discovery tools for automated company discovery
"""

import logging
from typing import Any, Dict, Optional

from ..models.discovery import DiscoveryRequest
from ..services.discovery import DiscoveryOrchestrator

logger = logging.getLogger(__name__)

# Initialize discovery orchestrator
discovery_orchestrator = DiscoveryOrchestrator()


async def discover_company_sources(
    company_name: str,
    industry_hint: Optional[str] = None,
    location_hint: Optional[str] = None,
    company_type_hint: Optional[str] = None,
    discovery_timeout: int = 30,
    required_sources: Optional[list] = None,
    optional_sources: Optional[list] = None
) -> Dict[str, Any]:
    """
    Automatically discover company website, LinkedIn profile, and other data sources
    
    Args:
        company_name: Name of the company to discover
        industry_hint: Optional industry hint (e.g., "software", "saas")
        location_hint: Optional location hint (e.g., "United States", "UK")
        company_type_hint: Optional company type hint (e.g., "software", "saas")
        discovery_timeout: Timeout in seconds for discovery process
        required_sources: List of required sources ["website", "linkedin"]
        optional_sources: List of optional sources ["crunchbase", "google_kg"]
    
    Returns:
        Dictionary with discovery results including found URLs and metadata
    """
    
    try:
        logger.info(f"Starting discovery for company: {company_name}")
        
        # Set defaults
        if required_sources is None:
            required_sources = ["website", "linkedin"]
        if optional_sources is None:
            optional_sources = ["crunchbase", "google_kg"]
        
        # Create discovery request
        request = DiscoveryRequest(
            company_name=company_name,
            industry_hint=industry_hint,
            location_hint=location_hint,
            company_type_hint=company_type_hint,
            discovery_timeout=discovery_timeout,
            required_sources=required_sources,
            optional_sources=optional_sources
        )
        
        # Run discovery
        discovery_result = await discovery_orchestrator.discover_company(request)
        
        # Format response
        response = {
            "success": True,
            "company_name": discovery_result.company_name,
            "normalized_name": discovery_result.normalized_name,
            "discovery_timestamp": discovery_result.discovery_timestamp.isoformat(),
            
            # Discovered URLs
            "website_url": discovery_result.website_url,
            "linkedin_url": discovery_result.linkedin_url,
            "crunchbase_url": discovery_result.crunchbase_url,
            
            # Confidence scores
            "website_confidence": discovery_result.website_discovery.confidence if discovery_result.website_discovery else 0.0,
            "linkedin_confidence": discovery_result.linkedin_discovery.confidence if discovery_result.linkedin_discovery else 0.0,
            "cross_validation_score": discovery_result.cross_validation_score,
            
            # Additional data
            "has_sufficient_data": discovery_result.has_sufficient_data,
            "discovery_metadata": {
                "sources_checked": discovery_result.discovery_metadata.total_sources_checked,
                "successful_sources": discovery_result.discovery_metadata.successful_sources,
                "failed_sources": discovery_result.discovery_metadata.failed_sources,
                "duration_seconds": discovery_result.discovery_metadata.discovery_duration_seconds,
                "api_calls_made": discovery_result.discovery_metadata.api_calls_made,
                "estimated_cost_usd": discovery_result.discovery_metadata.estimated_cost_usd
            }
        }
        
        # Add detailed results if found
        if discovery_result.website_discovery:
            response["website_details"] = {
                "evidence": discovery_result.website_discovery.evidence,
                "domain_verified": discovery_result.website_discovery.domain_verified,
                "ssl_valid": discovery_result.website_discovery.ssl_valid,
                "company_name_match": discovery_result.website_discovery.company_name_match,
                "discovery_method": discovery_result.website_discovery.discovery_method
            }
        
        if discovery_result.linkedin_discovery:
            response["linkedin_details"] = {
                "company_id": discovery_result.linkedin_discovery.company_id,
                "employee_count": discovery_result.linkedin_discovery.employee_count,
                "employee_range": discovery_result.linkedin_discovery.employee_range,
                "industry": discovery_result.linkedin_discovery.industry,
                "headquarters": discovery_result.linkedin_discovery.headquarters,
                "verified_badge": discovery_result.linkedin_discovery.verified_badge
            }
        
        if discovery_result.crunchbase_data:
            response["crunchbase_details"] = {
                "uuid": discovery_result.crunchbase_data.uuid,
                "name": discovery_result.crunchbase_data.name,
                "description": discovery_result.crunchbase_data.description,
                "founded_year": discovery_result.crunchbase_data.founded_year,
                "employee_range": discovery_result.crunchbase_data.employee_range,
                "total_funding_usd": discovery_result.crunchbase_data.total_funding_usd,
                "categories": discovery_result.crunchbase_data.categories
            }
        
        if discovery_result.google_kg_data:
            response["google_kg_details"] = {
                "entity_id": discovery_result.google_kg_data.entity_id,
                "description": discovery_result.google_kg_data.description,
                "types": discovery_result.google_kg_data.types,
                "attributes": discovery_result.google_kg_data.attributes
            }
        
        # Add validation conflicts if any
        if discovery_result.validation_conflicts:
            response["validation_conflicts"] = [
                {
                    "field": conflict.field,
                    "sources": conflict.sources,
                    "severity": conflict.severity,
                    "resolution": conflict.resolution
                }
                for conflict in discovery_result.validation_conflicts
            ]
        
        logger.info(
            f"Discovery completed for {company_name}. "
            f"Found: Website={bool(discovery_result.website_url)}, "
            f"LinkedIn={bool(discovery_result.linkedin_url)}, "
            f"Crunchbase={bool(discovery_result.crunchbase_data)}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Discovery failed for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "company_name": company_name,
            "website_url": None,
            "linkedin_url": None,
            "crunchbase_url": None,
            "has_sufficient_data": False
        }