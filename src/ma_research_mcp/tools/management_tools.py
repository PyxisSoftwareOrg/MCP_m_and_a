"""
Management tools for M&A Research Assistant
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import ScoringSystem, CompanyList, OverrideMetadata
from ..services import S3Service

logger = logging.getLogger(__name__)

# Initialize services
s3_service = S3Service()


async def manage_scoring_systems(
    action: str,
    system_data: Dict[str, Any] = None,
    system_id: str = ""
) -> Dict[str, Any]:
    """Create and manage custom scoring systems"""
    try:
        logger.info(f"Managing scoring system: {action}")
        
        if action == "create":
            if not system_data:
                return {
                    "success": False,
                    "error": "System data required for create action"
                }
            
            # Create new scoring system
            scoring_system = ScoringSystem(**system_data)
            s3_path = await s3_service.save_scoring_system(scoring_system)
            
            return {
                "success": True,
                "action": "create",
                "system_id": scoring_system.system_id,
                "s3_path": s3_path
            }
        
        elif action == "get":
            if not system_id:
                return {
                    "success": False,
                    "error": "System ID required for get action"
                }
            
            scoring_system = await s3_service.get_scoring_system(system_id)
            if not scoring_system:
                return {
                    "success": False,
                    "error": f"Scoring system {system_id} not found"
                }
            
            return {
                "success": True,
                "action": "get",
                "scoring_system": scoring_system.dict()
            }
        
        elif action == "list":
            # Get list of all scoring systems
            registry = await s3_service._load_json_object("scoring_systems/_registry.json") or []
            
            return {
                "success": True,
                "action": "list",
                "scoring_systems": registry
            }
        
        elif action == "update":
            if not system_id or not system_data:
                return {
                    "success": False,
                    "error": "System ID and data required for update action"
                }
            
            # Get existing system
            existing_system = await s3_service.get_scoring_system(system_id)
            if not existing_system:
                return {
                    "success": False,
                    "error": f"Scoring system {system_id} not found"
                }
            
            # Update system
            updated_data = existing_system.dict()
            updated_data.update(system_data)
            updated_data["updated_at"] = datetime.utcnow().isoformat() + 'Z'
            
            updated_system = ScoringSystem(**updated_data)
            s3_path = await s3_service.save_scoring_system(updated_system)
            
            return {
                "success": True,
                "action": "update",
                "system_id": system_id,
                "s3_path": s3_path
            }
        
        elif action == "delete":
            if not system_id:
                return {
                    "success": False,
                    "error": "System ID required for delete action"
                }
            
            # TODO: Implement soft delete by marking as inactive
            existing_system = await s3_service.get_scoring_system(system_id)
            if not existing_system:
                return {
                    "success": False,
                    "error": f"Scoring system {system_id} not found"
                }
            
            # Mark as inactive
            updated_data = existing_system.dict()
            updated_data["is_active"] = False
            updated_data["updated_at"] = datetime.utcnow().isoformat() + 'Z'
            
            updated_system = ScoringSystem(**updated_data)
            await s3_service.save_scoring_system(updated_system)
            
            return {
                "success": True,
                "action": "delete",
                "system_id": system_id,
                "status": "deactivated"
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
        
    except Exception as e:
        logger.error(f"Error managing scoring systems: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def override_company_tier(
    company_name: str,
    new_tier: str,
    reason: str,
    override_by: str
) -> Dict[str, Any]:
    """Manual tier override with approval workflow"""
    try:
        logger.info(f"Overriding tier for {company_name}: {new_tier}")
        
        # Get existing analysis
        analysis = await s3_service.get_analysis_result(company_name)
        if not analysis:
            return {
                "success": False,
                "error": f"No analysis found for company {company_name}"
            }
        
        # Create override metadata
        override_metadata = OverrideMetadata(
            override_by=override_by,
            override_date=datetime.utcnow().isoformat() + 'Z',
            override_reason=reason,
            approval_status="pending",
            approved_by=None,
            approval_date=None
        )
        
        # Update analysis with override
        analysis.manual_tier_override = new_tier
        analysis.override_metadata = override_metadata
        analysis.effective_tier = new_tier  # Override takes effect immediately
        
        # Save updated analysis
        s3_path = await s3_service.save_analysis_result(analysis)
        
        # Log the override for audit
        audit_logger = logging.getLogger("ma_research_mcp.audit")
        audit_logger.info(f"TIER_OVERRIDE: {company_name} from {analysis.automated_tier} to {new_tier} by {override_by}: {reason}")
        
        return {
            "success": True,
            "company_name": company_name,
            "previous_tier": analysis.automated_tier,
            "new_tier": new_tier,
            "override_by": override_by,
            "reason": reason,
            "s3_path": s3_path,
            "approval_status": "pending"
        }
        
    except Exception as e:
        logger.error(f"Error overriding tier for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def manage_company_lists(
    action: str,
    company_name: str = "",
    list_type: str = "active",
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Manage active and future candidate lists"""
    try:
        logger.info(f"Managing company lists: {action}")
        
        if action == "add":
            if not company_name:
                return {
                    "success": False,
                    "error": "Company name required for add action"
                }
            
            # Create company list entry
            company_list_entry = CompanyList(
                list_type=list_type,
                company_name=company_name,
                added_date=datetime.utcnow().isoformat() + 'Z',
                added_by=metadata.get("added_by", "system") if metadata else "system",
                automated_tier="UNKNOWN",
                automated_score=0.0,
                monitoring_frequency=metadata.get("monitoring_frequency", "monthly") if metadata else "monthly"
            )
            
            # Save to appropriate index
            index_file = f"_index/{list_type}_companies.json"
            existing_list = await s3_service._load_json_object(index_file) or []
            
            # Remove existing entry if present
            existing_list = [entry for entry in existing_list if entry.get("company_name") != company_name]
            
            # Add new entry
            existing_list.append(company_list_entry.dict())
            
            await s3_service._save_json_object(index_file, existing_list)
            
            return {
                "success": True,
                "action": "add",
                "company_name": company_name,
                "list_type": list_type
            }
        
        elif action == "remove":
            if not company_name:
                return {
                    "success": False,
                    "error": "Company name required for remove action"
                }
            
            # Remove from specified list
            index_file = f"_index/{list_type}_companies.json"
            existing_list = await s3_service._load_json_object(index_file) or []
            
            original_count = len(existing_list)
            existing_list = [entry for entry in existing_list if entry.get("company_name") != company_name]
            
            if len(existing_list) == original_count:
                return {
                    "success": False,
                    "error": f"Company {company_name} not found in {list_type} list"
                }
            
            await s3_service._save_json_object(index_file, existing_list)
            
            return {
                "success": True,
                "action": "remove",
                "company_name": company_name,
                "list_type": list_type
            }
        
        elif action == "move":
            if not company_name or not metadata or "target_list" not in metadata:
                return {
                    "success": False,
                    "error": "Company name and target_list required for move action"
                }
            
            source_list = list_type
            target_list = metadata["target_list"]
            
            # Remove from source list
            source_index = f"_index/{source_list}_companies.json"
            source_entries = await s3_service._load_json_object(source_index) or []
            
            company_entry = None
            for entry in source_entries:
                if entry.get("company_name") == company_name:
                    company_entry = entry
                    break
            
            if not company_entry:
                return {
                    "success": False,
                    "error": f"Company {company_name} not found in {source_list} list"
                }
            
            # Remove from source
            source_entries = [entry for entry in source_entries if entry.get("company_name") != company_name]
            await s3_service._save_json_object(source_index, source_entries)
            
            # Add to target
            target_index = f"_index/{target_list}_companies.json"
            target_entries = await s3_service._load_json_object(target_index) or []
            
            # Update entry metadata
            company_entry["list_type"] = target_list
            company_entry["moved_date"] = datetime.utcnow().isoformat() + 'Z'
            company_entry["moved_from"] = source_list
            
            # Remove existing entry in target if present
            target_entries = [entry for entry in target_entries if entry.get("company_name") != company_name]
            target_entries.append(company_entry)
            
            await s3_service._save_json_object(target_index, target_entries)
            
            return {
                "success": True,
                "action": "move",
                "company_name": company_name,
                "from_list": source_list,
                "to_list": target_list
            }
        
        elif action == "list":
            # Get companies from specified list
            index_file = f"_index/{list_type}_companies.json"
            companies = await s3_service._load_json_object(index_file) or []
            
            return {
                "success": True,
                "action": "list",
                "list_type": list_type,
                "company_count": len(companies),
                "companies": companies
            }
        
        elif action == "update":
            if not company_name or not metadata:
                return {
                    "success": False,
                    "error": "Company name and metadata required for update action"
                }
            
            # Update company entry in list
            index_file = f"_index/{list_type}_companies.json"
            companies = await s3_service._load_json_object(index_file) or []
            
            company_found = False
            for entry in companies:
                if entry.get("company_name") == company_name:
                    entry.update(metadata)
                    entry["last_updated"] = datetime.utcnow().isoformat() + 'Z'
                    company_found = True
                    break
            
            if not company_found:
                return {
                    "success": False,
                    "error": f"Company {company_name} not found in {list_type} list"
                }
            
            await s3_service._save_json_object(index_file, companies)
            
            return {
                "success": True,
                "action": "update",
                "company_name": company_name,
                "list_type": list_type,
                "updated_fields": list(metadata.keys())
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
        
    except Exception as e:
        logger.error(f"Error managing company lists: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def update_metadata(
    company_name: str,
    metadata_updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Manual metadata updates for companies"""
    try:
        logger.info(f"Updating metadata for {company_name}")
        
        # Get existing analysis
        analysis = await s3_service.get_analysis_result(company_name)
        if not analysis:
            return {
                "success": False,
                "error": f"No analysis found for company {company_name}"
            }
        
        # Update allowed metadata fields
        allowed_fields = [
            "linkedin_url", "website_url", "headquarters_location",
            "industry_vertical", "founding_year", "employee_count",
            "estimated_revenue", "primary_business_model"
        ]
        
        updated_fields = []
        for field, value in metadata_updates.items():
            if field in allowed_fields:
                # For analysis object, we'd typically store this in a metadata section
                # For now, update the basic fields that exist
                if hasattr(analysis, field):
                    setattr(analysis, field, value)
                    updated_fields.append(field)
        
        if not updated_fields:
            return {
                "success": False,
                "error": "No valid fields provided for update"
            }
        
        # Save updated analysis
        s3_path = await s3_service.save_analysis_result(analysis)
        
        # Log the update for audit
        audit_logger = logging.getLogger("ma_research_mcp.audit")
        audit_logger.info(f"METADATA_UPDATE: {company_name} fields: {updated_fields}")
        
        return {
            "success": True,
            "company_name": company_name,
            "updated_fields": updated_fields,
            "s3_path": s3_path,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error updating metadata for {company_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }