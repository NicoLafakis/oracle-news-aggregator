#!/usr/bin/env python3
"""
Oracle News Aggregator
Pulls global events from multiple sources, deduplicates, and catalogs unique stories.
"""

import os
import sys
import json
import hashlib
import logging
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
import re

import requests
import feedparser
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Story:
    """Represents a single news story."""
    id: str                          # Unique hash ID
    title: str
    description: str
    content: str                     # Full content if available
    source: str
    source_url: str
    published_at: str                # ISO format
    fetched_at: str                  # ISO format
    category: str
    subcategory: Optional[str]
    keywords: list[str]
    location: Optional[str]          # Geographic location if applicable
    raw_data: dict                   # Original data from source


# =============================================================================
# CATEGORY DEFINITIONS
# =============================================================================

# =============================================================================
# ORACLE SEARCH QUERIES - The 100 Searches
# Curated keyword combinations for tracking signals that matter
# =============================================================================

ORACLE_SEARCHES = {
    "ai_machine_intelligence": {
        "name": "AI & Machine Intelligence",
        "searches": [
            "AI model release benchmark",
            "AI inference cost pricing",
            "AI lab hiring layoffs",
            "enterprise AI adoption deployment",
            "AI reasoning breakthrough",
            "AI agent autonomous",
            "AI regulation legislation passed",
            "AI safety alignment research",
            "foundation model training compute",
            "AI revenue earnings",
            "synthetic data training",
            "open source AI model release",
        ]
    },
    "robotics_automation": {
        "name": "Robotics & Physical Automation",
        "searches": [
            "humanoid robot production manufacturing",
            "robot cost price unit",
            "warehouse automation deployment",
            "autonomous vehicle approval deployment",
            "robot dexterity manipulation",
            "industrial automation orders",
        ]
    },
    "semiconductors_compute": {
        "name": "Semiconductors & Compute",
        "searches": [
            "chip fab construction investment",
            "GPU shortage supply",
            "semiconductor export controls",
            "TSMC Intel Samsung foundry",
            "AI chip startup funding",
            "energy data center power",
        ]
    },
    "energy_resources": {
        "name": "Energy & Resources",
        "searches": [
            "solar cost record low",
            "battery storage price",
            "nuclear plant approval construction",
            "fusion energy milestone",
            "oil production OPEC supply",
            "grid infrastructure investment",
            "critical mineral lithium cobalt",
            "energy demand growth forecast",
        ]
    },
    "macroeconomics_finance": {
        "name": "Macroeconomics & Finance",
        "searches": [
            "Federal Reserve interest rate decision",
            "inflation CPI data",
            "recession indicators yield curve",
            "sovereign debt crisis",
            "bank failure stress",
            "corporate debt default",
            "housing market prices inventory",
            "unemployment claims jobs report",
            "venture capital funding rounds",
            "IPO market activity",
            "cryptocurrency regulation adoption",
            "central bank digital currency CBDC",
        ]
    },
    "geopolitics_security": {
        "name": "Geopolitics & Security",
        "searches": [
            "US China relations tensions",
            "Taiwan strait military",
            "Russia NATO Ukraine",
            "Middle East conflict escalation",
            "nuclear weapons proliferation",
            "sanctions imposed lifted",
            "military spending defense budget",
            "cyber attack infrastructure",
            "alliance treaty agreement",
            "territorial dispute claims",
            "arms deal weapons sale",
            "coup election interference",
        ]
    },
    "politics_governance": {
        "name": "Politics & Governance",
        "searches": [
            "election results polling",
            "legislation passed bill signed",
            "Supreme Court ruling decision",
            "protest demonstration movement",
            "populist party gains",
            "regulatory agency action",
            "executive order policy",
            "constitutional crisis challenge",
        ]
    },
    "labor_employment": {
        "name": "Labor & Employment",
        "searches": [
            "layoffs job cuts announced",
            "automation replacing jobs workers",
            "union strike labor action",
            "wage growth increase",
            "remote work policy return office",
            "skills gap training workforce",
        ]
    },
    "demographics_migration": {
        "name": "Demographics & Migration",
        "searches": [
            "birth rate fertility decline",
            "immigration policy border",
            "aging population retirement",
            "urbanization migration cities",
            "brain drain talent migration",
        ]
    },
    "health_biotech": {
        "name": "Health & Biotech",
        "searches": [
            "pandemic outbreak disease",
            "drug approval FDA breakthrough",
            "longevity aging research",
            "mental health crisis",
            "healthcare costs spending",
            "gene therapy CRISPR trial",
            "antibiotic resistance superbug",
        ]
    },
    "climate_environment": {
        "name": "Climate & Environment",
        "searches": [
            "extreme weather disaster damage",
            "climate policy carbon emissions",
            "drought water shortage",
            "crop yield harvest agriculture",
            "species extinction biodiversity",
            "sea level rise flooding",
        ]
    },
    "space_frontier": {
        "name": "Space & Frontier",
        "searches": [
            "SpaceX Starship launch",
            "satellite constellation deployment",
            "space station commercial",
            "asteroid mining resource",
        ]
    },
    "media_information_trust": {
        "name": "Media, Information & Trust",
        "searches": [
            "misinformation disinformation campaign",
            "social media platform policy",
            "trust institutions polling",
            "journalism media layoffs",
            "deepfake synthetic media",
        ]
    },
    "culture_social": {
        "name": "Culture & Social Dynamics",
        "searches": [
            "consumer confidence sentiment",
            "social movement activism",
            "generational trends Gen Z",
            "religious trends affiliation",
            "education trends enrollment",
        ]
    },
}

