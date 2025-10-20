"""
Spider.py - Research V4
Enhanced Plant Spider with JSON configuration management
All settings loaded from ConfigManager
"""

import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse
from typing import List, Dict, Optional
import json
from dataclasses import dataclass
from datetime import datetime
import logging
import io
import PyPDF2
import os
import wikipediaapi

from services.v4.ConfigManager import ConfigManager

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


class GoogleAIModeClient:
    """Client for querying Google AI Mode via SerpAPI - Config-driven"""

    def __init__(self, config: ConfigManager):
        """
        Initialize the Google AI Mode client.

        Args:
            config: ConfigManager instance
        """
        self.config = config
        self.serpapi_key = config.get_api_key()
        self.base_url = "https://serpapi.com/search"
        self.request_timeout = config.get_request_timeout()

    def ask_question(self, plant_name: str, question: str) -> Dict:
        """Ask Google AI Mode a question about a plant."""
        try:
            query = f"{plant_name} {question}"
            logger.info(f"Asking Google AI Mode: {query}")

            params = {
                "engine": "google_ai_mode",
                "q": query,
                "api_key": self.serpapi_key
            }

            response = requests.get(self.base_url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            data = response.json()

            text_blocks = data.get("text_blocks", [])
            answer_parts = []

            for block in text_blocks:
                block_type = block.get("type", "")
                snippet = block.get("snippet", "")

                if snippet:
                    if block_type == "heading":
                        answer_parts.append(f"\n## {snippet}")
                    elif block_type == "paragraph":
                        answer_parts.append(snippet)
                    elif block_type == "list":
                        items = block.get("list", [])
                        for item in items:
                            answer_parts.append(f"• {item.get('snippet', '')}")

            answer = "\n".join(answer_parts)

            return {
                "text": answer,
                "metadata": {
                    "source": data.get("search_metadata", {}),
                    "url": data.get("references", []),
                    "query": query,
                    'domain': "google_ai_mode",
                    'document_type': "AI Answer",
                    'scraped_date': datetime.now().strftime('%Y-%m-%d'),
                    "reliability": 0.95,
                    "title": question
                }
            }

        except Exception as e:
            logger.error(f"Error querying Google AI Mode: {str(e)}")
            return {
                "text": "",
                "metadata": {
                    "question": question,
                    "query": f"{plant_name} {question}",
                    "answer": f"Error: {str(e)}",
                    "references": []
                }
            }

    def ask_multiple_questions(self, plant_name: str) -> Dict:
        """Ask multiple predefined questions about a plant."""
        questions = self.config.get_search_questions()

        results = {
            "plant_name": plant_name,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "questions": []
        }

        for question in questions:
            logger.info(f"Processing question: {question}")
            result = self.ask_question(plant_name, question)
            results["questions"].append(result)
            time.sleep(2)

        return results


class PlantWikipediaSearch:
    """Search and retrieve plant information from Wikipedia."""
    
    def __init__(self, user_agent='PlantSearchBot (contact@example.com)', language='en'):
        self.wiki = wikipediaapi.Wikipedia(user_agent=user_agent, language=language)
        self.current_page = None
    
    def search_plant(self, plant_name):
        self.current_page = self.wiki.page(plant_name)
        return self.current_page.exists()
    
    def get_full_text(self):
        if self.current_page and self.current_page.exists():
            return self.current_page.text
        return "No page loaded or page does not exist."
    
    def get_page_info(self):
        if not self.current_page or not self.current_page.exists():
            return {"error": "No page loaded or page does not exist."}
       
        return {
            "title": self.current_page.title,
            "pageid": self.current_page.pageid,
            "summary": self.current_page.summary,
            "source": self.current_page.fullurl,
            "url": self.current_page.fullurl,
            "sections": [s.title for s in self.current_page.sections],
            "categories": list(self.current_page.categories.keys()),
            "language": self.current_page.pagelanguage,
            "reliability": 1,
            "last_modified": self.current_page.touched
        }


def wiki(plant_name=None):
    """Wikipedia search function."""
    plant_search = PlantWikipediaSearch()
    plant_name = plant_name if plant_name else "Rose"
    
    logger.info(f"Searching Wikipedia for: {plant_name}")
    
    if plant_search.search_plant(plant_name):
        logger.info(f"✓ Page exists for '{plant_name}'")
        info = plant_search.get_page_info()
        return [{"text": plant_search.get_full_text(), "metadata": info}]
    else:
        logger.warning(f"✗ Page does not exist for '{plant_name}'")
        return [{"text": plant_name, "metadata": {"url": "", "source": ""}}]


class EnhancedPlantSpider:
    """Enhanced Plant Spider with full JSON configuration support"""

    def __init__(self, config: ConfigManager):
        """Initialize with configuration."""
        self.config = config
        self.serpapi_key = config.get_api_key()
        self.delay = config.get_search_delay()
        self.max_sources = config.get_max_sources()
        self.request_timeout = config.get_request_timeout()
        
        self.session = requests.Session()
        self.session.headers.update(config.get_request_headers())

        self.ai_client = GoogleAIModeClient(config)
        self.wiki_searcher = PlantWikipediaSearch()
        
        self.domain_reliability = self._build_domain_reliability()
        self.skip_domains = set(config.get_skip_domains())
        
        search_cfg = config.get_search_config()
        self.supported_extensions = set(search_cfg.get('supported_extensions', ['.html', '.htm', '.php', '.asp', '.aspx', '.pdf', '.txt']))
        self.unsupported_extensions = set(search_cfg.get('unsupported_extensions', []))

    def _build_domain_reliability(self) -> Dict[str, float]:
        """Build flat domain reliability dictionary from config."""
        domain_reliability = {}
        config_domains = self.config.get_domain_reliability()
        
        for category, domains in config_domains.items():
            domain_reliability.update(domains)
        
        return domain_reliability

    def is_supported_document(self, url: str) -> tuple:
        """Check if URL points to a supported document type."""
        url_lower = url.lower()

        if url_lower.endswith('.pdf') or 'pdf' in url_lower:
            return True, 'pdf'

        if url_lower.endswith('.txt'):
            return True, 'text'

        for ext in self.unsupported_extensions:
            if url_lower.endswith(ext):
                return False, 'unsupported'

        return True, 'html'

    def extract_pdf_content(self, url: str) -> Optional[str]:
        """Extract text content from a PDF file."""
        try:
            logger.info(f"Downloading PDF from: {url}")
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()

            if 'application/pdf' not in response.headers.get('Content-Type', ''):
                logger.warning(f"URL doesn't return PDF content: {url}")
                return None

            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text_parts = []
            num_pages = len(pdf_reader.pages)

            for page_num in range(min(num_pages, 50)):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text and len(text.strip()) > 50:
                        text_parts.append(text.strip())
                except Exception as e:
                    logger.debug(f"Error extracting page {page_num}: {str(e)}")
                    continue

            if not text_parts:
                logger.warning(f"No text extracted from PDF: {url}")
                return None

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"Error extracting PDF content from {url}: {str(e)}")
            return None

    def extract_text_file(self, url: str) -> Optional[str]:
        """Extract content from a text file."""
        try:
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()

            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            for encoding in encodings:
                try:
                    text = response.content.decode(encoding)
                    if text and len(text.strip()) > 50:
                        return text.strip()
                except UnicodeDecodeError:
                    continue

            return None

        except Exception as e:
            logger.error(f"Error extracting text file from {url}: {str(e)}")
            return None

    def search_serpapi(self, plant_name: str) -> List[Dict[str, str]]:
        """Search for plant information using SerpAPI."""
        try:
            logger.info(f"Searching SerpAPI for: {plant_name}")

            results = []
            
            # First search: .ac.za domains
            query_za = f"{plant_name} plant site:.ac.za"
            params = {
                "q": query_za,
                "api_key": self.serpapi_key,
                "num": 30,
                "engine": "google"
            }

            response = requests.get("https://serpapi.com/search", params=params, timeout=self.request_timeout)
            response.raise_for_status()
            data = response.json()

            organic_results = data.get("organic_results", [])
            logger.info(f"SerpAPI returned {len(organic_results)} .ac.za results")

            for result in organic_results:
                url = result.get('link', '')
                is_supported, doc_type = self.is_supported_document(url)

                if is_supported:
                    results.append({
                        'url': url,
                        'title': result.get('title', ''),
                        'snippet': result.get('snippet', ''),
                        'doc_type': doc_type,
                        'priority': 'high'
                    })

            # Second search: General .za domains
            time.sleep(1)
            query_za_general = f"{plant_name} plant site:.za"
            params["q"] = query_za_general

            response = requests.get("https://serpapi.com/search", params=params, timeout=self.request_timeout)
            response.raise_for_status()
            data = response.json()

            for result in data.get("organic_results", []):
                url = result.get('link', '')
                if url not in [r['url'] for r in results]:
                    is_supported, doc_type = self.is_supported_document(url)
                    if is_supported:
                        results.append({
                            'url': url,
                            'title': result.get('title', ''),
                            'snippet': result.get('snippet', ''),
                            'doc_type': doc_type,
                            'priority': 'medium'
                        })

            # Third search: International sources
            if len(results) < self.max_sources:
                time.sleep(1)
                query_international = f"{plant_name} plant botanical"
                params["q"] = query_international

                response = requests.get("https://serpapi.com/search", params=params, timeout=self.request_timeout)
                response.raise_for_status()
                data = response.json()

                for result in data.get("organic_results", []):
                    url = result.get('link', '')
                    if url not in [r['url'] for r in results]:
                        is_supported, doc_type = self.is_supported_document(url)
                        if is_supported:
                            results.append({
                                'url': url,
                                'title': result.get('title', ''),
                                'snippet': result.get('snippet', ''),
                                'doc_type': doc_type,
                                'priority': 'low'
                            })

            filtered_results = self._filter_relevant_results(results, plant_name)
            logger.info(f"Filtered to {len(filtered_results)} relevant results")
            return filtered_results[:self.max_sources + 5]

        except Exception as e:
            logger.error(f"Error searching SerpAPI: {str(e)}")
            return []

    def _filter_relevant_results(self, results: List[Dict[str, str]], plant_name: str) -> List[Dict[str, str]]:
        """Filter and rank search results by relevance."""
        plant_terms = plant_name.lower().split()
        genus = plant_terms[0] if plant_terms else ""

        scored_results = []
        seen_urls = set()

        for result in results:
            url = result['url']
            title = result['title'].lower()
            snippet = result.get('snippet', '').lower()
            doc_type = result.get('doc_type', 'html')
            priority = result.get('priority', 'low')

            if url in seen_urls:
                continue
            if any(skip in url.lower() for skip in self.skip_domains):
                continue

            seen_urls.add(url)
            score = 0

            if priority == 'high':
                score += 25
            elif priority == 'medium':
                score += 15

            if doc_type == 'pdf':
                score += 5

            if plant_name.lower() in title or plant_name.lower() in snippet:
                score += 10

            if genus and (genus in title or genus in snippet):
                score += 5

            for term in plant_terms:
                if term in title:
                    score += 3
                if term in snippet:
                    score += 1

            plant_keywords = ['plant', 'botanical', 'species', 'cultivation', 'growing', 'care', 'garden']
            for keyword in plant_keywords:
                if keyword in title or keyword in snippet:
                    score += 1

            domain = urlparse(url).netloc
            if domain in self.domain_reliability:
                if '.za' in domain or 'sanbi' in domain:
                    score += 12
                else:
                    score += 5

            if any(specific in url.lower() for specific in ['/plant/', '/species/', '/wiki/', '/flora/']):
                score += 3

            scored_results.append((score, result))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [result for score, result in scored_results if score > 0]

    def extract_plant_info(self, url: str, doc_type: str = 'html') -> Optional[Source]:
        """Extract plant information from a URL."""
        try:
            if doc_type == 'pdf':
                content = self.extract_pdf_content(url)
                title = url.split('/')[-1].replace('.pdf', '').replace('_', ' ').replace('-', ' ').title()
            elif doc_type == 'text':
                content = self.extract_text_file(url)
                title = url.split('/')[-1].replace('.txt', '').replace('_', ' ').replace('-', ' ').title()
            else:
                response = self.session.get(url, timeout=self.request_timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()

                title = self._extract_title(soup, url)
                content = self._extract_content(soup, url)

            if not content or len(content.strip()) < 100:
                logger.debug(f"Insufficient content from {url}")
                return None

            domain = urlparse(url).netloc
            reliability_score = self._calculate_reliability(domain, content)

            metadata = {
                'source': self._get_source_name(domain, title),
                'reliability': self._get_reliability_level(reliability_score),
                'url': url,
                'domain': domain,
                'title': title,
                'scraped_date': datetime.now().strftime('%Y-%m-%d'),
                'content_type': self._classify_content_type(content, url),
                'document_type': doc_type,
                'is_south_african': '.za' in domain or 'sanbi' in domain
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
        """Extract page title."""
        selectors = ['h1.plant-name', 'h1.entry-title', 'h1.title', '.plant-header__title', 'h1', 'title']
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                if title and len(title) > 3:
                    return title
        return "Unknown Plant"

    def _extract_content(self, soup: BeautifulSoup, url: str) -> str:
        """Extract main content based on domain."""
        domain = urlparse(url).netloc

        if 'wikipedia.org' in domain:
            return self._extract_wikipedia_content(soup)
        elif 'thespruce.com' in domain:
            return self._extract_thespruce_content(soup)
        elif 'extension' in domain:
            return self._extract_extension_content(soup)
        elif 'britannica.com' in domain:
            return self._extract_britannica_content(soup)
        elif 'rhs.org.uk' in domain:
            return self._extract_rhs_content(soup)
        else:
            return self._extract_generic_content(soup)

    def _extract_wikipedia_content(self, soup: BeautifulSoup) -> str:
        """Extract from Wikipedia."""
        content_parts = []
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if content_div:
            paragraphs = content_div.find_all('p', recursive=True)[:10]
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50:
                    content_parts.append(text)
        return "\n\n".join(content_parts)

    def _extract_thespruce_content(self, soup: BeautifulSoup) -> str:
        """Extract from The Spruce."""
        content_parts = []
        selectors = ['.comp.mntl-sc-block-html', 'article p', '.entry-content p']
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
        """Extract from extension sites."""
        content_parts = []
        selectors = ['.entry-content p', '.article-content p', 'main p']
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

    def _extract_britannica_content(self, soup: BeautifulSoup) -> str:
        """Extract from Britannica."""
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
        """Extract from RHS."""
        content_parts = []
        selectors = ['.plant-description p', '.plant-summary p', 'article p']
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
        """Generic content extraction."""
        content_parts = []
        selectors = ['article p', '.entry-content p', '.content p', 'main p']
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements[:10]:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 40 and self._is_content_text(text):
                        content_parts.append(text)
                if len(content_parts) >= 3:
                    break
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
        """Check if text is actual content."""
        text_lower = text.lower()
        skip_phrases = ['cookie', 'privacy', 'subscribe', 'newsletter', 'advertisement', 'menu', 'navigation', 'share this', 'follow us', 'contact us']
        return not any(phrase in text_lower for phrase in skip_phrases)

    def _calculate_reliability(self, domain: str, content: str) -> float:
        """Calculate reliability score."""
        base_score = self.domain_reliability.get(domain, 0.5)
        content_lower = content.lower()
        if any(term in content_lower for term in ['scientific name', 'botanical', 'taxonomy']):
            base_score += 0.05
        if len(content) > 1000:
            base_score += 0.03
        return min(1.0, base_score)

    def _get_reliability_level(self, score: float) -> str:
        """Convert score to level."""
        if score >= 0.95:
            return "very_high"
        elif score >= 0.85:
            return "high"
        elif score >= 0.75:
            return "medium"
        else:
            return "low"

    def _get_source_name(self, domain: str, title: str) -> str:
        """Get clean source name."""
        source_names = {
            'up.ac.za': 'University of Pretoria', 'uct.ac.za': 'University of Cape Town',
            'wits.ac.za': 'University of Witwatersrand', 'sun.ac.za': 'Stellenbosch University',
            'ru.ac.za': 'Rhodes University', 'ukzn.ac.za': 'University of KwaZulu-Natal',
            'ufs.ac.za': 'University of Free State', 'unisa.ac.za': 'University of South Africa',
            'nwu.ac.za': 'North-West University', 'sanbi.org': 'South African National Biodiversity Institute',
            'sanbi.org.za': 'South African National Biodiversity Institute', 'plantzafrica.com': 'PlantZAfrica',
            'en.wikipedia.org': 'Wikipedia', 'www.britannica.com': 'Encyclopædia Britannica',
            'www.thespruce.com': 'The Spruce', 'www.rhs.org.uk': 'Royal Horticultural Society',
            'www.kew.org': 'Royal Botanic Gardens, Kew', 'powo.science.kew.org': 'Plants of the World Online',
            'www.missouribotanicalgarden.org': 'Missouri Botanical Garden'
        }
        return source_names.get(domain, title.split(' - ')[0] if ' - ' in title else domain.replace('www.', '').title())

    def _classify_content_type(self, content: str, url: str) -> str:
        """Classify content type."""
        content_lower = content.lower()
        if any(term in content_lower for term in ['scientific name', 'botanical', 'taxonomy']):
            return 'botanical_reference'
        elif any(term in content_lower for term in ['growing', 'planting', 'cultivation', 'care']):
            return 'cultivation_guide'
        elif any(term in content_lower for term in ['native', 'habitat', 'distribution', 'ecology']):
            return 'ecological_information'
        elif any(term in content_lower for term in ['description', 'appearance', 'characteristics']):
            return 'plant_description'
        else:
            return 'general_information'

    def collect_plant_sources(self, plant_name: str) -> List[Dict]:
        """Main method to collect plant sources using SerpAPI."""
        logger.info(f"Starting SerpAPI collection for: {plant_name}")

        search_results = self.search_serpapi(plant_name)

        if not search_results:
            logger.error("No search results from SerpAPI")
            return []

        sources = []
        processed_urls = set()
        domain_counts = {}

        for result in search_results:
            if len(sources) >= self.max_sources:
                break

            url = result['url']
            doc_type = result.get('doc_type', 'html')

            if url in processed_urls:
                continue

            domain = urlparse(url).netloc
            domain_counts[domain] = domain_counts.get(domain, 0)

            max_per_domain = 5 if '.za' in domain else 3
            if domain_counts[domain] >= max_per_domain:
                continue

            processed_urls.add(url)
            logger.info(f"Processing [{doc_type}]: {result['title'][:60]}...")

            try:
                source = self.extract_plant_info(url, doc_type)

                if source and len(source.text.strip()) > 150:
                    rag_source = {"text": source.text, "metadata": source.metadata}
                    sources.append(rag_source)
                    domain_counts[domain] += 1
                    logger.info(f"✓ Extracted from {domain} ({doc_type})")
                else:
                    logger.debug(f"✗ Insufficient content from {url}")

            except Exception as e:
                logger.debug(f"✗ Error processing {url}: {str(e)}")

            time.sleep(self.delay)

        sources.sort(key=lambda x: self._get_rag_sort_score(x['metadata']), reverse=True)
        logger.info(f"Successfully collected {len(sources)} sources for {plant_name}")
        return sources

    def _get_rag_sort_score(self, metadata: Dict) -> float:
        """Get sorting score for RAG system."""
        reliability_scores = {'very_high': 1.0, 'high': 0.8, 'medium': 0.6, 'low': 0.4}
        base_score = reliability_scores.get(metadata.get('reliability', 'low'), 0.4)

        if metadata.get('is_south_african', False):
            base_score += 0.25

        content_type_bonus = {
            'botanical_reference': 0.2, 'plant_description': 0.15,
            'cultivation_guide': 0.1, 'ecological_information': 0.1, 'general_information': 0.0
        }

        base_score += content_type_bonus.get(metadata.get('content_type', 'general_information'), 0.0)

        if metadata.get('document_type') == 'pdf':
            base_score += 0.05

        return min(1.5, base_score)

    def save_sources_for_rag(self, sources: List[Dict], filename: str, plant_name: str):
        """Save sources in RAG-optimized format."""
        rag_data = {
            "plant_name": plant_name,
            "collection_date": datetime.now().strftime('%Y-%m-%d'),
            "total_sources": len(sources),
            "sources": sources
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(rag_data, f, indent=2, ensure_ascii=False)

        sources_only_filename = filename.replace('.json', '_sources_only.json')
        with open(sources_only_filename, 'w', encoding='utf-8') as f:
            json.dump(sources, f, indent=2, ensure_ascii=False)


def search(name=None, config: ConfigManager = None):
    """Main search function with AI questions and Wikipedia integration."""
    if config is None:
        config = ConfigManager()
    
    spider = EnhancedPlantSpider(config)
    plant_name = name if name else "Rosa rubiginosa"

    print(f"\n{'='*80}")
    print(f"ENHANCED PLANT RESEARCH SYSTEM - V4")
    print(f"{'='*80}")
    print(f"Plant: {plant_name}")
    print(f"{'='*80}\n")

    # Step 1: Collect web sources
    print("📚 STEP 1: Collecting web sources...")
    sources = spider.collect_plant_sources(plant_name)
    print(f"✓ Collected {len(sources)} sources\n")

    # Step 2: Query Google AI Mode
    print("🤖 STEP 2: Querying Google AI Mode...")
    ai_results = spider.ai_client.ask_multiple_questions(plant_name)
    print(f"✓ Completed AI queries\n")

    # Step 3: Search Wikipedia
    print("📖 STEP 3: Searching Wikipedia...")
    wiki_results = wiki(plant_name)
    print(f"✓ Wikipedia search complete\n")

    # Combine all results
    final_output = {
        "plant_name": plant_name,
        "collection_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "web_sources": {
            "total_sources": len(sources),
            "sources": sources
        },
        "ai_insights": ai_results,
        "wikipedia": wiki_results
    }
    
    # Save complete results
    filename = f"{plant_name.replace(' ', '_')}_complete_research.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    # Also save legacy format
    legacy_filename = f"{plant_name.replace(' ', '_')}_enhanced_sources.json"
    spider.save_sources_for_rag(sources, legacy_filename, plant_name)

    # Print summary
    print(f"{'='*80}")
    print(f"RESEARCH SUMMARY FOR: {plant_name}")
    print(f"{'='*80}\n")

    print(f"📚 WEB SOURCES ({len(sources)} collected):")
    print(f"{'─'*80}")
    sa_sources = sum(1 for s in sources if s['metadata'].get('is_south_african', False))
    print(f"  • South African sources: {sa_sources}")
    print(f"  • International sources: {len(sources) - sa_sources}")
    print()

    for i, source in enumerate(sources[:10], 1):
        metadata = source['metadata']
        doc_type = metadata.get('document_type', 'html')
        sa_flag = "🇿🇦" if metadata.get('is_south_african', False) else "🌍"
        print(f"{i}. {sa_flag} {metadata['source']} [{doc_type.upper()}]")
        print(f"   Title: {metadata['title']}")
        print(f"   Reliability: {metadata['reliability']}")
        print(f"   Content type: {metadata['content_type']}")
        print()

    if len(sources) > 10:
        print(f"   ... and {len(sources) - 10} more sources\n")

    print(f"{'='*80}")
    print(f"📁 FILES SAVED:")
    print(f"{'─'*80}")
    print(f"  • Complete research: {filename}")
    print(f"  • RAG sources: {legacy_filename}")
    print(f"  • RAG sources only: {legacy_filename.replace('.json', '_sources_only.json')}")
    print(f"{'='*80}\n")
    
    sources.extend(ai_results.get('questions', []))
    sources.append(wiki_results[0])
    return sources


if __name__ == "__main__":
    config = ConfigManager(verbose=True)
    config.print_summary()
    results = search("Acanthopsis Harv", config=config)