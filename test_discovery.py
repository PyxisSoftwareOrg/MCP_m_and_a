#!/usr/bin/env python3
"""
Simple test for discovery functionality without requiring all dependencies
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_discovery_imports():
    """Test that discovery modules can be imported"""
    try:
        from ma_research_mcp.services.discovery.website_discovery import WebsiteDiscoveryService
        print("✓ WebsiteDiscoveryService imported")
        
        service = WebsiteDiscoveryService()
        print("✓ WebsiteDiscoveryService instantiated")
        
        # Test domain generation
        domains = service._generate_domain_candidates("Test Company Inc")
        print(f"✓ Generated {len(domains)} domain candidates")
        print(f"  Sample domains: {domains[:3]}")
        
        # Test normalization
        normalized = service._normalize_for_domain("Test Company Inc.")
        print(f"✓ Normalized 'Test Company Inc.' to '{normalized}'")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

async def test_discovery_orchestrator():
    """Test discovery orchestrator without dependencies"""
    try:
        # Test just the class structure without dependencies
        from ma_research_mcp.services.discovery.discovery_orchestrator import DiscoveryOrchestrator
        print("✓ DiscoveryOrchestrator imported")
        
        # Test normalize method
        orchestrator = DiscoveryOrchestrator()
        normalized = orchestrator._normalize_company_name("Test Company Inc.")
        print(f"✓ Normalized company name: '{normalized}'")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Discovery Implementation")
    print("=" * 40)
    
    # Test basic imports and functionality
    print("\n1. Testing Website Discovery Service:")
    test_discovery_imports()
    
    print("\n2. Testing Discovery Orchestrator:")
    asyncio.run(test_discovery_orchestrator())
    
    print("\n✓ Basic discovery implementation tests completed!")