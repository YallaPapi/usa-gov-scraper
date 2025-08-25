"""
Dynamic Agent Factory for creating specialized agents as needed
These agents are created on-demand to handle specific tasks during scraping.
"""

from agency_swarm import Agent
from agency_swarm.tools import BaseTool
from pydantic import Field
from typing import List, Dict, Any, Optional
import json
import time
from urllib.parse import urlparse, urljoin
import re


class DynamicAgentFactory:
    """Factory for creating specialized agents dynamically."""
    
    @staticmethod
    def create_agent(agent_type: str, **kwargs) -> Agent:
        """Create a new agent of the specified type with given parameters."""
        if agent_type == "normalizer":
            return URLNormalizerAgent(**kwargs)
        elif agent_type == "retry":
            return RetryHandlerAgent(**kwargs)
        elif agent_type == "deduplicator":
            return DeduplicatorAgent(**kwargs)
        elif agent_type == "dom_explorer":
            return DOMExplorerAgent(**kwargs)
        elif agent_type == "logger":
            return LoggerAgent(**kwargs)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")


class URLNormalizerAgent(Agent):
    """Agent responsible for cleaning and standardizing URLs."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="URL Normalizer",
            description="Cleans and standardizes URLs to ensure consistency.",
            instructions="""
            You are the URL Normalizer Agent responsible for:
            1. Standardizing URL formats across all agencies
            2. Resolving relative URLs to absolute URLs
            3. Removing tracking parameters and fragments
            4. Ensuring HTTPS is used where available
            5. Validating URL structure
            
            Normalization rules:
            - Convert relative URLs to absolute
            - Remove trailing slashes
            - Remove URL fragments (#)
            - Remove common tracking parameters
            - Ensure proper URL encoding
            - Prefer HTTPS over HTTP
            """,
            tools=[NormalizeURLsTool],
            temperature=0.1,
            max_prompt_tokens=10000
        )


class RetryHandlerAgent(Agent):
    """Agent responsible for retrying failed scrapes with exponential backoff."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="Retry Handler",
            description="Retries failed scraping operations with intelligent backoff strategies.",
            instructions="""
            You are the Retry Handler Agent responsible for:
            1. Retrying failed scraping attempts
            2. Implementing exponential backoff strategies
            3. Detecting different types of failures
            4. Adjusting retry strategies based on error types
            5. Reporting persistent failures
            
            Retry strategies:
            - Network errors: Exponential backoff with jitter
            - Rate limiting: Longer delays between retries
            - Server errors (5xx): Wait and retry
            - Client errors (4xx): Don't retry, report issue
            - Timeouts: Increase timeout and retry
            
            Max retries: 3 attempts
            Base delay: 2 seconds
            Max delay: 60 seconds
            """,
            tools=[RetryScrapeTool],
            temperature=0.2,
            max_prompt_tokens=10000
        )


class DeduplicatorAgent(Agent):
    """Agent responsible for removing duplicate agency entries."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="Deduplicator",
            description="Identifies and removes duplicate agency entries from the dataset.",
            instructions="""
            You are the Deduplicator Agent responsible for:
            1. Identifying duplicate agency entries
            2. Merging duplicate records intelligently
            3. Preserving the most complete information
            4. Handling variations in agency names
            5. Reporting deduplication statistics
            
            Deduplication strategies:
            - Exact name and URL matches
            - Fuzzy name matching with same domain
            - URL normalization before comparison
            - Preserve record with most complete data
            - Keep parent department information
            """,
            tools=[RemoveDuplicatesTool],
            temperature=0.1,
            max_prompt_tokens=10000
        )


class DOMExplorerAgent(Agent):
    """Agent responsible for exploring DOM structure when selectors change."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="DOM Explorer",
            description="Probes and analyzes website DOM structure to adapt to changes.",
            instructions="""
            You are the DOM Explorer Agent responsible for:
            1. Analyzing page DOM structure
            2. Finding alternative selectors when primary ones fail
            3. Detecting structural changes in the website
            4. Suggesting new scraping strategies
            5. Documenting DOM patterns
            
            Exploration strategies:
            - Use multiple selector strategies (CSS, XPath)
            - Identify patterns in class names and IDs
            - Find semantic HTML5 elements
            - Detect ARIA labels and roles
            - Analyze data attributes
            """,
            tools=[ExploreDOMTool],
            temperature=0.3,
            max_prompt_tokens=15000
        )