# Legacy category mapping for story categorization
ORACLE_CATEGORIES = {
    "ai_machine_intelligence": {
        "keywords": ["AI", "artificial intelligence", "machine learning", "model", "LLM", 
                     "neural", "GPT", "Claude", "inference", "training", "foundation model"],
    },
    "robotics_automation": {
        "keywords": ["robot", "humanoid", "automation", "autonomous", "dexterity", "manufacturing"],
    },
    "semiconductors_compute": {
        "keywords": ["chip", "semiconductor", "GPU", "TSMC", "Intel", "foundry", "fab", "compute"],
    },
    "energy_resources": {
        "keywords": ["solar", "battery", "nuclear", "fusion", "oil", "OPEC", "grid", "lithium", "energy"],
    },
    "macroeconomics_finance": {
        "keywords": ["Federal Reserve", "inflation", "CPI", "recession", "debt", "bank", 
                     "housing", "unemployment", "venture capital", "IPO", "cryptocurrency", "CBDC"],
    },
    "geopolitics_security": {
        "keywords": ["China", "Taiwan", "Russia", "NATO", "Ukraine", "nuclear", "sanctions",
                     "military", "cyber", "alliance", "treaty", "arms"],
    },
    "politics_governance": {
        "keywords": ["election", "legislation", "Supreme Court", "protest", "populist",
                     "regulatory", "executive order", "constitutional"],
    },
    "labor_employment": {
        "keywords": ["layoffs", "job cuts", "automation", "union", "strike", "wage", 
                     "remote work", "skills gap", "workforce"],
    },
    "demographics_migration": {
        "keywords": ["birth rate", "fertility", "immigration", "aging", "urbanization", "brain drain"],
    },
    "health_biotech": {
        "keywords": ["pandemic", "FDA", "drug", "longevity", "mental health", "healthcare",
                     "gene therapy", "CRISPR", "antibiotic"],
    },
    "climate_environment": {
        "keywords": ["climate", "weather", "disaster", "carbon", "drought", "crop", 
                     "extinction", "biodiversity", "sea level"],
    },
    "space_frontier": {
        "keywords": ["SpaceX", "Starship", "satellite", "space station", "asteroid", "orbit"],
    },
    "media_information_trust": {
        "keywords": ["misinformation", "disinformation", "social media", "trust", "journalism", "deepfake"],
    },
    "culture_social": {
        "keywords": ["consumer confidence", "sentiment", "social movement", "Gen Z", "generational"],
    },
    "geological_events": {
        "keywords": ["earthquake", "volcano", "tsunami", "seismic", "magnitude", "eruption"],
        "usgs": True,
    },
}


# =============================================================================
# DEDUPLICATION ENGINE
# =============================================================================

