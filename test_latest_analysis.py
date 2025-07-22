#!/usr/bin/env python3
"""
Test script to call the get_latest_analysis tool
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ma_research_mcp.services.s3_service import S3Service


async def test_get_latest_analysis():
    """Test the get_latest_analysis functionality"""
    company_name = "Whip Around"
    
    try:
        print(f"Testing get_latest_analysis for: {company_name}")
        
        # Initialize S3 service
        s3_service = S3Service()
        
        # Get the latest analysis
        latest_analysis = await s3_service.get_analysis_result(company_name)
        
        if latest_analysis:
            print(f"\n=== LATEST ANALYSIS FOR {company_name.upper()} ===")
            
            # Basic company information
            print(f"\nCOMPANY INFORMATION:")
            print(f"Company Name: {latest_analysis.company_name}")
            print(f"Analysis Timestamp: {latest_analysis.analysis_timestamp}")
            print(f"Website URL: {latest_analysis.website_url}")
            print(f"LinkedIn URL: {latest_analysis.linkedin_url}")
            print(f"List Type: {latest_analysis.list_type}")
            
            # Qualification results
            print(f"\nQUALIFICATION RESULTS:")
            print(f"Is Qualified: {latest_analysis.qualification_result.is_qualified}")
            print(f"Qualification Score: {latest_analysis.qualification_result.qualification_score:.2f}")
            print(f"Q1 Horizontal vs Vertical: {latest_analysis.qualification_result.q1_horizontal_vs_vertical}")
            print(f"Q2 Point vs Suite: {latest_analysis.qualification_result.q2_point_vs_suite}")
            print(f"Q3 Mission Critical: {latest_analysis.qualification_result.q3_mission_critical}")
            print(f"Q4 OPM vs Private: {latest_analysis.qualification_result.q4_opm_vs_private}")
            print(f"Q5 ARPU Level: {latest_analysis.qualification_result.q5_arpu_level}")
            
            # Filtering results
            print(f"\nFILTERING RESULTS:")
            print(f"Passed Geographic Filter: {latest_analysis.filtering_result.passed_geographic_filter}")
            print(f"Passed Business Model Filter: {latest_analysis.filtering_result.passed_business_model_filter}")
            print(f"Passed Size/Maturity Filter: {latest_analysis.filtering_result.passed_size_maturity_filter}")
            print(f"Overall Filter Result: {latest_analysis.filtering_result.overall_filter_result}")
            print(f"Geographic Region: {latest_analysis.filtering_result.geographic_region}")
            print(f"Business Model Type: {latest_analysis.filtering_result.business_model_type}")
            
            # Scoring results
            print(f"\nSCORING RESULTS:")
            print(f"Overall Score: {latest_analysis.overall_score:.2f}")
            
            # Individual dimension scores
            print(f"\nDIMENSION SCORES:")
            for dimension_name, score_data in latest_analysis.default_scores.items():
                print(f"  {dimension_name}:")
                print(f"    Score: {score_data.score:.2f}")
                print(f"    Confidence: {score_data.confidence:.2f}")
                print(f"    Reasoning: {score_data.reasoning}")
            
            # Tier information
            print(f"\nTIER INFORMATION:")
            print(f"Automated Tier: {latest_analysis.automated_tier}")
            print(f"Manual Tier Override: {latest_analysis.manual_tier_override}")
            print(f"Effective Tier: {latest_analysis.effective_tier}")
            
            # Analysis outputs
            print(f"\nANALYSIS OUTPUTS:")
            print(f"Recommendation: {latest_analysis.recommendation}")
            print(f"Key Strengths: {latest_analysis.key_strengths}")
            print(f"Key Concerns: {latest_analysis.key_concerns}")
            
            # Investment thesis (if available)
            if latest_analysis.investment_thesis:
                print(f"\nINVESTMENT THESIS:")
                print(f"Thesis Type: {latest_analysis.investment_thesis.thesis_type}")
                print(f"Strategic Rationale: {latest_analysis.investment_thesis.strategic_rationale}")
                print(f"VMS Alignment Score: {latest_analysis.investment_thesis.vms_alignment_score:.2f}")
                print(f"Growth Trajectory: {latest_analysis.investment_thesis.growth_trajectory}")
                print(f"Recommendation: {latest_analysis.investment_thesis.recommendation}")
                print(f"Confidence Level: {latest_analysis.investment_thesis.confidence_level:.2f}")
            
            # Metadata
            print(f"\nMETADATA:")
            print(f"Analysis ID: {latest_analysis.metadata.analysis_id}")
            print(f"Created At: {latest_analysis.metadata.created_at}")
            print(f"Duration (seconds): {latest_analysis.metadata.analysis_duration_seconds:.2f}")
            print(f"Bedrock Tokens Used: {latest_analysis.metadata.bedrock_tokens_used}")
            print(f"Bedrock Requests Made: {latest_analysis.metadata.bedrock_requests_made}")
            print(f"Pages Scraped: {latest_analysis.metadata.pages_scraped}")
            print(f"Data Sources Used: {latest_analysis.metadata.data_sources_used}")
            print(f"Errors Encountered: {latest_analysis.metadata.errors_encountered}")
            print(f"Cost Estimate USD: ${latest_analysis.metadata.cost_estimate_usd:.2f}")
            
        else:
            print(f"No analysis found for company: {company_name}")
            
    except Exception as e:
        print(f"Error retrieving latest analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_get_latest_analysis())