class LoggerAgent(Agent):
    """Agent responsible for compiling scrape statistics and observability."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="Logger",
            description="Tracks and reports scraping progress and statistics.",
            instructions="""
            You are the Logger Agent responsible for:
            1. Tracking scraping progress in real-time
            2. Collecting performance metrics
            3. Recording errors and warnings
            4. Generating summary statistics
            5. Creating detailed activity logs
            
            Metrics to track:
            - Agencies scraped per section
            - Success/failure rates
            - Response times
            - Error types and frequencies
            - Data quality metrics
            - Agent activity statistics
            """,
            tools=[LogActivityTool],
            temperature=0.1,
            max_prompt_tokens=10000
        )


# Tool definitions for dynamic agents

class NormalizeURLsTool(BaseTool):
    """
    Normalizes and standardizes a list of URLs.
    Converts relative URLs to absolute, removes fragments, and ensures consistency.
    """
    
    urls: List[Dict[str, Any]] = Field(
        ..., 
        description="List of agency records with URLs to normalize"
    )
    base_url: str = Field(
        default="https://www.usa.gov",
        description="Base URL for resolving relative URLs"
    )
    
    def run(self):
        """Normalize all URLs in the dataset."""
        normalized_records = []
        changes_made = 0
        
        for record in self.urls:
            original_url = record.get('homepage_url', '')
            normalized_url = self._normalize_url(original_url)
            
            if original_url != normalized_url:
                changes_made += 1
            
            record['homepage_url'] = normalized_url
            normalized_records.append(record)
        
        result = {
            'total_records': len(self.urls),
            'urls_normalized': changes_made,
            'normalized_records': normalized_records
        }
        
        return json.dumps(result, indent=2)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize a single URL."""
        if not url:
            return url
        
        # Remove whitespace
        url = url.strip()
        
        # Convert relative to absolute
        if not url.startswith(('http://', 'https://')):
            if url.startswith('/'):
                url = urljoin(self.base_url, url)
            else:
                url = 'https://' + url
        
        # Parse URL
        parsed = urlparse(url)
        
        # Remove fragment
        url = url.split('#')[0]
        
        # Remove common tracking parameters
        if '?' in url:
            base, params = url.split('?', 1)
            clean_params = []
            for param in params.split('&'):
                key = param.split('=')[0]
                if key not in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']:
                    clean_params.append(param)
            if clean_params:
                url = base + '?' + '&'.join(clean_params)
            else:
                url = base
        
        # Remove trailing slash
        if url.endswith('/') and url != 'https://':
            url = url[:-1]
        
        return url


class RetryScrapeTool(BaseTool):
    """
    Retries a failed scraping operation with exponential backoff.
    Implements intelligent retry strategies based on failure type.
    """
    
    failed_item: Dict[str, Any] = Field(
        ..., 
        description="The failed scraping item with error details"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts"
    )
    base_delay: float = Field(
        default=2.0,
        description="Base delay in seconds for exponential backoff"
    )
    
    def run(self):
        """Retry the failed scraping operation."""
        import requests
        from bs4 import BeautifulSoup
        
        url = self.failed_item.get('url', '')
        section_id = self.failed_item.get('section_id', '')
        error_type = self.failed_item.get('error_type', 'unknown')
        
        for attempt in range(self.max_retries):
            delay = self.base_delay * (2 ** attempt)  # Exponential backoff
            
            # Add jitter to prevent thundering herd
            import random
            delay += random.uniform(0, 1)
            
            time.sleep(delay)
            
            try:
                response = requests.get(
                    url or f"https://www.usa.gov/agency-index#{section_id}",
                    timeout=30 + (attempt * 10)  # Increase timeout with each retry
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Try to extract agencies
                    agencies = []
                    section = soup.find('section', {'id': section_id}) if section_id else soup
                    
                    if section:
                        for link in section.find_all('a', href=True):
                            agencies.append({
                                'agency_name': link.text.strip(),
                                'homepage_url': link['href'],
                                'parent_department': None
                            })
                    
                    return json.dumps({
                        'success': True,
                        'attempt': attempt + 1,
                        'agencies': agencies,
                        'agency_count': len(agencies)
                    }, indent=2)
                    
                elif response.status_code >= 500:
                    # Server error, worth retrying
                    continue
                else:
                    # Client error, don't retry
                    return json.dumps({
                        'success': False,
                        'error': f'HTTP {response.status_code}',
                        'attempt': attempt + 1,
                        'should_not_retry': True
                    })
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return json.dumps({
                        'success': False,
                        'error': str(e),
                        'max_retries_reached': True
                    })
        
        return json.dumps({
            'success': False,
            'error': 'Max retries exhausted'
        })


class RemoveDuplicatesTool(BaseTool):
    """
    Removes duplicate agency entries from the dataset.
    Uses multiple strategies to identify and merge duplicates.
    """
    
    data: List[Dict[str, Any]] = Field(
        ..., 
        description="List of agency records to deduplicate"
    )
    
    def run(self):
        """Remove duplicates from the dataset."""
        seen_urls = {}
        seen_names = {}
        unique_records = []
        duplicates_removed = 0
        
        for record in self.data:
            name = record.get('agency_name', '').strip().lower()
            url = record.get('homepage_url', '').strip().lower()
            
            # Create a composite key for comparison
            url_domain = urlparse(url).netloc if url else ''
            
            # Check for exact URL match
            if url and url in seen_urls:
                # Merge with existing record if this one has more info
                existing_idx = seen_urls[url]
                existing = unique_records[existing_idx]
                
                if not existing.get('parent_department') and record.get('parent_department'):
                    existing['parent_department'] = record['parent_department']
                
                duplicates_removed += 1
                continue
            
            # Check for exact name match with same domain
            if name and url_domain:
                name_key = f"{name}|{url_domain}"
                if name_key in seen_names:
                    duplicates_removed += 1
                    continue
            
            # Add to unique records
            if url:
                seen_urls[url] = len(unique_records)
            if name and url_domain:
                seen_names[f"{name}|{url_domain}"] = len(unique_records)
            
            unique_records.append(record)
        
        result = {
            'original_count': len(self.data),
            'unique_count': len(unique_records),
            'duplicates_removed': duplicates_removed,
            'unique_records': unique_records
        }
        
        return json.dumps(result, indent=2)


class ExploreDOMTool(BaseTool):
    """
    Explores the DOM structure of a page to find alternative selectors.
    Useful when the website structure changes.
    """
    
    url: str = Field(
        ..., 
        description="URL of the page to explore"
    )
    target_type: str = Field(
        default="agencies",
        description="Type of content to find (agencies, sections, etc.)"
    )
    
    def run(self):
        """Explore the DOM structure."""
        import requests
        from bs4 import BeautifulSoup
        
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            exploration_result = {
                'url': self.url,
                'selectors_found': {},
                'patterns_detected': [],
                'recommendations': []
            }
            
            # Try different selector strategies
            
            # 1. Semantic HTML5 elements
            semantic_elements = {
                'sections': len(soup.find_all('section')),
                'articles': len(soup.find_all('article')),
                'navs': len(soup.find_all('nav')),
                'mains': len(soup.find_all('main'))
            }
            exploration_result['selectors_found']['semantic'] = semantic_elements
            
            # 2. Common class patterns
            link_classes = {}
            for link in soup.find_all('a', href=True)[:20]:
                classes = link.get('class', [])
                for cls in classes:
                    link_classes[cls] = link_classes.get(cls, 0) + 1
            
            # Find most common link classes
            if link_classes:
                common_classes = sorted(link_classes.items(), key=lambda x: x[1], reverse=True)[:5]
                exploration_result['selectors_found']['common_link_classes'] = dict(common_classes)
            
            # 3. ID patterns
            id_patterns = []
            for elem in soup.find_all(id=True)[:50]:
                elem_id = elem.get('id')
                if len(elem_id) == 1 and elem_id.isalpha():
                    id_patterns.append(f"Single letter ID: {elem_id}")
            
            exploration_result['patterns_detected'] = list(set(id_patterns))
            
            # 4. Data attributes
            data_attrs = set()
            for elem in soup.find_all(True)[:100]:
                for attr in elem.attrs:
                    if attr.startswith('data-'):
                        data_attrs.add(attr)
            
            exploration_result['selectors_found']['data_attributes'] = list(data_attrs)[:10]
            
            # Generate recommendations
            if semantic_elements['sections'] > 20:
                exploration_result['recommendations'].append(
                    "Use 'section' elements with single-letter IDs for alphabetical sections"
                )
            
            if link_classes:
                exploration_result['recommendations'].append(
                    f"Try using links with class '{common_classes[0][0]}' for agency links"
                )
            
            return json.dumps(exploration_result, indent=2)
            
        except Exception as e:
            return json.dumps({
                'error': str(e),
                'url': self.url
            })


class LogActivityTool(BaseTool):
    """
    Logs agent activity and generates statistics.
    Tracks progress and performance metrics.
    """
    
    activity_type: str = Field(
        ..., 
        description="Type of activity (scrape_start, scrape_complete, error, etc.)"
    )
    details: Dict[str, Any] = Field(
        default={},
        description="Details about the activity"
    )
    
    _activity_log: List[Dict] = []  # Class variable to store logs
    
    def run(self):
        """Log the activity and return current statistics."""
        from datetime import datetime
        
        # Create log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'activity_type': self.activity_type,
            'details': self.details
        }
        
        # Add to activity log
        self._activity_log.append(log_entry)
        
        # Calculate statistics
        stats = {
            'total_activities': len(self._activity_log),
            'activity_types': {},
            'recent_activities': self._activity_log[-5:],  # Last 5 activities
        }
        
        # Count activity types
        for entry in self._activity_log:
            activity_type = entry['activity_type']
            stats['activity_types'][activity_type] = stats['activity_types'].get(activity_type, 0) + 1
        
        # Calculate specific metrics based on activity type
        if self.activity_type == 'scrape_complete':
            # Calculate success rate
            total_scrapes = stats['activity_types'].get('scrape_start', 0)
            successful_scrapes = stats['activity_types'].get('scrape_complete', 0)
            if total_scrapes > 0:
                stats['success_rate'] = f"{(successful_scrapes / total_scrapes) * 100:.1f}%"
        
        # Add current activity summary
        stats['current_activity'] = {
            'type': self.activity_type,
            'timestamp': log_entry['timestamp'],
            'summary': self._generate_summary(self.activity_type, self.details)
        }
        
        return json.dumps(stats, indent=2)
    
    def _generate_summary(self, activity_type: str, details: Dict) -> str:
        """Generate a human-readable summary of the activity."""
        if activity_type == 'scrape_start':
            return f"Started scraping section {details.get('section', 'unknown')}"
        elif activity_type == 'scrape_complete':
            return f"Completed scraping {details.get('count', 0)} agencies"
        elif activity_type == 'error':
            return f"Error occurred: {details.get('error', 'unknown error')}"
        elif activity_type == 'validation_complete':
            return f"Validated {details.get('valid', 0)} records, found {details.get('issues', 0)} issues"
        else:
            return f"{activity_type}: {details}"