class DeduplicationEngine:
    """Handles story deduplication using content hashing and semantic similarity."""
    
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        self.seen_hashes: set[str] = set()
        self.seen_titles: list[str] = []
        self.similarity_threshold = 0.75  # Titles must be <75% similar to be unique
        self._load_manifest()
    
    def _load_manifest(self):
        """Load existing manifest of seen stories."""
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r') as f:
                data = json.load(f)
                self.seen_hashes = set(data.get('hashes', []))
                self.seen_titles = data.get('titles', [])
            logger.info(f"Loaded manifest with {len(self.seen_hashes)} existing stories")
        else:
            logger.info("No existing manifest found, starting fresh")
    
    def save_manifest(self):
        """Save updated manifest with atomic write to prevent corruption."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first, then rename (atomic on most filesystems)
        temp_path = self.manifest_path.with_suffix('.json.tmp')
        try:
            with open(temp_path, 'w') as f:
                json.dump({
                    'hashes': list(self.seen_hashes),
                    'titles': self.seen_titles[-10000:],  # Keep last 10k titles for similarity
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
            # Atomic rename
            temp_path.replace(self.manifest_path)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def generate_hash(self, title: str, source: str, content: str = "") -> str:
        """Generate unique hash for a story."""
        # Normalize title
        normalized_title = self._normalize_text(title)
        
        # Create hash from normalized content
        hash_input = f"{normalized_title}|{source[:50]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
        text = re.sub(r'\s+', ' ', text)      # Normalize whitespace
        return text
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        t1 = self._normalize_text(title1)
        t2 = self._normalize_text(title2)
        return SequenceMatcher(None, t1, t2).ratio()
    
    def is_duplicate(self, story: Story) -> bool:
        """Check if story is a duplicate."""
        # Check exact hash match
        if story.id in self.seen_hashes:
            logger.debug(f"Exact hash match: {story.title[:50]}")
            return True
        
        # Check title similarity against recent titles
        normalized_title = self._normalize_text(story.title)
        for seen_title in self.seen_titles[-5000:]:  # Check last 5000
            similarity = self._title_similarity(story.title, seen_title)
            if similarity >= self.similarity_threshold:
                logger.debug(f"Similar title found ({similarity:.2%}): {story.title[:50]}")
                return True
        
        return False
    
    def mark_seen(self, story: Story):
        """Mark story as seen."""
        self.seen_hashes.add(story.id)
        self.seen_titles.append(story.title)


# =============================================================================
# NEWS SOURCES
# =============================================================================

class NewsAPIFetcher:
    """
    Fetch news from NewsAPI.org
    
    API Documentation: https://newsapi.org/docs
    
    IMPORTANT LIMITATIONS (Free Developer Tier):
    - 100 requests/day limit
    - Articles delayed by 24 hours
    - Content truncated to 200 chars
    - For development/testing ONLY (not production)
    
    For production use, upgrade to a paid plan.
    """
    
    BASE_URL = "https://newsapi.org/v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers['X-Api-Key'] = api_key
        self.request_count = 0
        self.max_requests = 100  # Free tier limit
    
    def _check_rate_limit(self) -> bool:
        """Check if we're approaching rate limit."""
        if self.request_count >= self.max_requests:
            logger.warning(f"NewsAPI rate limit reached ({self.max_requests} requests/day)")
            return False
        return True
    
    def fetch_everything(
        self, 
        query: str, 
        from_date: datetime, 
        to_date: Optional[datetime] = None,
        language: str = "en",
        sort_by: str = "publishedAt",
        page: int = 1
    ) -> list[dict]:
        """
        Fetch articles matching query using /v2/everything endpoint.
        
        Query supports advanced boolean operators:
        - Exact phrase: "artificial intelligence"
        - Must include: +bitcoin
        - Must exclude: -bitcoin
        - Boolean: crypto AND (ethereum OR litecoin) NOT bitcoin
        
        Args:
            query: Keywords/phrases (max 500 chars, will be URL-encoded)
            from_date: Oldest article date (ISO 8601)
            to_date: Newest article date (ISO 8601), defaults to now
            language: 2-letter ISO-639-1 code (ar,de,en,es,fr,he,it,nl,no,pt,ru,sv,ud,zh)
            sort_by: relevancy, popularity, or publishedAt
            page: Page number for pagination
        
        Returns:
            List of article dicts with: source, author, title, description, url, 
            urlToImage, publishedAt, content (truncated to 200 chars)
        """
        if not self._check_rate_limit():
            return []
        
        url = f"{self.BASE_URL}/everything"
        
        # Format dates per API spec (ISO 8601)
        params = {
            'q': query[:500],  # Max 500 chars
            'from': from_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'language': language,
            'sortBy': sort_by,
            'pageSize': 100,  # Max allowed
            'page': page,
        }
        
        if to_date:
            params['to'] = to_date.strftime('%Y-%m-%dT%H:%M:%S')
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            self.request_count += 1

            # Handle specific error codes
            if response.status_code == 401:
                logger.error("NewsAPI: Invalid API key")
                return []
            elif response.status_code == 426:
                logger.error("NewsAPI: Free tier cannot be used in production. Upgrade required.")
                return []
            elif response.status_code == 429:
                logger.error("NewsAPI: Rate limit exceeded")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'error':
                logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
            
            articles = data.get('articles', [])
            total = data.get('totalResults', 0)
            logger.info(f"NewsAPI: Found {total} total results for '{query[:30]}...', returned {len(articles)}")
            
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NewsAPI request error for '{query}': {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"NewsAPI JSON decode error: {e}")
            return []
    
    def fetch_top_headlines(
        self, 
        category: Optional[str] = None,
        country: str = "us",
        query: Optional[str] = None,
        sources: Optional[str] = None
    ) -> list[dict]:
        """
        Fetch top/breaking headlines using /v2/top-headlines endpoint.
        
        Note: Cannot mix 'sources' with 'country' or 'category' params.
        
        Args:
            category: business, entertainment, general, health, science, sports, technology
            country: 2-letter ISO 3166-1 country code
            query: Keywords to search in headlines
            sources: Comma-separated source IDs (cannot use with country/category)
        
        Returns:
            List of article dicts
        """
        if not self._check_rate_limit():
            return []
        
        url = f"{self.BASE_URL}/top-headlines"
        params = {'pageSize': 100}
        
        if sources:
            # Sources cannot be mixed with country/category
            params['sources'] = sources
        else:
            if country:
                params['country'] = country
            if category:
                params['category'] = category
        
        if query:
            params['q'] = query
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            self.request_count += 1
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'error':
                logger.error(f"NewsAPI headlines error: {data.get('message')}")
                return []

            return data.get('articles', [])
            
        except Exception as e:
            logger.error(f"NewsAPI headlines error for '{category}': {e}")
            return []
    
    def get_remaining_requests(self) -> int:
        """Return estimated remaining requests for today."""
        return max(0, self.max_requests - self.request_count)


