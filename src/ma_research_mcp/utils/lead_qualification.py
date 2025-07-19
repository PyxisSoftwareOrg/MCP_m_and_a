"""
Lead qualification engine for M&A Research Assistant
"""

import logging
import re
from typing import Any, Dict, List, Optional

from ..models import FilteringResult, QualificationResult

logger = logging.getLogger(__name__)


class LeadQualificationEngine:
    """Multi-tier lead qualification and filtering"""
    
    def __init__(self):
        # Geographic qualification rules
        self.geographic_rules = {
            "north_america": {
                "countries": ["US", "USA", "United States", "Canada", "Mexico"],
                "all_verticals": True
            },
            "united_kingdom": {
                "countries": ["UK", "United Kingdom", "Britain", "England", "Scotland", "Wales"],
                "allowed_verticals": ["sports", "fitness", "recreation", "health", "wellness"]
            },
            "excluded_regions": [
                "China", "Russia", "Iran", "North Korea", "Cuba", "Syria"
            ]
        }
        
        # Business model qualification criteria
        self.business_model_criteria = {
            "required_software_indicators": [
                "software", "saas", "platform", "application", "system", "solution",
                "technology", "digital", "cloud", "api", "dashboard", "analytics"
            ],
            "service_red_flags": [
                "consulting", "implementation", "training", "support services",
                "professional services", "custom development", "integration services"
            ],
            "b2b_indicators": [
                "enterprise", "business", "companies", "organizations", "clients",
                "corporate", "commercial", "professional", "industry"
            ],
            "b2c_red_flags": [
                "consumer", "personal", "individual", "marketplace", "e-commerce",
                "retail customers", "end users", "mobile app"
            ]
        }
        
        # Size and maturity thresholds
        self.size_maturity_thresholds = {
            "min_revenue": 1000000,  # $1M
            "min_employees": 10,
            "min_age_years": 4,
            "max_recent_funding_months": 18
        }
        
        # Q1-Q5 qualification questions
        self.qualification_questions = {
            "q1": "Horizontal vs Vertical focus",
            "q2": "Point vs Suite solution", 
            "q3": "Mission Critical nature",
            "q4": "OPM vs Private funding",
            "q5": "Annual Revenue Per User (ARPU)"
        }
        
        logger.info("Initialized lead qualification engine")
    
    async def qualify_lead(
        self,
        company_data: Dict[str, Any],
        force_requalification: bool = False
    ) -> Dict[str, Any]:
        """Complete lead qualification process"""
        try:
            logger.info(f"Qualifying lead: {company_data.get('company_name', 'Unknown')}")
            
            # Step 1: Geographic filtering
            geographic_result = self._check_geographic_qualification(company_data)
            
            # Step 2: Business model filtering
            business_model_result = self._check_business_model_qualification(company_data)
            
            # Step 3: Size and maturity filtering
            size_maturity_result = self._check_size_maturity_qualification(company_data)
            
            # Create filtering result
            filtering_result = FilteringResult(
                passed_geographic_filter=geographic_result["qualified"],
                passed_business_model_filter=business_model_result["qualified"],
                passed_size_maturity_filter=size_maturity_result["qualified"],
                overall_filter_result=(
                    geographic_result["qualified"] and 
                    business_model_result["qualified"] and 
                    size_maturity_result["qualified"]
                ),
                filter_notes=[
                    *geographic_result.get("notes", []),
                    *business_model_result.get("notes", []),
                    *size_maturity_result.get("notes", [])
                ],
                geographic_region=geographic_result.get("region", "unknown"),
                business_model_type=business_model_result.get("type", "unknown"),
                estimated_revenue=size_maturity_result.get("estimated_revenue"),
                estimated_employees=size_maturity_result.get("estimated_employees"),
                company_age_years=size_maturity_result.get("company_age_years")
            )
            
            # Step 4: Detailed qualification (Q1-Q5) if passed filtering
            qualification_result = None
            if filtering_result.overall_filter_result:
                qualification_result = await self._perform_detailed_qualification(company_data)
            else:
                # Create basic disqualified result
                disqualification_reasons = []
                if not geographic_result["qualified"]:
                    disqualification_reasons.append("Geographic restriction")
                if not business_model_result["qualified"]:
                    disqualification_reasons.append("Business model mismatch")
                if not size_maturity_result["qualified"]:
                    disqualification_reasons.append("Size/maturity threshold not met")
                
                qualification_result = QualificationResult(
                    is_qualified=False,
                    qualification_score=0.0,
                    disqualification_reasons=disqualification_reasons,
                    geographic_qualification=geographic_result["qualified"],
                    business_model_qualification=business_model_result["qualified"],
                    size_maturity_qualification=size_maturity_result["qualified"],
                    q1_horizontal_vs_vertical="not_assessed",
                    q2_point_vs_suite="not_assessed",
                    q3_mission_critical="not_assessed",
                    q4_opm_vs_private="not_assessed",
                    q5_arpu_level="not_assessed",
                    qualification_confidence=0.0
                )
            
            return {
                "success": True,
                "is_qualified": qualification_result.is_qualified,
                "filtering_result": filtering_result,
                "qualification_result": qualification_result,
                "qualification_summary": self._generate_qualification_summary(
                    filtering_result, qualification_result
                )
            }
            
        except Exception as e:
            logger.error(f"Error in lead qualification: {e}")
            return {
                "success": False,
                "error": str(e),
                "is_qualified": False
            }
    
    def _check_geographic_qualification(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check geographic qualification rules"""
        try:
            # Extract location information
            locations = []
            
            # Check various location fields
            location_fields = [
                "headquarters", "location", "address", "country", "region",
                "headquarters_location", "company_location"
            ]
            
            for field in location_fields:
                if field in company_data and company_data[field]:
                    locations.append(str(company_data[field]).lower())
            
            # Also check website domain for country indicators
            website = company_data.get("website_url", "")
            if website:
                domain = website.lower()
                if ".uk" in domain or ".co.uk" in domain:
                    locations.append("uk")
                elif ".ca" in domain:
                    locations.append("canada")
                elif ".mx" in domain:
                    locations.append("mexico")
            
            location_text = " ".join(locations)
            
            # Check for excluded regions first
            for excluded in self.geographic_rules["excluded_regions"]:
                if excluded.lower() in location_text:
                    return {
                        "qualified": False,
                        "region": excluded,
                        "notes": [f"Company located in excluded region: {excluded}"]
                    }
            
            # Check North America (all verticals allowed)
            for country in self.geographic_rules["north_america"]["countries"]:
                if country.lower() in location_text:
                    return {
                        "qualified": True,
                        "region": "north_america",
                        "notes": [f"Company located in North America: {country}"]
                    }
            
            # Check UK (sports/fitness only)
            for country in self.geographic_rules["united_kingdom"]["countries"]:
                if country.lower() in location_text:
                    # Check if company is in sports/fitness vertical
                    vertical_qualified = self._check_uk_vertical_qualification(company_data)
                    return {
                        "qualified": vertical_qualified,
                        "region": "united_kingdom", 
                        "notes": [
                            f"Company located in UK: {country}",
                            f"Sports/Fitness vertical requirement: {'met' if vertical_qualified else 'not met'}"
                        ]
                    }
            
            # If no location match found, assume disqualified
            return {
                "qualified": False,
                "region": "unknown",
                "notes": ["Unable to determine qualifying geographic location"]
            }
            
        except Exception as e:
            logger.error(f"Error in geographic qualification: {e}")
            return {
                "qualified": False,
                "region": "error",
                "notes": [f"Error checking geography: {str(e)}"]
            }
    
    def _check_uk_vertical_qualification(self, company_data: Dict[str, Any]) -> bool:
        """Check if UK company operates in sports/fitness vertical"""
        text_fields = []
        
        # Collect text from various fields
        text_sources = [
            "description", "industry", "specialties", "products", "solutions",
            "title", "company_info", "text_content", "industry_vertical"
        ]
        
        for field in text_sources:
            if field in company_data and company_data[field]:
                if isinstance(company_data[field], str):
                    text_fields.append(company_data[field].lower())
                elif isinstance(company_data[field], list):
                    text_fields.extend([str(item).lower() for item in company_data[field]])
                elif isinstance(company_data[field], dict):
                    text_fields.extend([str(value).lower() for value in company_data[field].values()])
        
        combined_text = " ".join(text_fields)
        
        # Sports/fitness keywords
        sports_fitness_keywords = [
            "sports", "fitness", "gym", "recreation", "athletic", "exercise",
            "wellness", "health club", "leisure", "coaching", "training",
            "tournament", "league", "competition", "stadium", "arena",
            "membership", "personal training", "yoga", "pilates", "swimming",
            "tennis", "golf", "football", "soccer", "basketball", "cycling"
        ]
        
        for keyword in sports_fitness_keywords:
            if keyword in combined_text:
                return True
        
        return False
    
    def _check_business_model_qualification(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check business model qualification criteria"""
        try:
            # Collect text for analysis
            text_fields = []
            text_sources = [
                "description", "products", "solutions", "services", "text_content",
                "title", "company_info", "primary_business_model"
            ]
            
            for field in text_sources:
                if field in company_data and company_data[field]:
                    if isinstance(company_data[field], str):
                        text_fields.append(company_data[field].lower())
                    elif isinstance(company_data[field], dict):
                        text_fields.extend([str(v).lower() for v in company_data[field].values()])
            
            combined_text = " ".join(text_fields)
            
            # Check for software indicators
            software_score = 0
            for indicator in self.business_model_criteria["required_software_indicators"]:
                if indicator in combined_text:
                    software_score += 1
            
            # Check for service red flags
            service_flags = 0
            for flag in self.business_model_criteria["service_red_flags"]:
                if flag in combined_text:
                    service_flags += 1
            
            # Check for B2B indicators
            b2b_score = 0
            for indicator in self.business_model_criteria["b2b_indicators"]:
                if indicator in combined_text:
                    b2b_score += 1
            
            # Check for B2C red flags
            b2c_flags = 0
            for flag in self.business_model_criteria["b2c_red_flags"]:
                if flag in combined_text:
                    b2c_flags += 1
            
            # Determine qualification
            software_qualified = software_score >= 2
            service_qualified = service_flags <= 2  # Some services OK
            b2b_qualified = b2b_score > b2c_flags
            
            overall_qualified = software_qualified and service_qualified and b2b_qualified
            
            # Determine business model type
            if software_score >= 3 and service_flags <= 1:
                model_type = "pure_software"
            elif software_score >= 2 and service_flags <= 3:
                model_type = "software_with_services"
            elif service_flags > 3:
                model_type = "service_heavy"
            else:
                model_type = "unknown"
            
            notes = [
                f"Software indicators: {software_score}",
                f"Service flags: {service_flags}",
                f"B2B indicators: {b2b_score}",
                f"B2C flags: {b2c_flags}",
                f"Business model type: {model_type}"
            ]
            
            return {
                "qualified": overall_qualified,
                "type": model_type,
                "notes": notes,
                "scores": {
                    "software_score": software_score,
                    "service_flags": service_flags,
                    "b2b_score": b2b_score,
                    "b2c_flags": b2c_flags
                }
            }
            
        except Exception as e:
            logger.error(f"Error in business model qualification: {e}")
            return {
                "qualified": False,
                "type": "error",
                "notes": [f"Error checking business model: {str(e)}"]
            }
    
    def _check_size_maturity_qualification(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check size and maturity qualification thresholds"""
        try:
            notes = []
            qualified = True
            
            # Extract revenue information
            estimated_revenue = None
            revenue_sources = ["revenue", "estimated_revenue", "annual_revenue"]
            
            for source in revenue_sources:
                if source in company_data and company_data[source]:
                    try:
                        estimated_revenue = float(company_data[source])
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Try to extract from text
            if not estimated_revenue:
                estimated_revenue = self._extract_revenue_from_text(company_data)
            
            # Check revenue threshold
            if estimated_revenue:
                if estimated_revenue >= self.size_maturity_thresholds["min_revenue"]:
                    notes.append(f"Revenue threshold met: ${estimated_revenue:,.0f}")
                else:
                    notes.append(f"Revenue below threshold: ${estimated_revenue:,.0f} < ${self.size_maturity_thresholds['min_revenue']:,.0f}")
                    qualified = False
            else:
                notes.append("Revenue information not available")
            
            # Extract employee count
            estimated_employees = None
            employee_sources = ["employee_count", "employees", "team_size", "staff_count"]
            
            for source in employee_sources:
                if source in company_data and company_data[source]:
                    try:
                        estimated_employees = int(company_data[source])
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Try to extract from text
            if not estimated_employees:
                estimated_employees = self._extract_employee_count_from_text(company_data)
            
            # Check employee threshold
            if estimated_employees:
                if estimated_employees >= self.size_maturity_thresholds["min_employees"]:
                    notes.append(f"Employee threshold met: {estimated_employees}")
                else:
                    notes.append(f"Employee count below threshold: {estimated_employees} < {self.size_maturity_thresholds['min_employees']}")
                    qualified = False
            else:
                notes.append("Employee count information not available")
            
            # Extract company age
            company_age_years = None
            age_sources = ["founding_year", "founded", "established", "company_age"]
            
            for source in age_sources:
                if source in company_data and company_data[source]:
                    try:
                        founding_year = int(company_data[source])
                        from datetime import datetime
                        current_year = datetime.now().year
                        company_age_years = current_year - founding_year
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Try to extract from text
            if not company_age_years:
                company_age_years = self._extract_company_age_from_text(company_data)
            
            # Check age threshold
            if company_age_years:
                if company_age_years >= self.size_maturity_thresholds["min_age_years"]:
                    notes.append(f"Age threshold met: {company_age_years} years")
                else:
                    notes.append(f"Company too young: {company_age_years} < {self.size_maturity_thresholds['min_age_years']} years")
                    qualified = False
            else:
                notes.append("Company age information not available")
            
            # If we don't have revenue OR employees, but have one, be more lenient
            if not estimated_revenue and not estimated_employees:
                notes.append("Insufficient size data - requires manual review")
                qualified = False
            elif (not estimated_revenue or estimated_revenue < self.size_maturity_thresholds["min_revenue"]) and \
                 (not estimated_employees or estimated_employees < self.size_maturity_thresholds["min_employees"]):
                qualified = False
            elif estimated_revenue and estimated_revenue >= self.size_maturity_thresholds["min_revenue"]:
                qualified = True  # Revenue threshold met
            elif estimated_employees and estimated_employees >= self.size_maturity_thresholds["min_employees"]:
                qualified = True  # Employee threshold met
            
            return {
                "qualified": qualified,
                "estimated_revenue": estimated_revenue,
                "estimated_employees": estimated_employees,
                "company_age_years": company_age_years,
                "notes": notes
            }
            
        except Exception as e:
            logger.error(f"Error in size/maturity qualification: {e}")
            return {
                "qualified": False,
                "notes": [f"Error checking size/maturity: {str(e)}"]
            }
    
    def _extract_revenue_from_text(self, company_data: Dict[str, Any]) -> Optional[float]:
        """Extract revenue information from text fields"""
        text_content = self._get_combined_text(company_data)
        
        # Revenue patterns
        patterns = [
            r'\$(\d+(?:\.\d+)?)\s*(?:million|m)\s*(?:in\s*)?(?:revenue|sales)',
            r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:in\s*)?(?:revenue|sales)',
            r'revenue.*?\$(\d+(?:\.\d+)?)\s*(?:million|m)',
            r'(\d+(?:\.\d+)?)\s*million.*?revenue'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match.replace(',', ''))
                    if 'million' in pattern or 'm' in pattern:
                        value *= 1000000
                    return value
                except ValueError:
                    continue
        
        return None
    
    def _extract_employee_count_from_text(self, company_data: Dict[str, Any]) -> Optional[int]:
        """Extract employee count from text fields"""
        text_content = self._get_combined_text(company_data)
        
        # Employee count patterns
        patterns = [
            r'(\d+)\s*(?:\+)?\s*employees',
            r'team\s*of\s*(\d+)',
            r'(\d+)\s*(?:\+)?\s*people',
            r'staff\s*of\s*(\d+)',
            r'(\d+)\s*person\s*team'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                try:
                    return int(match)
                except ValueError:
                    continue
        
        return None
    
    def _extract_company_age_from_text(self, company_data: Dict[str, Any]) -> Optional[int]:
        """Extract company age from text fields"""
        text_content = self._get_combined_text(company_data)
        
        # Company age/founding patterns
        patterns = [
            r'(?:founded|established|since)\s*(?:in\s*)?(\d{4})',
            r'(\d{4}).*?founded',
            r'since\s*(\d{4})'
        ]
        
        from datetime import datetime
        current_year = datetime.now().year
        
        for pattern in patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                try:
                    founding_year = int(match)
                    if 1900 <= founding_year <= current_year:
                        return current_year - founding_year
                except ValueError:
                    continue
        
        return None
    
    def _get_combined_text(self, company_data: Dict[str, Any]) -> str:
        """Get combined text from various fields"""
        text_fields = []
        text_sources = [
            "description", "text_content", "company_info", "about",
            "title", "overview", "summary"
        ]
        
        for field in text_sources:
            if field in company_data and company_data[field]:
                if isinstance(company_data[field], str):
                    text_fields.append(company_data[field])
                elif isinstance(company_data[field], dict):
                    text_fields.extend([str(v) for v in company_data[field].values()])
        
        return " ".join(text_fields).lower()
    
    async def _perform_detailed_qualification(self, company_data: Dict[str, Any]) -> QualificationResult:
        """Perform detailed Q1-Q5 qualification assessment"""
        try:
            # For now, implement basic rule-based assessment
            # In production, this could use LLM for more sophisticated analysis
            
            q1_result = self._assess_horizontal_vs_vertical(company_data)
            q2_result = self._assess_point_vs_suite(company_data)
            q3_result = self._assess_mission_critical(company_data)
            q4_result = self._assess_opm_vs_private(company_data)
            q5_result = self._assess_arpu_level(company_data)
            
            # Calculate overall qualification score
            scores = [q1_result["score"], q2_result["score"], q3_result["score"], 
                     q4_result["score"], q5_result["score"]]
            qualification_score = sum(scores) / len(scores)
            
            # Determine if qualified (average score >= 6.0)
            is_qualified = qualification_score >= 6.0
            
            # Calculate confidence based on data availability
            confidences = [q1_result["confidence"], q2_result["confidence"], 
                          q3_result["confidence"], q4_result["confidence"], q5_result["confidence"]]
            overall_confidence = sum(confidences) / len(confidences)
            
            return QualificationResult(
                is_qualified=is_qualified,
                qualification_score=qualification_score,
                disqualification_reasons=[],
                geographic_qualification=True,
                business_model_qualification=True,
                size_maturity_qualification=True,
                q1_horizontal_vs_vertical=q1_result["assessment"],
                q2_point_vs_suite=q2_result["assessment"],
                q3_mission_critical=q3_result["assessment"],
                q4_omp_vs_private=q4_result["assessment"],
                q5_arpu_level=q5_result["assessment"],
                qualification_confidence=overall_confidence
            )
            
        except Exception as e:
            logger.error(f"Error in detailed qualification: {e}")
            return QualificationResult(
                is_qualified=False,
                qualification_score=0.0,
                disqualification_reasons=[f"Error in qualification: {str(e)}"],
                geographic_qualification=True,
                business_model_qualification=True,
                size_maturity_qualification=True,
                q1_horizontal_vs_vertical="error",
                q2_point_vs_suite="error",
                q3_mission_critical="error",
                q4_opm_vs_private="error",
                q5_arpu_level="error",
                qualification_confidence=0.0
            )
    
    def _assess_horizontal_vs_vertical(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess Q1: Horizontal vs Vertical focus"""
        text_content = self._get_combined_text(company_data)
        
        vertical_indicators = [
            "industry-specific", "vertical", "specialized", "tailored",
            "healthcare", "education", "finance", "retail", "manufacturing",
            "sports", "fitness", "legal", "construction", "automotive"
        ]
        
        horizontal_indicators = [
            "any industry", "all industries", "general", "universal",
            "cross-industry", "horizontal", "generic", "broad market"
        ]
        
        vertical_score = sum(1 for indicator in vertical_indicators if indicator in text_content)
        horizontal_score = sum(1 for indicator in horizontal_indicators if indicator in text_content)
        
        if vertical_score > horizontal_score * 1.5:
            assessment = "vertical_focused"
            score = 8.0
        elif vertical_score > horizontal_score:
            assessment = "mostly_vertical"
            score = 6.0
        elif horizontal_score > vertical_score:
            assessment = "horizontal"
            score = 3.0
        else:
            assessment = "mixed"
            score = 5.0
        
        confidence = min(1.0, (vertical_score + horizontal_score) / 5.0)
        
        return {
            "assessment": assessment,
            "score": score,
            "confidence": confidence
        }
    
    def _assess_point_vs_suite(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess Q2: Point vs Suite solution"""
        text_content = self._get_combined_text(company_data)
        
        suite_indicators = [
            "suite", "platform", "integrated", "end-to-end", "comprehensive",
            "modules", "all-in-one", "complete solution", "unified"
        ]
        
        point_indicators = [
            "single", "focused", "specific", "specialized tool",
            "one thing", "targeted", "niche"
        ]
        
        suite_score = sum(1 for indicator in suite_indicators if indicator in text_content)
        point_score = sum(1 for indicator in point_indicators if indicator in text_content)
        
        if suite_score > point_score * 1.5:
            assessment = "comprehensive_suite"
            score = 8.0
        elif suite_score > point_score:
            assessment = "modular_platform"
            score = 6.0
        elif point_score > suite_score:
            assessment = "point_solution"
            score = 4.0
        else:
            assessment = "mixed"
            score = 5.0
        
        confidence = min(1.0, (suite_score + point_score) / 3.0)
        
        return {
            "assessment": assessment,
            "score": score,
            "confidence": confidence
        }
    
    def _assess_mission_critical(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess Q3: Mission Critical nature"""
        text_content = self._get_combined_text(company_data)
        
        critical_indicators = [
            "mission critical", "essential", "core business", "critical",
            "compliance", "regulatory", "security", "audit",
            "24/7", "uptime", "reliability", "enterprise-grade"
        ]
        
        non_critical_indicators = [
            "nice to have", "optional", "convenience", "enhancement",
            "productivity", "efficiency", "workflow"
        ]
        
        critical_score = sum(1 for indicator in critical_indicators if indicator in text_content)
        non_critical_score = sum(1 for indicator in non_critical_indicators if indicator in text_content)
        
        if critical_score > non_critical_score * 1.5:
            assessment = "mission_critical"
            score = 8.0
        elif critical_score > non_critical_score:
            assessment = "important"
            score = 6.0
        elif non_critical_score > critical_score:
            assessment = "nice_to_have"
            score = 3.0
        else:
            assessment = "moderate"
            score = 5.0
        
        confidence = min(1.0, (critical_score + non_critical_score) / 3.0)
        
        return {
            "assessment": assessment,
            "score": score,
            "confidence": confidence
        }
    
    def _assess_opm_vs_private(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess Q4: OPM vs Private funding"""
        text_content = self._get_combined_text(company_data)
        
        government_indicators = [
            "government", "public sector", "federal", "state", "municipal",
            "grant", "funding", "taxpayer", "public contract"
        ]
        
        private_indicators = [
            "commercial", "private sector", "enterprise", "business",
            "corporate", "subscription", "license", "market-driven"
        ]
        
        gov_score = sum(1 for indicator in government_indicators if indicator in text_content)
        private_score = sum(1 for indicator in private_indicators if indicator in text_content)
        
        if private_score > gov_score * 2:
            assessment = "private_focused"
            score = 9.0
        elif private_score > gov_score:
            assessment = "mostly_private"
            score = 7.0
        elif gov_score > private_score:
            assessment = "government_dependent"
            score = 4.0
        else:
            assessment = "mixed"
            score = 6.0
        
        confidence = min(1.0, (gov_score + private_score) / 3.0)
        
        return {
            "assessment": assessment,
            "score": score,
            "confidence": confidence
        }
    
    def _assess_arpu_level(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess Q5: Annual Revenue Per User level"""
        # Try to extract pricing information
        pricing_data = company_data.get("pricing_info", [])
        text_content = self._get_combined_text(company_data)
        
        # Look for pricing indicators
        high_value_patterns = [
            r'\$(\d{2,3}),?(\d{3})\+?.*?(?:year|annual)',
            r'\$(\d{1,2}),?(\d{3}).*?(?:month|monthly)',
            r'enterprise.*?\$(\d+)',
            r'starting.*?\$(\d{3,})'
        ]
        
        pricing_amounts = []
        for pattern in high_value_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    amount = int(''.join(match))
                else:
                    amount = int(match)
                pricing_amounts.append(amount)
        
        if pricing_amounts:
            max_price = max(pricing_amounts)
            if max_price >= 50000:
                assessment = "premium_enterprise"
                score = 10.0
            elif max_price >= 25000:
                assessment = "high_value"
                score = 8.0
            elif max_price >= 10000:
                assessment = "mid_market"
                score = 6.0
            elif max_price >= 2000:
                assessment = "standard"
                score = 5.0
            else:
                assessment = "low_value"
                score = 3.0
            confidence = 0.8
        else:
            assessment = "unknown"
            score = 5.0
            confidence = 0.2
        
        return {
            "assessment": assessment,
            "score": score,
            "confidence": confidence
        }
    
    def _generate_qualification_summary(
        self,
        filtering_result: FilteringResult,
        qualification_result: QualificationResult
    ) -> str:
        """Generate human-readable qualification summary"""
        if not filtering_result.overall_filter_result:
            failed_filters = []
            if not filtering_result.passed_geographic_filter:
                failed_filters.append("geographic")
            if not filtering_result.passed_business_model_filter:
                failed_filters.append("business model")
            if not filtering_result.passed_size_maturity_filter:
                failed_filters.append("size/maturity")
            
            return f"DISQUALIFIED: Failed {', '.join(failed_filters)} filter(s)"
        
        if not qualification_result.is_qualified:
            return f"QUALIFIED FOR BASIC CRITERIA but failed detailed assessment (score: {qualification_result.qualification_score:.1f}/10)"
        
        score = qualification_result.qualification_score
        confidence = qualification_result.qualification_confidence
        
        if score >= 8.0:
            tier = "STRONG CANDIDATE"
        elif score >= 6.5:
            tier = "GOOD CANDIDATE"
        elif score >= 6.0:
            tier = "MARGINAL CANDIDATE"
        else:
            tier = "WEAK CANDIDATE"
        
        return f"{tier}: Score {score:.1f}/10 (confidence: {confidence:.1f})"