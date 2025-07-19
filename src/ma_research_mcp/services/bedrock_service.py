"""
AWS Bedrock LLM service for M&A Research Assistant
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.config import get_config

logger = logging.getLogger(__name__)


class BedrockLLMService:
    """AWS Bedrock LLM service with Claude and Nova Pro models"""
    
    def __init__(self):
        self.config = get_config()
        self.bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.config.BEDROCK_REGION,
            aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY
        )
        
        self.primary_model = self.config.BEDROCK_PRIMARY_MODEL
        self.fallback_model = self.config.BEDROCK_FALLBACK_MODEL
        
        # Rate limiting
        self.requests_per_minute = self.config.BEDROCK_REQUESTS_PER_MINUTE
        self.tokens_per_minute = self.config.BEDROCK_TOKENS_PER_MINUTE
        self.max_concurrent = self.config.BEDROCK_MAX_CONCURRENT
        
        # Token tracking
        self.total_tokens_used = 0
        self.total_requests_made = 0
        self.last_reset_time = time.time()
        
        logger.info(f"Initialized Bedrock service with primary model: {self.primary_model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_response(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.1,
        system_prompt: Optional[str] = None,
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """Generate response using Bedrock LLM"""
        try:
            model_id = self.fallback_model if use_fallback else self.primary_model
            
            # Check rate limits
            await self._check_rate_limits()
            
            # Prepare request based on model type
            if "claude" in model_id.lower():
                response = await self._call_claude_model(
                    model_id, prompt, max_tokens, temperature, system_prompt
                )
            elif "nova" in model_id.lower():
                response = await self._call_nova_model(
                    model_id, prompt, max_tokens, temperature, system_prompt
                )
            else:
                raise ValueError(f"Unsupported model: {model_id}")
            
            # Track usage
            self.total_requests_made += 1
            
            return {
                "success": True,
                "response": response["content"],
                "model_used": model_id,
                "tokens_used": response.get("tokens_used", 0),
                "stop_reason": response.get("stop_reason", "complete")
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code == 'ThrottlingException' and not use_fallback:
                logger.warning("Primary model throttled, trying fallback")
                return await self.generate_response(
                    prompt, max_tokens, temperature, system_prompt, use_fallback=True
                )
            
            logger.error(f"Bedrock API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": error_code
            }
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _call_claude_model(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Call Claude model via Bedrock"""
        messages = [{"role": "user", "content": prompt}]
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            body["system"] = system_prompt
        
        response = self.bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        
        return {
            "content": response_body["content"][0]["text"],
            "tokens_used": response_body.get("usage", {}).get("input_tokens", 0) + 
                          response_body.get("usage", {}).get("output_tokens", 0),
            "stop_reason": response_body.get("stop_reason", "complete")
        }
    
    async def _call_nova_model(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Call Nova model via Bedrock"""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        body = {
            "inputText": full_prompt,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": temperature,
                "topP": 0.9
            }
        }
        
        response = self.bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        
        return {
            "content": response_body["results"][0]["outputText"],
            "tokens_used": response_body.get("inputTextTokenCount", 0) + 
                          len(response_body["results"][0]["outputText"].split()),
            "stop_reason": response_body["results"][0].get("completionReason", "complete")
        }
    
    async def _check_rate_limits(self) -> None:
        """Check and enforce rate limits"""
        current_time = time.time()
        
        # Reset counters every minute
        if current_time - self.last_reset_time >= 60:
            self.total_tokens_used = 0
            self.total_requests_made = 0
            self.last_reset_time = current_time
        
        # Check limits
        if self.total_requests_made >= self.requests_per_minute:
            sleep_time = 60 - (current_time - self.last_reset_time)
            if sleep_time > 0:
                logger.warning(f"Rate limit hit, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self.total_tokens_used = 0
                self.total_requests_made = 0
                self.last_reset_time = time.time()
    
    async def score_dimension(
        self,
        dimension_name: str,
        dimension_description: str,
        scoring_criteria: Dict[str, str],
        company_data: Dict[str, Any],
        min_score: float = 0.0,
        max_score: float = 10.0
    ) -> Dict[str, Any]:
        """Score a specific dimension using LLM"""
        
        system_prompt = f"""You are an expert M&A analyst specializing in software company evaluation.
Your task is to score companies on specific dimensions for acquisition assessment.

IMPORTANT: You must provide your response as valid JSON with the following structure:
{{
    "score": <numeric_score>,
    "confidence": <confidence_0_to_1>,
    "evidence": ["<evidence_point_1>", "<evidence_point_2>", ...],
    "reasoning": "<detailed_reasoning>",
    "data_sources": ["<source_1>", "<source_2>", ...]
}}

Dimension: {dimension_name}
Description: {dimension_description}
Score Range: {min_score} to {max_score}

Scoring Criteria:
{json.dumps(scoring_criteria, indent=2)}"""

        prompt = f"""Based on the following company data, score this company on the "{dimension_name}" dimension.

Company Data:
{json.dumps(company_data, indent=2, default=str)}

Provide your analysis as valid JSON following the required structure."""

        try:
            response = await self.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=1500,
                temperature=0.1
            )
            
            if not response["success"]:
                return response
            
            # Parse JSON response
            try:
                result = json.loads(response["response"])
                
                # Validate required fields
                required_fields = ["score", "confidence", "evidence", "reasoning", "data_sources"]
                for field in required_fields:
                    if field not in result:
                        result[field] = []
                
                # Validate score range
                score = float(result["score"])
                if score < min_score or score > max_score:
                    logger.warning(f"Score {score} outside range [{min_score}, {max_score}], clamping")
                    result["score"] = max(min_score, min(max_score, score))
                
                # Add metadata
                result["model_used"] = response["model_used"]
                result["tokens_used"] = response["tokens_used"]
                
                return {
                    "success": True,
                    "dimension_score": result
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Response: {response['response'][:500]}...")
                
                return {
                    "success": False,
                    "error": "Invalid JSON response from LLM",
                    "raw_response": response["response"]
                }
                
        except Exception as e:
            logger.error(f"Error scoring dimension {dimension_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_investment_thesis(
        self,
        company_data: Dict[str, Any],
        analysis_results: Dict[str, Any],
        thesis_type: str = "standard"
    ) -> Dict[str, Any]:
        """Generate AI-powered investment thesis"""
        
        system_prompt = """You are a senior M&A analyst at a leading software company.
Your expertise is in evaluating vertical market software companies for acquisition.
Generate a comprehensive investment thesis based on the provided company data and analysis.

IMPORTANT: Provide your response as valid JSON with this structure:
{
    "strategic_rationale": "<why this acquisition makes strategic sense>",
    "vms_alignment_score": <score_0_to_10>,
    "financial_profile": {
        "revenue_model": "<assessment>",
        "growth_trajectory": "<assessment>",
        "profitability": "<assessment>",
        "pricing_power": "<assessment>"
    },
    "execution_factors": ["<factor_1>", "<factor_2>", ...],
    "integration_complexity": "<low/medium/high with reasoning>",
    "risk_assessment": {
        "market_risks": ["<risk_1>", "<risk_2>", ...],
        "technical_risks": ["<risk_1>", "<risk_2>", ...],
        "execution_risks": ["<risk_1>", "<risk_2>", ...]
    },
    "mitigation_strategies": ["<strategy_1>", "<strategy_2>", ...],
    "recommendation": "<acquire/pass with reasoning>",
    "confidence_level": <confidence_0_to_1>
}"""

        prompt = f"""Generate an investment thesis for this software company.

Company Data:
{json.dumps(company_data, indent=2, default=str)}

Analysis Results:
{json.dumps(analysis_results, indent=2, default=str)}

Thesis Type: {thesis_type}

Focus on vertical market software potential, strategic fit, and acquisition value."""

        try:
            response = await self.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            if not response["success"]:
                return response
            
            try:
                thesis = json.loads(response["response"])
                thesis["generated_at"] = time.time()
                thesis["thesis_type"] = thesis_type
                thesis["model_used"] = response["model_used"]
                
                return {
                    "success": True,
                    "investment_thesis": thesis
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse investment thesis JSON: {e}")
                return {
                    "success": False,
                    "error": "Invalid JSON response for investment thesis"
                }
                
        except Exception as e:
            logger.error(f"Error generating investment thesis: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_tokens_used": self.total_tokens_used,
            "total_requests_made": self.total_requests_made,
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model,
            "rate_limits": {
                "requests_per_minute": self.requests_per_minute,
                "tokens_per_minute": self.tokens_per_minute
            }
        }