class GDELTFetcher:
    """Fetch global events from GDELT Project (free, no API key)."""
    
    BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
    
    def fetch_events(self, query: str, timespan: str = "24h", max_records: int = 250) -> list[dict]:
        """Fetch events from GDELT."""
        params = {
            'query': query,
            'mode': 'artlist',
            'maxrecords': max_records,
            'timespan': timespan,
            'format': 'json',
            'sort': 'datedesc',
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('articles', [])
        except Exception as e:
            logger.error(f"GDELT error for '{query}': {e}")
            return []


class USGSFetcher:
    """Fetch earthquake data from USGS."""
    
    BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    
    def fetch_earthquakes(self, start_time: datetime, min_magnitude: float = 4.0) -> list[dict]:
        """Fetch significant earthquakes."""
        params = {
            'format': 'geojson',
            'starttime': start_time.isoformat(),
            'minmagnitude': min_magnitude,
            'orderby': 'time',
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('features', [])
        except Exception as e:
            logger.error(f"USGS error: {e}")
            return []


class RSSFetcher:
    """Fetch from RSS feeds - free, no limits!"""
    
    # Curated RSS feeds aligned with oracle categories
    FEEDS = {
        "ai_machine_intelligence": [
            "https://feeds.arstechnica.com/arstechnica/technology-lab",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.technologyreview.com/feed/",
            "https://blog.google/technology/ai/rss/",
        ],
        "robotics_automation": [
            "https://spectrum.ieee.org/feeds/topic/robotics",
            "https://www.therobotreport.com/feed/",
        ],
        "semiconductors_compute": [
            "https://feeds.arstechnica.com/arstechnica/gadgets",
            "https://www.anandtech.com/rss/",
        ],
        "energy_resources": [
            "https://www.renewableenergyworld.com/feed/",
            "https://cleantechnica.com/feed/",
        ],
        "macroeconomics_finance": [
            "https://feeds.bloomberg.com/markets/news.rss",
            "https://www.ft.com/?format=rss",
            "https://feeds.reuters.com/reuters/businessNews",
        ],
        "geopolitics_security": [
            "https://feeds.reuters.com/Reuters/worldNews",
            "https://www.foreignaffairs.com/rss.xml",
        ],
        "politics_governance": [
            "https://rss.politico.com/politics-news.xml",
            "https://feeds.npr.org/1014/rss.xml",
        ],
        "labor_employment": [
            "https://feeds.reuters.com/reuters/businessNews",
        ],
        "health_biotech": [
            "https://www.statnews.com/feed/",
            "https://www.sciencedaily.com/rss/health_medicine.xml",
        ],
        "climate_environment": [
            "https://www.sciencedaily.com/rss/earth_climate.xml",
            "https://grist.org/feed/",
        ],
        "space_frontier": [
            "https://www.nasa.gov/rss/dyn/breaking_news.rss",
            "https://spacenews.com/feed/",
            "https://www.space.com/feeds/all",
        ],
        "media_information_trust": [
            "https://www.niemanlab.org/feed/",
        ],
    }
    
    def fetch_feed(self, url: str, since: datetime) -> list[dict]:
        """Fetch and parse RSS feed."""
        try:
            feed = feedparser.parse(url)
            articles = []
            
            for entry in feed.entries:
                # Parse published date
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                
                # Skip old articles
                if published and published < since:
                    continue
                
                articles.append({
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', ''),
                    'url': entry.get('link', ''),
                    'published': published.isoformat() if published else None,
                    'source': feed.feed.get('title', url),
                })
            
            return articles
        except Exception as e:
            logger.error(f"RSS error for {url}: {e}")
            return []


# =============================================================================
# FIRECRAWL CONTENT ENRICHMENT
# =============================================================================

class FirecrawlContentFetcher:
    """
    Fetch full article content using Firecrawl API.

    Firecrawl extracts clean, readable content from web pages,
    perfect for enriching GDELT stories that only have titles/URLs.

    API Documentation: https://docs.firecrawl.dev/
    """

    BASE_URL = "https://api.firecrawl.dev/v1"

    def __init__(self, api_key: str, max_requests_per_run: int = 500):
        """
        Initialize Firecrawl fetcher.

        Args:
            api_key: Firecrawl API key
            max_requests_per_run: Max articles to enrich per run (to control costs)
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers['Authorization'] = f'Bearer {api_key}'
        self.session.headers['Content-Type'] = 'application/json'
        self.request_count = 0
        self.max_requests = max_requests_per_run
        self.success_count = 0
        self.error_count = 0

    def _check_rate_limit(self) -> bool:
        """Check if we should continue making requests."""
        if self.request_count >= self.max_requests:
            logger.warning(f"Firecrawl: Reached max requests limit ({self.max_requests})")
            return False
        return True

    def fetch_content(self, url: str, timeout: int = 30) -> Optional[dict]:
        """
        Scrape a single URL and extract clean content.

        Args:
            url: The URL to scrape
            timeout: Request timeout in seconds

        Returns:
            Dict with 'content' (markdown), 'title', 'description' or None on failure
        """
        if not self._check_rate_limit():
            return None

        if not url or not url.startswith('http'):
            return None

        try:
            response = self.session.post(
                f"{self.BASE_URL}/scrape",
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                    "timeout": timeout * 1000,  # API expects milliseconds
                },
                timeout=timeout + 10  # Add buffer for network latency
            )
            self.request_count += 1

            if response.status_code == 402:
                logger.error("Firecrawl: Payment required - check API credits")
                return None
            elif response.status_code == 429:
                logger.warning("Firecrawl: Rate limited, backing off...")
                time.sleep(2)
                return None
            elif response.status_code != 200:
                logger.debug(f"Firecrawl error {response.status_code} for {url[:50]}...")
                self.error_count += 1
                return None

            data = response.json()

            if not data.get('success'):
                self.error_count += 1
                return None

            result = data.get('data', {})
            markdown_content = result.get('markdown', '')
            metadata = result.get('metadata', {})

            # Extract first ~2000 chars of meaningful content
            content = markdown_content[:2000] if markdown_content else ''

            self.success_count += 1

            return {
                'content': content,
                'title': metadata.get('title', ''),
                'description': metadata.get('description', ''),
                'og_description': metadata.get('ogDescription', ''),
            }

        except requests.exceptions.Timeout:
            logger.debug(f"Firecrawl timeout for {url[:50]}...")
            self.error_count += 1
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Firecrawl request error: {e}")
            self.error_count += 1
            return None
        except json.JSONDecodeError:
            self.error_count += 1
            return None

    def enrich_stories(self, stories: list, priority_empty_content: bool = True) -> list:
        """
        Enrich a batch of stories with full content.

        Args:
            stories: List of Story objects to enrich
            priority_empty_content: If True, prioritize stories with empty content

        Returns:
            The same list with content fields populated where possible
        """
        if not stories:
            return stories

        # Sort to prioritize stories without content
        if priority_empty_content:
            stories_to_enrich = sorted(
                stories,
                key=lambda s: (len(s.content) > 0, s.published_at),
                reverse=False  # Empty content first, then oldest
            )
        else:
            stories_to_enrich = stories

        enriched_count = 0

        for story in stories_to_enrich:
            if not self._check_rate_limit():
                break

            # Skip if already has substantial content
            if len(story.content) > 200:
                continue

            # Skip non-HTTP URLs
            if not story.source_url or not story.source_url.startswith('http'):
                continue

            result = self.fetch_content(story.source_url)

            if result and result.get('content'):
                # Update story with fetched content
                story.content = result['content']

                # Update description if it was just a timestamp or empty
                if not story.description or story.description.startswith('20'):
                    story.description = (
                        result.get('description') or
                        result.get('og_description') or
                        result['content'][:200]
                    )

                enriched_count += 1

                # Small delay to be respectful to the API
                if enriched_count % 10 == 0:
                    time.sleep(0.5)

        logger.info(f"Firecrawl: Enriched {enriched_count} stories "
                   f"(success: {self.success_count}, errors: {self.error_count})")

        return stories

    def get_stats(self) -> dict:
        """Return enrichment statistics."""
        return {
            "requests_made": self.request_count,
            "successful": self.success_count,
            "errors": self.error_count,
            "remaining": self.max_requests - self.request_count,
        }


# =============================================================================
# STORY PROCESSOR
# =============================================================================

class StoryProcessor:
    """Process and categorize raw news data into Story objects."""
    
    def __init__(self):
        self.now = datetime.now(timezone.utc)
    
    def categorize(self, title: str, description: str) -> tuple[str, Optional[str]]:
        """Determine category based on content keywords."""
        text = f"{title} {description}".lower()
        
        scores = {}
        for category, config in ORACLE_CATEGORIES.items():
            score = sum(1 for kw in config.get('keywords', []) if kw.lower() in text)
            if score > 0:
                scores[category] = score
        
        if not scores:
            return "general", None
        
        # Return highest scoring category
        best = max(scores, key=scores.get)
        return best, None
    
    def extract_keywords(self, title: str, description: str) -> list[str]:
        """Extract relevant keywords from content."""
        text = f"{title} {description}"
        keywords = set()
        
        for category, config in ORACLE_CATEGORIES.items():
            for kw in config.get('keywords', []):
                if kw.lower() in text.lower():
                    keywords.add(kw.lower())
        
        return list(keywords)[:15]  # Limit to 15 keywords
    
    def process_newsapi_article(self, article: dict, default_category: str) -> Optional[Story]:
        """Process NewsAPI article into Story."""
        if not article.get('title'):
            return None
        
        title = article['title']
        description = article.get('description') or ""
        content = article.get('content') or description
        
        category, subcategory = self.categorize(title, description)
        if category == "general":
            category = default_category
        
        story = Story(
            id=hashlib.sha256(f"{title}|{article.get('source', {}).get('name', '')}".encode()).hexdigest()[:16],
            title=title,
            description=description,
            content=content,
            source=article.get('source', {}).get('name', 'Unknown'),
            source_url=article.get('url', ''),
            published_at=article.get('publishedAt', self.now.isoformat()),
            fetched_at=self.now.isoformat(),
            category=category,
            subcategory=subcategory,
            keywords=self.extract_keywords(title, description),
            location=None,
            raw_data=article,
        )
        return story
    
    def process_gdelt_article(self, article: dict) -> Optional[Story]:
        """Process GDELT article into Story."""
        if not article.get('title'):
            return None
        
        title = article['title']
        description = article.get('seendate', '')
        
        category, subcategory = self.categorize(title, description)
        
        story = Story(
            id=hashlib.sha256(f"{title}|{article.get('domain', '')}".encode()).hexdigest()[:16],
            title=title,
            description=description,
            content="",
            source=article.get('domain', 'Unknown'),
            source_url=article.get('url', ''),
            published_at=article.get('seendate', self.now.isoformat()),
            fetched_at=self.now.isoformat(),
            category=category,
            subcategory=subcategory,
            keywords=self.extract_keywords(title, description),
            location=article.get('sourcecountry'),
            raw_data=article,
        )
        return story
    
    def process_usgs_earthquake(self, feature: dict) -> Optional[Story]:
        """Process USGS earthquake into Story."""
        props = feature.get('properties', {})
        
        title = props.get('title', 'Unknown Earthquake')
        magnitude = props.get('mag', 0)
        place = props.get('place', 'Unknown location')
        
        description = f"Magnitude {magnitude} earthquake detected. Location: {place}"
        
        # Convert timestamp with validation
        time_ms = props.get('time')
        if time_ms and time_ms > 0:
            published = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
        else:
            published = self.now  # Fallback to fetch time if timestamp invalid
        
        story = Story(
            id=hashlib.sha256(f"{props.get('ids', '')}|usgs".encode()).hexdigest()[:16],
            title=title,
            description=description,
            content=f"Magnitude: {magnitude}\nDepth: {props.get('depth', 'unknown')}km\nLocation: {place}",
            source="USGS",
            source_url=props.get('url', ''),
            published_at=published.isoformat(),
            fetched_at=self.now.isoformat(),
            category="geological_events",
            subcategory="earthquake",
            keywords=["earthquake", "seismic", f"magnitude {int(magnitude)}"],
            location=place,
            raw_data=props,
        )
        return story
    
    def process_rss_article(self, article: dict, category: str) -> Optional[Story]:
        """Process RSS article into Story."""
        if not article.get('title'):
            return None
        
        title = article['title']
        description = article.get('description', '')
        
        story = Story(
            id=hashlib.sha256(f"{title}|{article.get('source', '')}".encode()).hexdigest()[:16],
            title=title,
            description=description,
            content=description,
            source=article.get('source', 'RSS'),
            source_url=article.get('url', ''),
            published_at=article.get('published', self.now.isoformat()),
            fetched_at=self.now.isoformat(),
            category=category,
            subcategory=None,
            keywords=self.extract_keywords(title, description),
            location=None,
            raw_data=article,
        )
        return story


# =============================================================================
# STORAGE
# =============================================================================

class OracleStorage:
    """Handle story storage in the repository."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.stories_path = base_path / "oracle" / "stories"
        self.logs_path = base_path / "logs"
    
    def save_story(self, story: Story):
        """Save a story to the appropriate location."""
        # Organize by date and category
        published = datetime.fromisoformat(story.published_at.replace('Z', '+00:00'))
        date_path = self.stories_path / published.strftime("%Y/%m/%d") / story.category
        date_path.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        story_file = date_path / f"{story.id}.json"
        with open(story_file, 'w') as f:
            json.dump(asdict(story), f, indent=2, default=str)
        
        logger.debug(f"Saved: {story.title[:50]}...")
    
    def save_summary(self, summary: dict):
        """Save run summary."""
        self.logs_path.mkdir(parents=True, exist_ok=True)
        with open(self.logs_path / "run_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
    
    def create_daily_index(self, stories: list[Story], date: datetime):
        """Create a daily index file for easy reference."""
        date_path = self.stories_path / date.strftime("%Y/%m/%d")
        date_path.mkdir(parents=True, exist_ok=True)
        
        index = {
            "date": date.strftime("%Y-%m-%d"),
            "total_stories": len(stories),
            "by_category": {},
            "stories": []
        }
        
        for story in stories:
            if story.category not in index["by_category"]:
                index["by_category"][story.category] = 0
            index["by_category"][story.category] += 1
            
            index["stories"].append({
                "id": story.id,
                "title": story.title,
                "category": story.category,
                "source": story.source,
                "published_at": story.published_at,
            })
        
        with open(date_path / "index.json", 'w') as f:
            json.dump(index, f, indent=2)


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class OracleAggregator:
    """Main orchestrator for news aggregation."""
    
    def __init__(self, base_path: Path, hours_lookback: int = 24):
        self.base_path = base_path
        self.hours_lookback = hours_lookback
        self.since = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)
        
        # Initialize components
        self.dedup = DeduplicationEngine(base_path / "oracle" / "manifest.json")
        self.processor = StoryProcessor()
        self.storage = OracleStorage(base_path)
        
        # Initialize fetchers
        self.newsapi = None
        if os.getenv('NEWS_API_KEY'):
            self.newsapi = NewsAPIFetcher(os.getenv('NEWS_API_KEY'))
        
        self.gdelt = GDELTFetcher()
        self.usgs = USGSFetcher()
        self.rss = RSSFetcher()

        # Initialize Firecrawl for content enrichment (optional)
        self.firecrawl = None
        if os.getenv('FIRECRAWL_API_KEY'):
            # Default to 500 requests per run - adjust based on your plan
            max_enrichments = int(os.getenv('FIRECRAWL_MAX_REQUESTS', '500'))
            self.firecrawl = FirecrawlContentFetcher(
                os.getenv('FIRECRAWL_API_KEY'),
                max_requests_per_run=max_enrichments
            )
            logger.info(f"Firecrawl enabled (max {max_enrichments} enrichments per run)")

        # Stats
        self.stats = {
            "total_fetched": 0,
            "total_new": 0,
            "duplicates_filtered": 0,
            "by_category": {},
            "by_source": {},
        }
    
    def run(self):
        """Execute the full aggregation pipeline."""
        logger.info(f"Starting Oracle aggregation (lookback: {self.hours_lookback}h)")
        logger.info(f"Fetching stories since: {self.since.isoformat()}")
        
        all_stories = []
        
        # 1. Fetch from NewsAPI (if available)
        if self.newsapi:
            logger.info("Fetching from NewsAPI...")
            all_stories.extend(self._fetch_newsapi())
        else:
            logger.warning("NewsAPI key not set, skipping NewsAPI")
        
        # 2. Fetch from GDELT (always available)
        if os.getenv('GDELT_ENABLED', 'true').lower() == 'true':
            logger.info("Fetching from GDELT...")
            all_stories.extend(self._fetch_gdelt())
        
        # 3. Fetch from USGS (geological events)
        logger.info("Fetching from USGS...")
        all_stories.extend(self._fetch_usgs())
        
        # 4. Fetch from RSS feeds
        logger.info("Fetching from RSS feeds...")
        all_stories.extend(self._fetch_rss())
        
        # 5. Deduplicate
        logger.info(f"Deduplicating {len(all_stories)} stories...")
        unique_stories = self._deduplicate(all_stories)

        # 6. Enrich content with Firecrawl (if available)
        if self.firecrawl and unique_stories:
            logger.info(f"Enriching {len(unique_stories)} stories with Firecrawl...")
            unique_stories = self.firecrawl.enrich_stories(unique_stories)
            # Add Firecrawl stats to our stats
            fc_stats = self.firecrawl.get_stats()
            self.stats["firecrawl"] = fc_stats
        else:
            if not self.firecrawl:
                logger.info("Firecrawl not configured, skipping content enrichment")

        # 7. Store
        logger.info(f"Storing {len(unique_stories)} unique stories...")
        for story in unique_stories:
            self.storage.save_story(story)
            self._update_stats(story)

        # 8. Create daily index
        if unique_stories:
            self.storage.create_daily_index(unique_stories, datetime.now(timezone.utc))

        # 9. Save manifest and summary
        self.dedup.save_manifest()
        self.storage.save_summary(self.stats)
        
        logger.info(f"Complete! {self.stats['total_new']} new stories, "
                   f"{self.stats['duplicates_filtered']} duplicates filtered")
        
        return unique_stories
    
    def _fetch_newsapi(self) -> list[Story]:
        """
        Fetch from NewsAPI using the curated 100 searches.
        
        Each search uses 1 API request. With 100 requests/day limit,
        we execute all searches in a single daily run.
        """
        stories = []
        total_searches = 0
        
        # Count total searches available
        for category_key, category_data in ORACLE_SEARCHES.items():
            total_searches += len(category_data['searches'])
        
        logger.info(f"NewsAPI: Starting {total_searches} curated searches")
        
        searches_completed = 0
        
        for category_key, category_data in ORACLE_SEARCHES.items():
            category_name = category_data['name']
            
            for search_query in category_data['searches']:
                # Check rate limit before each request
                remaining = self.newsapi.get_remaining_requests()
                if remaining <= 0:
                    logger.warning(f"NewsAPI: Rate limit reached after {searches_completed} searches")
                    break
                
                # Execute search
                articles = self.newsapi.fetch_everything(
                    query=search_query,
                    from_date=self.since,
                    language='en',
                    sort_by='publishedAt'
                )
                
                searches_completed += 1
                
                # Process articles
                for article in articles:
                    story = self.processor.process_newsapi_article(article, category_key)
                    if story:
                        # Add search context to story
                        story.keywords.append(f"search:{search_query[:30]}")
                        stories.append(story)
                
                # Log progress every 10 searches
                if searches_completed % 10 == 0:
                    logger.info(f"NewsAPI: {searches_completed}/{total_searches} searches complete, "
                               f"{len(stories)} stories collected")
            
            # Break outer loop if rate limited
            if self.newsapi.get_remaining_requests() <= 0:
                break
        
        logger.info(f"NewsAPI: Completed {searches_completed} searches, "
                   f"collected {len(stories)} stories, "
                   f"{self.newsapi.get_remaining_requests()} requests remaining")
        
        return stories
    
    def _fetch_gdelt(self) -> list[Story]:
        """
        Fetch from GDELT for global events - no API limits!
        
        GDELT is free and unlimited, so we can query more broadly here
        to supplement the NewsAPI searches.
        """
        stories = []
        
        # GDELT queries aligned with oracle categories
        # These complement NewsAPI with global event monitoring
        gdelt_queries = [
            # Geopolitics (GDELT's strength)
            ("US China tensions", "geopolitics_security"),
            ("Taiwan military", "geopolitics_security"),
            ("Russia Ukraine NATO", "geopolitics_security"),
            ("Middle East conflict", "geopolitics_security"),
            ("sanctions imposed", "geopolitics_security"),
            ("nuclear proliferation", "geopolitics_security"),
            ("cyber attack", "geopolitics_security"),
            
            # Macroeconomics
            ("Federal Reserve interest rate", "macroeconomics_finance"),
            ("inflation CPI", "macroeconomics_finance"),
            ("bank failure", "macroeconomics_finance"),
            ("recession indicators", "macroeconomics_finance"),
            
            # Energy
            ("oil OPEC production", "energy_resources"),
            ("solar energy record", "energy_resources"),
            ("nuclear power plant", "energy_resources"),
            
            # Climate & Disasters
            ("extreme weather disaster", "climate_environment"),
            ("climate policy emissions", "climate_environment"),
            ("drought water crisis", "climate_environment"),
            
            # Politics
            ("election results", "politics_governance"),
            ("legislation passed", "politics_governance"),
            ("protest demonstration", "politics_governance"),
            
            # Labor
            ("layoffs announced", "labor_employment"),
            ("strike union", "labor_employment"),
            
            # Health
            ("pandemic outbreak", "health_biotech"),
            ("FDA drug approval", "health_biotech"),
            
            # AI & Tech (supplement NewsAPI)
            ("artificial intelligence breakthrough", "ai_machine_intelligence"),
            ("autonomous vehicle", "robotics_automation"),
            ("semiconductor chip", "semiconductors_compute"),
            
            # Space
            ("SpaceX launch", "space_frontier"),
            ("satellite deployment", "space_frontier"),
        ]
        
        for query, category in gdelt_queries:
            articles = self.gdelt.fetch_events(query, max_records=100)
            for article in articles:
                story = self.processor.process_gdelt_article(article)
                if story:
                    story.category = category  # Override with our category
                    stories.append(story)
        
        logger.info(f"GDELT: Fetched {len(stories)} stories from {len(gdelt_queries)} queries")
        return stories
    
    def _fetch_usgs(self) -> list[Story]:
        """Fetch earthquake data from USGS."""
        stories = []
        features = self.usgs.fetch_earthquakes(self.since, min_magnitude=4.0)
        
        for feature in features:
            story = self.processor.process_usgs_earthquake(feature)
            if story:
                stories.append(story)
        
        return stories
    
    def _fetch_rss(self) -> list[Story]:
        """Fetch from RSS feeds."""
        stories = []
        
        for category, feeds in RSSFetcher.FEEDS.items():
            for feed_url in feeds:
                articles = self.rss.fetch_feed(feed_url, self.since)
                for article in articles:
                    story = self.processor.process_rss_article(article, category)
                    if story:
                        stories.append(story)
        
        return stories
    
    def _deduplicate(self, stories: list[Story]) -> list[Story]:
        """Remove duplicate stories."""
        unique = []
        
        for story in stories:
            self.stats["total_fetched"] += 1
            
            if self.dedup.is_duplicate(story):
                self.stats["duplicates_filtered"] += 1
                continue
            
            self.dedup.mark_seen(story)
            unique.append(story)
        
        return unique
    
    def _update_stats(self, story: Story):
        """Update statistics."""
        self.stats["total_new"] += 1
        
        if story.category not in self.stats["by_category"]:
            self.stats["by_category"][story.category] = 0
        self.stats["by_category"][story.category] += 1
        
        if story.source not in self.stats["by_source"]:
            self.stats["by_source"][story.source] = 0
        self.stats["by_source"][story.source] += 1


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Oracle News Aggregator")
    parser.add_argument('--hours', type=int, default=24, 
                       help='Hours to look back for news (default: 24)')
    parser.add_argument('--path', type=str, default='.', 
                       help='Base path for repository')
    args = parser.parse_args()
    
    base_path = Path(args.path).resolve()
    
    aggregator = OracleAggregator(base_path, args.hours)
    stories = aggregator.run()
    
    print(f"\n{'='*60}")
    print(f"Oracle Aggregation Complete")
    print(f"{'='*60}")
    print(f"New Stories: {len(stories)}")
    print(f"By Category:")
    for cat, count in aggregator.stats['by_category'].items():
        print(f"  - {cat}: {count}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
