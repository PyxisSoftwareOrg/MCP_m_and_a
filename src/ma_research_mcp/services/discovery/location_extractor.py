"""
Location extraction service for finding company addresses and locations
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LocationExtractor:
    """Extract company location information from web content"""
    
    def __init__(self):
        self.us_states = {
            'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
            'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
            'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana',
            'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota',
            'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
            'new hampshire', 'new jersey', 'new mexico', 'new york',
            'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon',
            'pennsylvania', 'rhode island', 'south carolina', 'south dakota',
            'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington',
            'west virginia', 'wisconsin', 'wyoming'
        }
        
        self.state_abbreviations = {
            'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga',
            'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md',
            'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj',
            'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri', 'sc',
            'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy',
            'dc'  # District of Columbia
        }
        
        self.countries = {
            'united states', 'usa', 'us', 'canada', 'united kingdom', 'uk',
            'australia', 'germany', 'france', 'italy', 'spain', 'netherlands',
            'sweden', 'norway', 'denmark', 'finland', 'switzerland', 'austria',
            'belgium', 'ireland', 'new zealand', 'japan', 'singapore'
        }
        
        # Address patterns
        self.address_patterns = [
            # Street number + street name + street type
            r'\b\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|court|ct|place|pl|circle|cir)\b',
            # PO Box
            r'\bpo\s+box\s+\d+\b',
            r'\bp\.o\.?\s+box\s+\d+\b',
            # Suite/Floor/Unit
            r'\bsuite\s+\w+\b',
            r'\bfloor\s+\d+\b',
            r'\bunit\s+\w+\b',
        ]
        
        # Zip code patterns
        self.zip_patterns = [
            r'\b\d{5}(?:-\d{4})?\b',  # US ZIP codes
            r'\b[A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d\b',  # Canadian postal codes
        ]
        
        # Phone number patterns
        self.phone_patterns = [
            r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',
        ]
    
    def extract_locations_from_html(self, html_content: str, url: str = "") -> Dict[str, any]:
        """Extract location information from HTML content"""
        
        if not html_content:
            return self._empty_location_result()
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text_content = soup.get_text()
            
            # Look for structured data
            structured_data = self._extract_structured_data(soup)
            
            # Look for contact/about sections
            contact_sections = self._find_contact_sections(soup)
            
            # Extract addresses from different sources
            addresses = []
            
            # From structured data
            if structured_data:
                addresses.extend(structured_data.get('addresses', []))
            
            # From contact sections
            for section in contact_sections:
                section_text = section.get_text()
                section_addresses = self._extract_addresses_from_text(section_text)
                addresses.extend(section_addresses)
            
            # From general text if no addresses found yet
            if not addresses:
                addresses = self._extract_addresses_from_text(text_content)
            
            # Extract other location info
            phone_numbers = self._extract_phone_numbers(text_content)
            cities_states = self._extract_cities_and_states(text_content)
            
            # Determine primary location
            primary_location = self._determine_primary_location(addresses, cities_states)
            
            return {
                'addresses': addresses[:5],  # Limit to top 5
                'phone_numbers': phone_numbers[:3],  # Limit to top 3
                'cities_states': list(cities_states)[:5],
                'primary_location': primary_location,
                'structured_data': structured_data,
                'extraction_confidence': self._calculate_confidence(addresses, phone_numbers, cities_states),
                'source_url': url
            }
            
        except Exception as e:
            logger.error(f"Failed to extract locations from HTML: {e}")
            return self._empty_location_result()
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract location data from structured markup"""
        structured_data = {}
        
        try:
            # JSON-LD structured data
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    
                    if isinstance(data, dict):
                        address = data.get('address')
                        if address:
                            structured_data['addresses'] = [self._format_structured_address(address)]
                            
                except Exception as e:
                    logger.debug(f"Failed to parse JSON-LD: {e}")
            
            # Microdata
            address_elements = soup.find_all(attrs={"itemtype": re.compile(r"schema\.org.*Address")})
            for elem in address_elements:
                address = self._extract_microdata_address(elem)
                if address:
                    if 'addresses' not in structured_data:
                        structured_data['addresses'] = []
                    structured_data['addresses'].append(address)
            
            return structured_data if structured_data else None
            
        except Exception as e:
            logger.debug(f"Failed to extract structured data: {e}")
            return None
    
    def _find_contact_sections(self, soup: BeautifulSoup) -> List:
        """Find contact/address sections in HTML"""
        contact_sections = []
        
        # Look for sections with contact-related keywords
        contact_keywords = [
            'contact', 'address', 'location', 'office', 'headquarters',
            'about', 'footer', 'contact-us', 'contact-info'
        ]
        
        for keyword in contact_keywords:
            # Find by class/id containing keyword
            elements = soup.find_all(attrs={'class': re.compile(keyword, re.I)})
            elements.extend(soup.find_all(attrs={'id': re.compile(keyword, re.I)}))
            contact_sections.extend(elements)
        
        # Look for footer
        footer = soup.find('footer')
        if footer:
            contact_sections.append(footer)
        
        # Look for address tags
        address_tags = soup.find_all('address')
        contact_sections.extend(address_tags)
        
        return contact_sections
    
    def _extract_addresses_from_text(self, text: str) -> List[Dict]:
        """Extract addresses from plain text"""
        addresses = []
        
        # Normalize text
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Look for address patterns
        for pattern in self.address_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                address_candidate = self._expand_address_context(text, match.span())
                if address_candidate:
                    addresses.append({
                        'full_address': address_candidate,
                        'confidence': 0.8,
                        'type': 'extracted'
                    })
        
        return addresses
    
    def _expand_address_context(self, text: str, match_span: Tuple[int, int]) -> Optional[str]:
        """Expand address match to include surrounding context"""
        start, end = match_span
        
        # Look for surrounding context (up to 200 chars before and after)
        context_start = max(0, start - 200)
        context_end = min(len(text), end + 200)
        context = text[context_start:context_end]
        
        # Look for complete address components
        lines = context.split('\n')
        address_lines = []
        
        for line in lines:
            line = line.strip()
            if self._looks_like_address_line(line):
                address_lines.append(line)
        
        if address_lines:
            return ' '.join(address_lines)
        
        # Fallback to original match
        return text[start:end].strip()
    
    def _looks_like_address_line(self, line: str) -> bool:
        """Check if a line looks like part of an address"""
        if len(line) < 5 or len(line) > 100:
            return False
        
        # Check for address indicators
        address_indicators = [
            r'\b\d+\s+\w+',  # Number + word
            r'\bsuite\b|\bfloor\b|\bunit\b',  # Suite/floor/unit
            r'\b[A-Za-z]+,\s*[A-Z]{2}\b',  # City, ST
            r'\b\d{5}\b',  # ZIP code
        ]
        
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in address_indicators)
    
    def _extract_cities_and_states(self, text: str) -> Set[str]:
        """Extract cities and states from text"""
        cities_states = set()
        
        # Pattern: City, State
        pattern = r'\b([A-Za-z\s]+),\s*([A-Z]{2}|[A-Za-z\s]+)\b'
        matches = re.finditer(pattern, text)
        
        for match in matches:
            city, state = match.groups()
            city = city.strip()
            state = state.strip().lower()
            
            # Validate state
            if state in self.us_states or state in self.state_abbreviations:
                cities_states.add(f"{city}, {state.upper()}")
        
        return cities_states
    
    def _extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        phone_numbers = []
        
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text)
            phone_numbers.extend(matches)
        
        # Clean and deduplicate
        cleaned = []
        seen = set()
        
        for phone in phone_numbers:
            # Remove formatting
            clean_phone = re.sub(r'[^\d]', '', phone)
            if len(clean_phone) >= 10 and clean_phone not in seen:
                seen.add(clean_phone)
                cleaned.append(phone)
        
        return cleaned
    
    def _determine_primary_location(self, addresses: List[Dict], cities_states: Set[str]) -> Optional[Dict]:
        """Determine the primary/headquarters location"""
        
        if not addresses and not cities_states:
            return None
        
        # Prefer structured addresses
        if addresses:
            # Look for headquarters indicators
            for addr in addresses:
                addr_text = addr.get('full_address', '').lower()
                if any(keyword in addr_text for keyword in ['headquarters', 'hq', 'corporate']):
                    return {
                        'address': addr['full_address'],
                        'type': 'headquarters',
                        'confidence': 0.9
                    }
            
            # Return first address if no HQ found
            return {
                'address': addresses[0]['full_address'],
                'type': 'primary',
                'confidence': 0.7
            }
        
        # Fallback to city/state
        if cities_states:
            return {
                'address': list(cities_states)[0],
                'type': 'city_state',
                'confidence': 0.5
            }
        
        return None
    
    def _calculate_confidence(self, addresses: List, phone_numbers: List, cities_states: Set) -> float:
        """Calculate overall extraction confidence"""
        confidence = 0.0
        
        if addresses:
            confidence += 0.4
        if phone_numbers:
            confidence += 0.2
        if cities_states:
            confidence += 0.2
        
        # Bonus for multiple sources
        sources = sum([bool(addresses), bool(phone_numbers), bool(cities_states)])
        if sources >= 2:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _format_structured_address(self, address_data: Dict) -> Dict:
        """Format structured address data"""
        if isinstance(address_data, str):
            return {
                'full_address': address_data,
                'confidence': 0.9,
                'type': 'structured'
            }
        
        # Build full address from components
        components = []
        if address_data.get('streetAddress'):
            components.append(address_data['streetAddress'])
        if address_data.get('addressLocality'):
            components.append(address_data['addressLocality'])
        if address_data.get('addressRegion'):
            components.append(address_data['addressRegion'])
        if address_data.get('postalCode'):
            components.append(address_data['postalCode'])
        
        return {
            'full_address': ', '.join(components),
            'confidence': 0.9,
            'type': 'structured',
            'components': address_data
        }
    
    def _extract_microdata_address(self, element) -> Optional[Dict]:
        """Extract address from microdata markup"""
        try:
            address_parts = []
            
            # Look for address components
            street = element.find(attrs={"itemprop": "streetAddress"})
            if street:
                address_parts.append(street.get_text().strip())
            
            city = element.find(attrs={"itemprop": "addressLocality"})
            if city:
                address_parts.append(city.get_text().strip())
            
            state = element.find(attrs={"itemprop": "addressRegion"})
            if state:
                address_parts.append(state.get_text().strip())
            
            postal = element.find(attrs={"itemprop": "postalCode"})
            if postal:
                address_parts.append(postal.get_text().strip())
            
            if address_parts:
                return {
                    'full_address': ', '.join(address_parts),
                    'confidence': 0.9,
                    'type': 'microdata'
                }
            
        except Exception as e:
            logger.debug(f"Failed to extract microdata address: {e}")
        
        return None
    
    def _empty_location_result(self) -> Dict:
        """Return empty location result"""
        return {
            'addresses': [],
            'phone_numbers': [],
            'cities_states': [],
            'primary_location': None,
            'structured_data': None,
            'extraction_confidence': 0.0,
            'source_url': ''
        }