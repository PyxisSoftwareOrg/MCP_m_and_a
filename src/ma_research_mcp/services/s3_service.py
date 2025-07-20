"""
S3 storage service for M&A Research Assistant
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..core.config import get_config
from ..models import AnalysisResult, CompanyList, ScoringSystem

logger = logging.getLogger(__name__)


class S3Service:
    """S3 storage service with structured organization"""
    
    def __init__(self):
        self.config = get_config()
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY,
                region_name=self.config.AWS_REGION
            )
            self.bucket_name = self.config.S3_BUCKET_NAME
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        
        # Test bucket access (skip in development mode)
        if not self._is_development_mode():
            self._verify_bucket_access()
        else:
            logger.warning("Development mode: Skipping S3 bucket verification")
    
    def _verify_bucket_access(self) -> None:
        """Verify bucket exists and is accessible"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"Bucket {self.bucket_name} not found")
            elif error_code == '403':
                logger.error(f"Access denied to bucket {self.bucket_name}")
            else:
                logger.error(f"Error accessing bucket: {e}")
            raise
    
    def _is_development_mode(self) -> bool:
        """Check if running in development mode"""
        # Check for development indicators
        return (
            self.config.AWS_ACCESS_KEY_ID == "test" or
            self.config.S3_BUCKET_NAME in ["test", "ma-research-bucket"] or
            hasattr(self.config, 'DEVELOPMENT_MODE') and self.config.DEVELOPMENT_MODE
        )
    
    def _sanitize_company_name(self, company_name: str) -> str:
        """Sanitize company name for use as S3 key"""
        # Replace special characters with hyphens, remove multiple hyphens
        sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '-', company_name.lower())
        sanitized = re.sub(r'-+', '-', sanitized)
        return sanitized.strip('-')
    
    def _generate_timestamp(self) -> str:
        """Generate ISO 8601 timestamp"""
        return datetime.utcnow().isoformat() + 'Z'
    
    def _get_company_base_path(self, company_name: str) -> str:
        """Get base S3 path for company"""
        sanitized_name = self._sanitize_company_name(company_name)
        return f"companies/{sanitized_name}"
    
    def _get_analysis_path(self, company_name: str, timestamp: str) -> str:
        """Get S3 path for specific analysis"""
        base_path = self._get_company_base_path(company_name)
        return f"{base_path}/{timestamp}"
    
    async def save_analysis_result(
        self, 
        analysis: AnalysisResult,
        raw_website_content: Optional[Dict[str, Any]] = None,
        linkedin_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save complete analysis result to S3"""
        try:
            analysis_path = self._get_analysis_path(
                analysis.company_name, 
                analysis.analysis_timestamp
            )
            
            # Save main analysis
            await self._save_json_object(
                f"{analysis_path}/analysis.json",
                analysis.dict()
            )
            
            # Save raw data if provided
            if raw_website_content:
                await self._save_json_object(
                    f"{analysis_path}/raw_website_content.json",
                    raw_website_content
                )
            
            if linkedin_data:
                await self._save_json_object(
                    f"{analysis_path}/linkedin_data.json", 
                    linkedin_data
                )
            
            # Save metadata
            metadata = {
                "company_name": analysis.company_name,
                "analysis_timestamp": analysis.analysis_timestamp,
                "overall_score": analysis.overall_score,
                "automated_tier": analysis.automated_tier,
                "effective_tier": analysis.effective_tier,
                "is_qualified": analysis.qualification_result.is_qualified,
                "created_at": self._generate_timestamp()
            }
            await self._save_json_object(
                f"{analysis_path}/metadata.json",
                metadata
            )
            
            # Update latest analysis pointer
            await self._update_latest_analysis(analysis.company_name, analysis_path)
            
            # Update company index
            await self._update_company_index(analysis)
            
            return f"s3://{self.bucket_name}/{analysis_path}"
            
        except Exception as e:
            logger.error(f"Failed to save analysis for {analysis.company_name}: {e}")
            raise
    
    async def _save_json_object(self, s3_key: str, data: Dict[str, Any]) -> None:
        """Save JSON object to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(data, indent=2, default=str),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            logger.debug(f"Saved object to s3://{self.bucket_name}/{s3_key}")
        except ClientError as e:
            logger.error(f"Failed to save object {s3_key}: {e}")
            raise
    
    async def _update_latest_analysis(self, company_name: str, analysis_path: str) -> None:
        """Update latest analysis pointer"""
        base_path = self._get_company_base_path(company_name)
        latest_path = f"{base_path}/latest"
        
        latest_data = {
            "company_name": company_name,
            "latest_analysis_path": analysis_path,
            "updated_at": self._generate_timestamp()
        }
        
        await self._save_json_object(f"{latest_path}/pointer.json", latest_data)
    
    async def _update_company_index(self, analysis: AnalysisResult) -> None:
        """Update global company index"""
        try:
            # Get existing index
            companies_index = await self._load_json_object("_index/companies_list.json") or []
            
            # Update or add company entry
            company_entry = {
                "company_name": analysis.company_name,
                "sanitized_name": self._sanitize_company_name(analysis.company_name),
                "website_url": analysis.website_url,
                "linkedin_url": analysis.linkedin_url,
                "latest_analysis": analysis.analysis_timestamp,
                "overall_score": analysis.overall_score,
                "automated_tier": analysis.automated_tier,
                "effective_tier": analysis.effective_tier,
                "is_qualified": analysis.qualification_result.is_qualified,
                "list_type": analysis.list_type,
                "last_updated": self._generate_timestamp()
            }
            
            # Remove existing entry if present
            companies_index = [c for c in companies_index if c.get("company_name") != analysis.company_name]
            companies_index.append(company_entry)
            
            # Sort by score descending
            companies_index.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
            
            await self._save_json_object("_index/companies_list.json", companies_index)
            
        except Exception as e:
            logger.warning(f"Failed to update company index: {e}")
    
    async def _load_json_object(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """Load JSON object from S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            logger.error(f"Failed to load object {s3_key}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {s3_key}: {e}")
            return None
    
    async def get_analysis_result(
        self, 
        company_name: str, 
        timestamp: Optional[str] = None
    ) -> Optional[AnalysisResult]:
        """Get analysis result for company"""
        try:
            if timestamp:
                analysis_path = self._get_analysis_path(company_name, timestamp)
            else:
                # Get latest analysis
                base_path = self._get_company_base_path(company_name)
                latest_data = await self._load_json_object(f"{base_path}/latest/pointer.json")
                if not latest_data:
                    return None
                analysis_path = latest_data["latest_analysis_path"]
            
            # Load analysis data
            analysis_data = await self._load_json_object(f"{analysis_path}/analysis.json")
            if not analysis_data:
                return None
            
            return AnalysisResult(**analysis_data)
            
        except Exception as e:
            logger.error(f"Failed to get analysis for {company_name}: {e}")
            return None
    
    async def get_company_history(
        self, 
        company_name: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get analysis history for company"""
        try:
            base_path = self._get_company_base_path(company_name)
            
            # List all analysis timestamps
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"{base_path}/",
                Delimiter='/'
            )
            
            timestamps = []
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    folder_name = prefix['Prefix'].split('/')[-2]
                    if folder_name != 'latest' and self._is_iso_timestamp(folder_name):
                        timestamps.append(folder_name)
            
            # Sort by timestamp descending and limit
            timestamps.sort(reverse=True)
            timestamps = timestamps[:limit]
            
            # Load metadata for each analysis
            history = []
            for timestamp in timestamps:
                metadata = await self._load_json_object(
                    f"{base_path}/{timestamp}/metadata.json"
                )
                if metadata:
                    history.append(metadata)
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get history for {company_name}: {e}")
            return []
    
    def _is_iso_timestamp(self, timestamp: str) -> bool:
        """Check if string is ISO 8601 timestamp"""
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return True
        except ValueError:
            return False
    
    async def search_companies(
        self, 
        criteria: Dict[str, Any],
        sort_by: str = "overall_score",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search companies by criteria"""
        try:
            companies_index = await self._load_json_object("_index/companies_list.json") or []
            
            # Apply filters
            filtered = []
            for company in companies_index:
                if self._matches_criteria(company, criteria):
                    filtered.append(company)
            
            # Sort
            if sort_by in ["overall_score", "last_updated"]:
                reverse = True
            else:
                reverse = False
            
            filtered.sort(
                key=lambda x: x.get(sort_by, 0), 
                reverse=reverse
            )
            
            return filtered[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search companies: {e}")
            return []
    
    def _matches_criteria(self, company: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """Check if company matches search criteria"""
        for key, value in criteria.items():
            if key == "min_score":
                if company.get("overall_score", 0) < value:
                    return False
            elif key == "max_score":
                if company.get("overall_score", 0) > value:
                    return False
            elif key == "tier":
                if company.get("effective_tier") != value:
                    return False
            elif key == "qualified":
                if company.get("is_qualified") != value:
                    return False
            elif key == "list_type":
                if company.get("list_type") != value:
                    return False
        return True
    
    async def save_scoring_system(self, scoring_system: ScoringSystem) -> str:
        """Save scoring system configuration"""
        try:
            s3_key = f"scoring_systems/{scoring_system.system_id}/configuration.json"
            await self._save_json_object(s3_key, scoring_system.dict())
            
            # Update registry
            await self._update_scoring_system_registry(scoring_system)
            
            return f"s3://{self.bucket_name}/{s3_key}"
            
        except Exception as e:
            logger.error(f"Failed to save scoring system {scoring_system.system_id}: {e}")
            raise
    
    async def _update_scoring_system_registry(self, scoring_system: ScoringSystem) -> None:
        """Update scoring system registry"""
        try:
            registry = await self._load_json_object("scoring_systems/_registry.json") or []
            
            # Remove existing entry
            registry = [s for s in registry if s.get("system_id") != scoring_system.system_id]
            
            # Add new entry
            registry_entry = {
                "system_id": scoring_system.system_id,
                "system_name": scoring_system.system_name,
                "owner": scoring_system.owner,
                "is_active": scoring_system.is_active,
                "is_default": scoring_system.is_default,
                "created_at": scoring_system.created_at,
                "updated_at": scoring_system.updated_at
            }
            registry.append(registry_entry)
            
            await self._save_json_object("scoring_systems/_registry.json", registry)
            
        except Exception as e:
            logger.warning(f"Failed to update scoring system registry: {e}")
    
    async def get_scoring_system(self, system_id: str) -> Optional[ScoringSystem]:
        """Get scoring system by ID"""
        try:
            system_data = await self._load_json_object(
                f"scoring_systems/{system_id}/configuration.json"
            )
            if system_data:
                return ScoringSystem(**system_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get scoring system {system_id}: {e}")
            return None
    
    async def generate_presigned_url(
        self, 
        s3_key: str, 
        expiration: int = 3600
    ) -> str:
        """Generate presigned URL for S3 object"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise