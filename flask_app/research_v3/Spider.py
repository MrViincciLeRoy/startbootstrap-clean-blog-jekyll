


import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse, quote_plus
from typing import List, Dict, Optional, Set
import json
from dataclasses import dataclass
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Source:
    text: str
    metadata: Dict
    url: str
    title: str
    reliability_score: float

class EnhancedPlantSpider:
    def __init__(self, delay: float = 1.5, max_sources: int = 10, articles_per_search: int = 3):
        """
        Initialize the Enhanced Plant Spider for RAG system

        Args:
            delay: Delay between requests in seconds
            max_sources: Maximum number of sources to collect
            articles_per_search: Number of articles to extract from each search page
        """
        self.delay = delay
        self.max_sources = max_sources
        self.articles_per_search = articles_per_search
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Trusted plant information sources with search patterns
        self.search_sources = {
            'thespruce.com': {
                'reliability': 0.75,
                'search_url': 'https://www.thespruce.com/search?q={query}',
                'article_selector': 'a[href*="/plants/"], a[href*="/gardening/"]',
                'title_selector': '.card-title, .comp.card-list__title',
            },
            'extension.wisc.edu': {
                'reliability': 0.85,
                'search_url': 'https://hort.extension.wisc.edu/articles/?s={query}',
                'article_selector': 'a[href*="/articles/"]',
                'title_selector': '.entry-title, h2',
            },
            'ces.ncsu.edu': {
                'reliability': 0.85,
                'search_url': 'https://plants.ces.ncsu.edu/find_a_plant/?q={query}',
                'article_selector': 'a[href*="/plants/"]',
                'title_selector': 'h1, .plant-name',
                'browse_mode': True  # This site works better with browsing than search
            },
            'britannica.com': {
                'reliability': 0.9,
                'search_url': 'https://www.britannica.com/search?query={query}',
                'article_selector': 'a[href*="/plant/"], a[href*="/topic/"]',
                'title_selector': '.title, h3',
            },
            'rhs.org.uk': {
                'reliability': 0.9,
                'search_url': 'https://www.rhs.org.uk/search?query={query}',
                'article_selector': 'a[href*="/plants/"]',
                'title_selector': '.plant-header__title, h2',
            },
            'extension.umn.edu': {
                'reliability': 0.85,
                'search_url': 'https://extension.umn.edu/search?q={query}',
                'article_selector': 'a[href*="/plants"], a[href*="/garden"]',
                'title_selector': '.search-result-title, h3',
            }
        }

        # Direct reliable sources (non-search)
        self.direct_sources = {
            'en.wikipedia.org': {'reliability': 0.95, 'weight': 1.5},
            'kew.org': {'reliability': 0.95, 'weight': 1.5},
            'powo.science.kew.org': {'reliability': 0.95, 'weight': 1.5},
            'missouribotanicalgarden.org': {'reliability': 0.9, 'weight': 1.3},
        }

    def get_search_urls_for_plant(self, plant_name: str) -> List[str]:
        """
        Generate search URLs for a plant across different botanical sites
        """
        search_urls = []
        query = quote_plus(plant_name)

        # Add search URLs from known sources
        for domain, config in self.search_sources.items():
            search_url = config['search_url'].format(query=query)
            search_urls.append(search_url)

        # Add direct Wikipedia attempts (these often work)
        wiki_variations = [
            f"https://en.wikipedia.org/wiki/{plant_name.replace(' ', '_')}",
        ]

        # Add genus page if binomial name
        genus_species = plant_name.split()
        if len(genus_species) >= 2:
            genus = genus_species[0]
            wiki_variations.append(f"https://en.wikipedia.org/wiki/{genus}")

        search_urls.extend(wiki_variations)

        return search_urls

    def extract_article_links_from_search(self, search_url: str, plant_name: str) -> List[Dict[str, str]]:
        """
        Extract article links from search result pages

        Returns:
            List of dicts with 'url' and 'title' keys
        """
        try:
            logger.info(f"Processing search page: {search_url}")
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            domain = urlparse(search_url).netloc

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()

            articles = []

            # Handle different site structures
            if 'thespruce.com' in domain:
                articles = self._extract_thespruce_links(soup, search_url, plant_name)
            elif 'extension.wisc.edu' in domain:
                articles = self._extract_extension_links(soup, search_url, plant_name)
            elif 'ces.ncsu.edu' in domain:
                articles = self._extract_ncsu_links(soup, search_url, plant_name)
            elif 'britannica.com' in domain:
                articles = self._extract_britannica_links(soup, search_url, plant_name)
            elif 'rhs.org.uk' in domain:
                articles = self._extract_rhs_links(soup, search_url, plant_name)
            else:
                # Generic extraction
                articles = self._extract_generic_search_links(soup, search_url, plant_name)

            # Filter and rank articles
            filtered_articles = self._filter_relevant_articles(articles, plant_name)

            logger.info(f"Found {len(filtered_articles)} relevant articles from {domain}")
            return filtered_articles[:self.articles_per_search]

        except Exception as e:
            logger.error(f"Error processing search page {search_url}: {str(e)}")
            return []

    def _extract_thespruce_links(self, soup: BeautifulSoup, base_url: str, plant_name: str) -> List[Dict[str, str]]:
        """Extract links from The Spruce search results"""
        articles = []

        # The Spruce uses different selectors for search results
        selectors = [
            'a[href*="/plants/"]',
            'a[href*="/gardening/"]',
            '.comp.card-list__item a',
            '.search-results a[href*="thespruce.com"]'
        ]

        for selector in selectors:
            links = soup.select(selector)
            for link in links[:10]:  # Limit to avoid too many
                href = link.get('href')
                if href and not href.startswith('javascript:'):
                    full_url = urljoin(base_url, href)
                    title = link.get_text(strip=True)

                    # Get title from nearby elements if link text is not descriptive
                    if not title or len(title) < 10:
                        parent = link.find_parent()
                        if parent:
                            title_elem = parent.find(['h2', 'h3', '.title', '.card-title'])
                            if title_elem:
                                title = title_elem.get_text(strip=True)

                    if title and href:
                        articles.append({'url': full_url, 'title': title})

            if articles:  # If we found articles with this selector, stop trying others
                break

        return articles

    def _extract_extension_links(self, soup: BeautifulSoup, base_url: str, plant_name: str) -> List[Dict[str, str]]:
        """Extract links from extension site search results"""
        articles = []

        # Extension sites often have article lists
        selectors = [
            'a[href*="/articles/"]',
            'a[href*="/plants/"]',
            '.search-result a',
            '.entry-title a',
            'h2 a, h3 a'
        ]

        for selector in selectors:
            links = soup.select(selector)
            for link in links[:8]:
                href = link.get('href')
                title = link.get_text(strip=True)

                if href and title:
                    full_url = urljoin(base_url, href)
                    articles.append({'url': full_url, 'title': title})

            if articles:
                break

        return articles

    def _extract_ncsu_links(self, soup: BeautifulSoup, base_url: str, plant_name: str) -> List[Dict[str, str]]:
        """Extract links from NC State Extension plant database"""
        articles = []

        # NCSU plant database has specific structure
        selectors = [
            'a[href*="/plants/"]',
            '.plant-list a',
            '.search-results a',
            'td a',  # Sometimes in tables
            '.plant-name a'
        ]

        for selector in selectors:
            links = soup.select(selector)
            for link in links[:10]:
                href = link.get('href')
                title = link.get_text(strip=True)

                if href and title and len(title) > 3:
                    full_url = urljoin(base_url, href)
                    articles.append({'url': full_url, 'title': title})

        return articles

    def _extract_britannica_links(self, soup: BeautifulSoup, base_url: str, plant_name: str) -> List[Dict[str, str]]:
        """Extract links from Britannica search results"""
        articles = []

        # Britannica search result selectors
        selectors = [
            'a[href*="/plant/"]',
            'a[href*="/topic/"]',
            '.search-results a',
            '.title a',
            'h3 a'
        ]

        for selector in selectors:
            links = soup.select(selector)
            for link in links[:6]:
                href = link.get('href')
                title = link.get_text(strip=True)

                if href and title:
                    full_url = urljoin('https://www.britannica.com', href)
                    articles.append({'url': full_url, 'title': title})

            if articles:
                break

        return articles

    def _extract_rhs_links(self, soup: BeautifulSoup, base_url: str, plant_name: str) -> List[Dict[str, str]]:
        """Extract links from RHS search results"""
        articles = []

        selectors = [
            'a[href*="/plants/"]',
            '.search-result a',
            '.plant-search-result a',
            'h2 a, h3 a'
        ]

        for selector in selectors:
            links = soup.select(selector)
            for link in links[:8]:
                href = link.get('href')
                title = link.get_text(strip=True)

                if href and title:
                    full_url = urljoin(base_url, href)
                    articles.append({'url': full_url, 'title': title})

        return articles

    def _extract_generic_search_links(self, soup: BeautifulSoup, base_url: str, plant_name: str) -> List[Dict[str, str]]:
        """Generic extraction for unknown sites"""
        articles = []

        # Generic selectors that might work on various sites
        selectors = [
            'a[href*="plant"]',
            '.search-result a',
            '.result a',
            'h2 a, h3 a',
            '.title a',
            '.entry-title a'
        ]

        for selector in selectors:
            links = soup.select(selector)[:15]  # Limit to avoid noise
            for link in links:
                href = link.get('href')
                title = link.get_text(strip=True)

                if href and title and len(title) > 5:
                    # Skip obvious non-content links
                    if not any(skip in href.lower() for skip in ['contact', 'about', 'privacy', 'terms']):
                        full_url = urljoin(base_url, href)
                        articles.append({'url': full_url, 'title': title})

        return articles

    def _filter_relevant_articles(self, articles: List[Dict[str, str]], plant_name: str) -> List[Dict[str, str]]:
        """Filter and rank articles by relevance to the plant"""
        if not articles:
            return []

        plant_terms = plant_name.lower().split()
        genus = plant_terms[0] if plant_terms else ""

        scored_articles = []
        seen_urls = set()

        for article in articles:
            url = article['url']
            title = article['title'].lower()

            # Skip duplicates
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Calculate relevance score
            score = 0

            # Exact plant name match (highest score)
            if plant_name.lower() in title:
                score += 10

            # Genus match
            if genus and genus in title:
                score += 5

            # Individual term matches
            for term in plant_terms:
                if term in title:
                    score += 2

            # Plant-related keywords
            plant_keywords = ['plant', 'flower', 'tree', 'shrub', 'garden', 'cultivation', 'growing']
            for keyword in plant_keywords:
                if keyword in title:
                    score += 1

            # Prefer specific plant pages over general garden advice
            if any(specific in url.lower() for specific in ['/plants/', '/plant/', '/species/']):
                score += 3

            scored_articles.append((score, article))

        # Sort by score (highest first) and return articles
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        return [article for score, article in scored_articles if score > 0]

    def extract_plant_info(self, url: str) -> Optional[Source]:
        """
        Enhanced plant information extraction with better content detection
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', '.ad', '.advertisement']):
                element.decompose()

            # Extract title
            title = self._extract_title(soup, url)

            # Extract main content
            content = self._extract_content(soup, url)

            if not content or len(content.strip()) < 100:
                logger.debug(f"Insufficient content from {url} (length: {len(content) if content else 0})")
                return None

            # Calculate reliability score
            domain = urlparse(url).netloc
            reliability_score = self._calculate_reliability(domain, content)

            # Create metadata optimized for RAG system
            metadata = {
                'source': self._get_source_name(domain, title),
                'reliability': self._get_reliability_level(reliability_score),
                'url': url,
                'domain': domain,
                'title': title,
                'scraped_date': datetime.now().strftime('%Y-%m-%d'),
                'content_type': self._classify_content_type(content, url)
            }

            return Source(
                text=content,
                metadata=metadata,
                url=url,
                title=title,
                reliability_score=reliability_score
            )

        except Exception as e:
            logger.error(f"Error extracting from {url}: {str(e)}")
            return None

    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Enhanced title extraction"""
        # Try different title selectors in order of preference
        selectors = [
            'h1.plant-name',
            'h1.entry-title',
            'h1.title',
            '.plant-header__title',
            '.plant-title',
            'h1',
            'title'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                if title and len(title) > 3:
                    return title

        return "Unknown Plant"

    def _extract_content(self, soup: BeautifulSoup, url: str) -> str:
        """Enhanced content extraction with site-specific handling"""
        domain = urlparse(url).netloc

        if 'wikipedia.org' in domain:
            return self._extract_wikipedia_content(soup)
        elif 'thespruce.com' in domain:
            return self._extract_thespruce_content(soup)
        elif 'extension.wisc.edu' in domain or 'extension.' in domain:
            return self._extract_extension_content(soup)
        elif 'ces.ncsu.edu' in domain:
            return self._extract_ncsu_content(soup)
        elif 'britannica.com' in domain:
            return self._extract_britannica_content(soup)
        elif 'rhs.org.uk' in domain:
            return self._extract_rhs_content(soup)
        else:
            return self._extract_generic_content(soup)

    def _extract_thespruce_content(self, soup: BeautifulSoup) -> str:
        """Extract content from The Spruce articles"""
        content_parts = []

        # The Spruce article structure
        selectors = [
            '.comp.mntl-sc-block-html',
            '.comp.article-content p',
            '.content-block p',
            'article p',
            '.entry-content p'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:8]:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 30 and self._is_content_text(text):
                        content_parts.append(text)
                if len(content_parts) >= 3:
                    break

        return "\n\n".join(content_parts)

    def _extract_extension_content(self, soup: BeautifulSoup) -> str:
        """Extract content from extension articles"""
        content_parts = []

        selectors = [
            '.entry-content p',
            '.article-content p',
            '.content p',
            'main p',
            '#content p'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:10]:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 40 and self._is_content_text(text):
                        content_parts.append(text)
                if content_parts:
                    break

        return "\n\n".join(content_parts)

    def _extract_ncsu_content(self, soup: BeautifulSoup) -> str:
        """Extract content from NC State plant database"""
        content_parts = []

        # NCSU specific selectors
        selectors = [
            '.plant-description p',
            '.plant-details p',
            '.plant-info p',
            'td',  # Plant details often in tables
            '.content p',
            'p'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:12]:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 25 and self._is_content_text(text):
                        content_parts.append(text)
                if len(content_parts) >= 4:
                    break

        return "\n\n".join(content_parts)

    def _extract_wikipedia_content(self, soup: BeautifulSoup) -> str:
        """Extract content from Wikipedia pages"""
        content_parts = []

        content_div = soup.find('div', {'id': 'mw-content-text'})
        if content_div:
            paragraphs = content_div.find_all('p', recursive=True)[:10]

            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50:
                    content_parts.append(text)

        return "\n\n".join(content_parts)

    def _extract_britannica_content(self, soup: BeautifulSoup) -> str:
        """Extract content from Britannica articles"""
        content_parts = []

        article = soup.find('article') or soup.find('div', class_='article-content')
        if article:
            paragraphs = article.find_all('p')[:8]
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50 and self._is_content_text(text):
                    content_parts.append(text)

        return "\n\n".join(content_parts)

    def _extract_rhs_content(self, soup: BeautifulSoup) -> str:
        """Extract content from RHS articles"""
        content_parts = []

        selectors = [
            '.plant-description p',
            '.plant-summary p',
            '.content-area p',
            '.main-content p',
            'article p'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:6]:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 50 and self._is_content_text(text):
                        content_parts.append(text)
                if content_parts:
                    break

        return "\n\n".join(content_parts)

    def _extract_generic_content(self, soup: BeautifulSoup) -> str:
        """Enhanced generic content extraction"""
        content_parts = []

        # Try content-specific selectors first
        priority_selectors = [
            'article p',
            '.entry-content p',
            '.post-content p',
            '.content p',
            '.main-content p',
            '#content p'
        ]

        for selector in priority_selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:10]:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 40 and self._is_content_text(text):
                        content_parts.append(text)
                if len(content_parts) >= 3:
                    break

        # Fallback to all paragraphs
        if not content_parts:
            paragraphs = soup.find_all('p')
            for p in paragraphs[:20]:
                text = p.get_text(strip=True)
                if text and len(text) > 50 and self._is_content_text(text):
                    content_parts.append(text)
                if len(content_parts) >= 5:
                    break

        return "\n\n".join(content_parts[:8])

    def _is_content_text(self, text: str) -> bool:
        """Check if text is actual content vs navigation/ads"""
        text_lower = text.lower()

        # Skip navigation, ads, etc.
        skip_phrases = [
            'cookie', 'privacy', 'subscribe', 'newsletter', 'advertisement',
            'menu', 'navigation', 'share this', 'follow us', 'contact us',
            'terms of service', 'all rights reserved'
        ]

        return not any(phrase in text_lower for phrase in skip_phrases)

    def _calculate_reliability(self, domain: str, content: str) -> float:
        """Calculate reliability score"""
        base_score = 0.5

        # Check direct sources
        if domain in self.direct_sources:
            base_score = self.direct_sources[domain]['reliability']
        else:
            # Check search sources
            for search_domain, config in self.search_sources.items():
                if search_domain in domain:
                    base_score = config['reliability']
                    break

        # Content quality indicators
        content_lower = content.lower()

        if any(term in content_lower for term in ['scientific name', 'botanical', 'taxonomy']):
            base_score += 0.1

        if len(content) > 1000:
            base_score += 0.05

        return min(1.0, base_score)

    def _get_reliability_level(self, score: float) -> str:
        """Convert reliability score to level"""
        if score >= 0.9:
            return "very_high"
        elif score >= 0.8:
            return "high"
        elif score >= 0.7:
            return "medium"
        else:
            return "low"

    def collect_plant_sources(self, plant_name: str) -> List[Dict]:
        """
        Main method to collect sources using enhanced search-based approach
        """
        logger.info(f"Starting enhanced collection for: {plant_name}")

        search_urls = self.get_search_urls_for_plant(plant_name)

        all_article_links = []
        sources = []
        processed_urls = set()
        processed_domains = set()

        # Step 1: Extract article links from search pages
        for search_url in search_urls:
            if len(all_article_links) >= self.max_sources * 2:  # Get extra links to filter from
                break

            article_links = self.extract_article_links_from_search(search_url, plant_name)
            all_article_links.extend(article_links)

            time.sleep(self.delay)

        logger.info(f"Found {len(all_article_links)} total article links")

        # Step 2: Process article links to extract content
        for article in all_article_links:
            if len(sources) >= self.max_sources:
                break

            url = article['url']

            # Skip if already processed
            if url in processed_urls:
                continue

            # Limit to 2 articles per domain for diversity
            domain = urlparse(url).netloc
            domain_count = sum(1 for s in sources if urlparse(s['metadata']['url']).netloc == domain)
            if domain_count >= 2:
                continue

            processed_urls.add(url)

            logger.info(f"Processing article: {article['title'][:50]}...")

            try:
                source = self.extract_plant_info(url)
                if source and len(source.text.strip()) > 150:
                    # Create RAG-optimized source format
                    rag_source = {
                        "text": source.text,
                        "metadata": source.metadata
                    }
                    sources.append(rag_source)
                    logger.info(f"✓ Extracted content from {domain}")
                else:
                    logger.debug(f"✗ Insufficient content from {url}")

            except Exception as e:
                logger.debug(f"✗ Error processing {url}: {str(e)}")

            time.sleep(self.delay)

        # Sort by reliability for RAG system
        sources.sort(key=lambda x: self._get_rag_sort_score(x['metadata']), reverse=True)

        logger.info(f"Successfully collected {len(sources)} sources for {plant_name}")
        return sources

    def _get_source_name(self, domain: str, title: str) -> str:
        """Get a clean source name for RAG metadata"""
        source_names = {
            'en.wikipedia.org': 'Wikipedia',
            'www.britannica.com': 'Encyclopædia Britannica',
            'www.thespruce.com': 'The Spruce',
            'hort.extension.wisc.edu': 'Wisconsin Horticulture Extension',
            'plants.ces.ncsu.edu': 'NC State Extension Plants',
            'extension.umn.edu': 'University of Minnesota Extension',
            'www.rhs.org.uk': 'Royal Horticultural Society',
            'www.kew.org': 'Royal Botanic Gardens, Kew',
            'powo.science.kew.org': 'Plants of the World Online',
            'www.missouribotanicalgarden.org': 'Missouri Botanical Garden',
            'plants.usda.gov': 'USDA Plants Database',
            'plantnet.rbgsyd.nsw.gov.au': 'PlantNET'
        }

        return source_names.get(domain, title.split(' - ')[0] if ' - ' in title else domain.replace('www.', '').title())

    def _classify_content_type(self, content: str, url: str) -> str:
        """Classify the type of content for RAG context"""
        content_lower = content.lower()

        if any(term in content_lower for term in ['scientific name', 'botanical', 'taxonomy', 'genus', 'species']):
            return 'botanical_reference'
        elif any(term in content_lower for term in ['growing', 'planting', 'cultivation', 'care', 'garden']):
            return 'cultivation_guide'
        elif any(term in content_lower for term in ['native', 'habitat', 'distribution', 'ecology']):
            return 'ecological_information'
        elif any(term in content_lower for term in ['description', 'appearance', 'characteristics', 'features']):
            return 'plant_description'
        else:
            return 'general_information'

    def _get_rag_sort_score(self, metadata: Dict) -> float:
        """Get sorting score optimized for RAG system"""
        reliability_scores = {
            'very_high': 1.0,
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }

        base_score = reliability_scores.get(metadata.get('reliability', 'low'), 0.4)

        # Bonus for specific content types that are more informative
        content_type_bonus = {
            'botanical_reference': 0.2,
            'plant_description': 0.15,
            'cultivation_guide': 0.1,
            'ecological_information': 0.1,
            'general_information': 0.0
        }

        base_score += content_type_bonus.get(metadata.get('content_type', 'general_information'), 0.0)

        return min(1.0, base_score)

    def save_sources_for_rag(self, sources: List[Dict], filename: str, plant_name: str):
        """Save sources in RAG-optimized format with additional context"""
        rag_data = {
            "plant_name": plant_name,
            "collection_date": datetime.now().strftime('%Y-%m-%d'),
            "total_sources": len(sources),
            "sources": sources
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(rag_data, f, indent=2, ensure_ascii=False)

        # Also save just the sources array for direct RAG use
        sources_only_filename = filename.replace('.json', '_sources_only.json')
        with open(sources_only_filename, 'w', encoding='utf-8') as f:
            json.dump(sources, f, indent=2, ensure_ascii=False)

# Example usage
def search(name=None):
    # Initialize enhanced spider
    spider = EnhancedPlantSpider(delay=1.5, max_sources=8, articles_per_search=3)

    # Test with Rosa rubiginosa
    plant_name = name if name else "Rosa rubiginosa"
    sources = spider.collect_plant_sources(plant_name)

    # Save results
    filename = f"{plant_name.replace(' ', '_')}_enhanced_sources.json"
    spider.save_sources_for_rag(sources, filename, plant_name)

    # Print detailed summary
    print(f"\n{'='*60}")
    print(f"ENHANCED PLANT SPIDER RESULTS FOR: {plant_name}")
    print(f"{'='*60}")
    print(f"Total sources collected: {len(sources)}")
    print()

    for i, source in enumerate(sources, 1):
        metadata = source['metadata']
        print(f"{i}. {metadata['source']}")
        print(f"   Title: {metadata['title']}")
        print(f"   Relia7bility: {metadata['reliability']}")
        print(f"   Content length: {metadata['content_type']} characters")
        print(f"   URL: {metadata.keys()}")
    return sources
#data = search()