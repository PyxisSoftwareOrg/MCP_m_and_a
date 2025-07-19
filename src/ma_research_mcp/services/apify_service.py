"""
Apify API service for LinkedIn company data extraction
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.config import get_config

logger = logging.getLogger(__name__)


class ApifyService:
    """Apify API service for LinkedIn company data"""
    
    def __init__(self):
        self.config = get_config()
        self.api_token = self.config.APIFY_API_TOKEN
        self.base_url = "https://api.apify.com/v2"
        
        # Actor configuration
        self.linkedin_actor_id = "linkedin-company-scraper"
        self.timeout_secs = 300
        self.memory_mbytes = 256
        self.max_retries = 3
        
        # Rate limiting
        self.requests_per_hour = self.config.APIFY_REQUESTS_PER_HOUR
        self.last_request_time = 0
        self.request_count = 0
        self.hour_start = time.time()
        
        self.session = None
        
        logger.info("Initialized Apify service")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=600)  # 10 minutes for runs
            )
        return self.session
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _check_rate_limits(self) -> None:
        """Check and enforce rate limits"""
        current_time = time.time()
        
        # Reset counter every hour
        if current_time - self.hour_start >= 3600:
            self.request_count = 0
            self.hour_start = current_time
        
        # Check if we've hit the hourly limit
        if self.request_count >= self.requests_per_hour:
            sleep_time = 3600 - (current_time - self.hour_start)
            if sleep_time > 0:
                logger.warning(f"Apify rate limit hit, sleeping {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
                self.request_count = 0
                self.hour_start = time.time()
        
        # Minimum time between requests (1 request per minute for safety)
        if current_time - self.last_request_time < 60:
            sleep_time = 60 - (current_time - self.last_request_time)
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _run_actor(
        self,
        actor_id: str,
        input_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Run Apify actor and wait for completion"""
        try:
            await self._check_rate_limits()
            
            session = await self._get_session()
            
            # Start actor run
            run_url = f"{self.base_url}/acts/{actor_id}/runs"
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            run_data = {
                'timeout': self.timeout_secs,
                'memory': self.memory_mbytes,
                'build': 'latest'
            }
            
            logger.info(f"Starting Apify actor run: {actor_id}")
            
            async with session.post(run_url, json=run_data, headers=headers) as response:
                if response.status != 201:
                    error_text = await response.text()
                    logger.error(f"Failed to start actor run: {response.status} - {error_text}")
                    return None
                
                run_info = await response.json()
                run_id = run_info['data']['id']
            
            # Set input data
            input_url = f"{self.base_url}/actor-runs/{run_id}/input"
            async with session.put(input_url, json=input_data, headers=headers) as response:
                if response.status not in [200, 201]:
                    logger.error(f"Failed to set input data: {response.status}")
                    return None
            
            # Wait for completion
            logger.info(f"Waiting for actor run {run_id} to complete...")
            result = await self._wait_for_completion(run_id)
            
            if result:
                logger.info(f"Actor run {run_id} completed successfully")
                return result
            else:
                logger.error(f"Actor run {run_id} failed or timed out")
                return None
                
        except Exception as e:
            logger.error(f"Error running Apify actor {actor_id}: {e}")
            return None
    
    async def _wait_for_completion(
        self,
        run_id: str,
        max_wait_time: int = 600
    ) -> Optional[Dict[str, Any]]:
        """Wait for actor run to complete and return results"""
        try:
            session = await self._get_session()
            headers = {'Authorization': f'Bearer {self.api_token}'}
            
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                # Check run status
                status_url = f"{self.base_url}/actor-runs/{run_id}"
                async with session.get(status_url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get run status: {response.status}")
                        return None
                    
                    run_info = await response.json()
                    status = run_info['data']['status']
                    
                    if status == 'SUCCEEDED':
                        # Get results
                        return await self._get_run_results(run_id)
                    elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                        logger.error(f"Actor run {run_id} failed with status: {status}")
                        return None
                    elif status in ['READY', 'RUNNING']:
                        # Still running, wait and check again
                        await asyncio.sleep(10)
                    else:
                        logger.warning(f"Unknown run status: {status}")
                        await asyncio.sleep(10)
            
            logger.error(f"Actor run {run_id} timed out after {max_wait_time}s")
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for actor run {run_id}: {e}")
            return None
    
    async def _get_run_results(self, run_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get results from completed actor run"""
        try:
            session = await self._get_session()
            headers = {'Authorization': f'Bearer {self.api_token}'}
            
            # Get dataset ID
            run_url = f"{self.base_url}/actor-runs/{run_id}"
            async with session.get(run_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to get run info: {response.status}")
                    return None
                
                run_info = await response.json()
                dataset_id = run_info['data']['defaultDatasetId']
            
            # Get dataset items
            dataset_url = f"{self.base_url}/datasets/{dataset_id}/items"
            async with session.get(dataset_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to get dataset items: {response.status}")
                    return None
                
                results = await response.json()
                return results if isinstance(results, list) else [results]
                
        except Exception as e:
            logger.error(f"Error getting results for run {run_id}: {e}")
            return None
    
    async def get_linkedin_company_data(
        self,
        linkedin_url: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Get LinkedIn company data via Apify"""
        try:
            logger.info(f"Fetching LinkedIn data for: {linkedin_url}")
            
            # Prepare input for LinkedIn company scraper
            input_data = {
                "companyUrls": [linkedin_url],
                "useCache": not force_refresh,
                "saveToDataset": True
            }
            
            # Run the actor
            results = await self._run_actor(self.linkedin_actor_id, input_data)
            
            if not results:
                return {
                    'success': False,
                    'error': 'Failed to run LinkedIn scraper',
                    'linkedin_url': linkedin_url
                }
            
            if not results or len(results) == 0:
                return {
                    'success': False,
                    'error': 'No data returned from LinkedIn scraper',
                    'linkedin_url': linkedin_url
                }
            
            # Process the first result
            company_data = results[0]
            
            # Extract and structure relevant information
            structured_data = self._structure_linkedin_data(company_data, linkedin_url)
            
            return {
                'success': True,
                'linkedin_url': linkedin_url,
                'company_data': structured_data,
                'raw_data': company_data,
                'data_freshness': 'fresh' if force_refresh else 'cached',
                'extraction_timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting LinkedIn data for {linkedin_url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'linkedin_url': linkedin_url
            }
    
    def _structure_linkedin_data(
        self,
        raw_data: Dict[str, Any],
        linkedin_url: str
    ) -> Dict[str, Any]:
        """Structure raw LinkedIn data into consistent format"""
        structured = {
            'linkedin_url': linkedin_url,
            'company_name': raw_data.get('name', ''),
            'description': raw_data.get('description', ''),
            'industry': raw_data.get('industry', ''),
            'company_size': raw_data.get('companySize', ''),
            'headquarters': raw_data.get('headquarters', ''),
            'founded': raw_data.get('founded', ''),
            'website': raw_data.get('website', ''),
            'specialties': raw_data.get('specialties', []),
            'employee_count': None,
            'growth_metrics': {},
            'recent_updates': []
        }
        
        # Parse employee count from company size
        if structured['company_size']:
            structured['employee_count'] = self._parse_employee_count(structured['company_size'])
        
        # Extract growth metrics if available
        if 'employeeCount' in raw_data:
            structured['employee_count'] = raw_data['employeeCount']
        
        if 'updates' in raw_data and isinstance(raw_data['updates'], list):
            structured['recent_updates'] = raw_data['updates'][:5]  # Keep last 5 updates
        
        # Calculate growth metrics
        structured['growth_metrics'] = self._calculate_growth_metrics(raw_data)
        
        # Add data quality score
        structured['data_quality_score'] = self._calculate_data_quality(structured)
        
        return structured
    
    def _parse_employee_count(self, company_size: str) -> Optional[int]:
        """Parse employee count from LinkedIn company size string"""
        try:
            import re
            
            # Common patterns: "51-200 employees", "1,001-5,000 employees"
            size_lower = company_size.lower()
            
            if 'employee' not in size_lower:
                return None
            
            # Extract numbers
            numbers = re.findall(r'[\d,]+', company_size)
            if not numbers:
                return None
            
            # Take the first number as rough estimate
            first_num = numbers[0].replace(',', '')
            return int(first_num)
            
        except Exception:
            return None
    
    def _calculate_growth_metrics(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate growth metrics from LinkedIn data"""
        metrics = {
            'has_recent_activity': False,
            'update_frequency': 'unknown',
            'engagement_level': 'unknown'
        }
        
        # Check for recent updates
        if 'updates' in raw_data and isinstance(raw_data['updates'], list):
            updates = raw_data['updates']
            if updates:
                metrics['has_recent_activity'] = True
                
                # Estimate update frequency
                if len(updates) >= 5:
                    metrics['update_frequency'] = 'high'
                elif len(updates) >= 3:
                    metrics['update_frequency'] = 'medium'
                else:
                    metrics['update_frequency'] = 'low'
        
        # Check follower count if available
        if 'followerCount' in raw_data:
            followers = raw_data['followerCount']
            if followers > 10000:
                metrics['engagement_level'] = 'high'
            elif followers > 1000:
                metrics['engagement_level'] = 'medium'
            else:
                metrics['engagement_level'] = 'low'
        
        return metrics
    
    def _calculate_data_quality(self, structured_data: Dict[str, Any]) -> float:
        """Calculate data quality score (0-1)"""
        score = 0.0
        total_fields = 0
        
        # Core fields
        core_fields = [
            'company_name', 'description', 'industry', 
            'company_size', 'headquarters', 'website'
        ]
        
        for field in core_fields:
            total_fields += 1
            if structured_data.get(field):
                score += 1
        
        # Bonus for additional data
        if structured_data.get('founded'):
            score += 0.5
        if structured_data.get('specialties'):
            score += 0.5
        if structured_data.get('employee_count'):
            score += 0.5
        if structured_data.get('recent_updates'):
            score += 0.5
        
        total_fields += 2  # Adjust for bonus fields
        
        return min(1.0, score / total_fields)
    
    async def get_multiple_companies(
        self,
        linkedin_urls: List[str],
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Get data for multiple LinkedIn companies"""
        try:
            logger.info(f"Fetching LinkedIn data for {len(linkedin_urls)} companies")
            
            # Prepare input for batch processing
            input_data = {
                "companyUrls": linkedin_urls,
                "useCache": not force_refresh,
                "saveToDataset": True
            }
            
            # Run the actor
            results = await self._run_actor(self.linkedin_actor_id, input_data)
            
            if not results:
                return {
                    'success': False,
                    'error': 'Failed to run LinkedIn batch scraper',
                    'requested_urls': linkedin_urls
                }
            
            # Process results
            processed_companies = []
            for result in results:
                if isinstance(result, dict):
                    company_url = result.get('url', '')
                    structured_data = self._structure_linkedin_data(result, company_url)
                    processed_companies.append({
                        'linkedin_url': company_url,
                        'success': True,
                        'data': structured_data
                    })
            
            return {
                'success': True,
                'requested_urls': linkedin_urls,
                'processed_count': len(processed_companies),
                'companies': processed_companies,
                'extraction_timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting multiple LinkedIn companies: {e}")
            return {
                'success': False,
                'error': str(e),
                'requested_urls': linkedin_urls
            }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return {
            'requests_made_this_hour': self.request_count,
            'requests_per_hour_limit': self.requests_per_hour,
            'hour_started_at': self.hour_start,
            'last_request_time': self.last_request_time
        }