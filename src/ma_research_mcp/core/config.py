"""
Configuration management for M&A Research Assistant
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class Config(BaseSettings):
    """Application configuration"""
    
    model_config = ConfigDict(env_file=".env", case_sensitive=True)
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID: str = Field(...)
    AWS_SECRET_ACCESS_KEY: str = Field(...)
    AWS_REGION: str = Field("us-east-1")
    S3_BUCKET_NAME: str = Field(...)
    
    # AWS Bedrock Configuration
    BEDROCK_REGION: str = Field("us-east-1")
    BEDROCK_PRIMARY_MODEL: str = Field("us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    BEDROCK_FALLBACK_MODEL: str = Field("amazon.nova-pro-v1:0")
    
    # API Keys
    APIFY_API_TOKEN: str = Field(...)
    
    # MCP Configuration
    MCP_SERVER_NAME: str = Field("ma-research-assistant")
    MCP_SERVER_VERSION: str = Field("1.0.0")
    
    # Feature Flags
    ENABLE_CACHING: bool = Field(True)
    MAX_PARALLEL_ANALYSES: int = Field(5)
    
    # Lead Qualification Thresholds
    QUALIFICATION_MINIMUM_SCORE: float = Field(7.0)
    TIER_VIP_THRESHOLD: float = Field(9.0)
    TIER_HIGH_THRESHOLD: float = Field(7.0)
    TIER_MEDIUM_THRESHOLD: float = Field(5.0)
    
    # Rate Limiting
    BEDROCK_REQUESTS_PER_MINUTE: int = Field(100)
    BEDROCK_TOKENS_PER_MINUTE: int = Field(200000)
    BEDROCK_MAX_CONCURRENT: int = Field(10)
    
    APIFY_REQUESTS_PER_HOUR: int = Field(100)
    
    WEB_SCRAPING_REQUESTS_PER_SECOND: int = Field(1)
    WEB_SCRAPING_CONCURRENT_DOMAINS: int = Field(5)
    
    # Resource Limits
    MAX_MEMORY_PER_ANALYSIS: str = Field("512MB")
    MAX_WEBSITE_CONTENT_SIZE: str = Field("10MB")
    MAX_PAGES_PER_COMPANY: int = Field(10)
    MAX_ANALYSIS_TIME: int = Field(300)
    MAX_RETRY_ATTEMPTS: int = Field(3)
    
    # Cache Configuration
    CACHE_WEBSITE_CONTENT_HOURS: int = Field(24)
    CACHE_LINKEDIN_DATA_DAYS: int = Field(7)
    CACHE_PAID_API_DAYS: int = Field(30)
    
    # Security
    ENCRYPT_SENSITIVE_DATA: bool = Field(True)
    AUDIT_ALL_OPERATIONS: bool = Field(True)
    REQUIRE_MFA_FOR_EXPORTS: bool = Field(True)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Reload configuration from environment"""
    global _config
    _config = Config()
    return _config