
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
    def __init__(self, serpapi_key: str, delay: float = 1.5, max_sources: int = 20, 
                 add_search_terms: bool = False):
        """
        Initialize the Enhanced Plant Spider using SerpAPI for search

        Args:
            serpapi_key: Your SerpAPI API key
            delay: Delay between requests in seconds
            max_sources: Maximum number of sources to collect (minimum 20)
            add_search_terms: If True, adds 'plant care cultivation botanical' to search
        """
        self.serpapi_key = os.getenv('SERP_API_KEY') or serpapi_key
        self.delay = delay
        self.max_sources = max(20, max_sources)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Domain reliability scores
        self.domain_reliability = {
            'en.wikipedia.org': 0.95,
            'kew.org': 0.95,
            'powo.science.kew.org': 0.95,
            'missouribotanicalgarden.org': 0.9,
            'britannica.com': 0.9,
            'rhs.org.uk': 0.9,
            'extension.wisc.edu': 0.85,
            'ces.ncsu.edu': 0.85,
            'extension.umn.edu': 0.85,
            'thespruce.com': 0.75,
            'plants.usda.gov': 0.9,
            'plantnet.rbgsyd.nsw.gov.au': 0.85,
            'up.ac.za': 0.9  # Academic institution
        }

        # Supported document types
        self.supported_extensions = {'.html', '.htm', '.php', '.asp', '.aspx', '.pdf', '.txt'}

    def is_supported_document(self, url: str) -> tuple[bool, str]:
        """
        Check if URL points to a supported document type
        
        Returns:
            (is_supported, document_type) where document_type is 'html', 'pdf', or 'text'
        """
        url_lower = url.lower()
        
        # Check for PDF
        if url_lower.endswith('.pdf') or 'pdf' in url_lower:
            return True, 'pdf'
        
        # Check for text files
        if url_lower.endswith('.txt'):
            return True, 'text'
        
        # Check for unsupported document types
        unsupported_extensions = [
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.mp4', '.avi', '.mov', '.mp3', '.wav'
        ]
        
        for ext in unsupported_extensions:
            if url_lower.endswith(ext):
                return False, 'unsupported'
        
        # Default to HTML for web pages
        return True, 'html'

    def extract_pdf_content(self, url: str) -> Optional[str]:
        """
        Extract text content from a PDF file
        
        Args:
            url: URL of the PDF file
            
        Returns:
            Extracted text content or None if extraction fails
        """
        try:
            logger.info(f"Downloading PDF from: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Verify it's actually a PDF
            if 'application/pdf' not in response.headers.get('Content-Type', ''):
                logger.warning(f"URL doesn't return PDF content: {url}")
                return None
            
            # Read PDF content
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            text_parts = []
            num_pages = len(pdf_reader.pages)
            logger.info(f"Extracting text from {num_pages} pages")
            
            for page_num in range(min(num_pages, 50)):  # Limit to first 50 pages
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
            
            full_text = "\n\n".join(text_parts)
            logger.info(f"Successfully extracted {len(full_text)} characters from PDF")
            return full_text
            
        except Exception as e:
            logger.error(f"Error extracting PDF content from {url}: {str(e)}")
            return None

    def extract_text_file(self, url: str) -> Optional[str]:
        """
        Extract content from a text file
        
        Args:
            url: URL of the text file
            
        Returns:
            Text content or None if extraction fails
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Try to decode with different encodings
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
        """
        Search for plant information using SerpAPI
        
        Returns:
            List of dicts with 'url', 'title', and 'snippet' keys
        """
        try:
            logger.info(f"Searching SerpAPI for: {plant_name}")
            
            # Construct search query with plant-specific terms
            query = f"{plant_name} plant site:.za"
            
            params = {
                "q": query,
                "api_key": self.serpapi_key,
                "num": self.max_sources + 10,
                "engine": "google"
            }
            
            response = requests.get("https://serpapi.com/search", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = []
            organic_results = data.get("organic_results", [])
            
            logger.info(f"SerpAPI returned {len(organic_results)} results")
            
            for result in organic_results:
                url = result.get('link', '')
                
                # Filter by document type
                is_supported, doc_type = self.is_supported_document(url)
                
                if is_supported:
                    results.append({
                        'url': url,
                        'title': result.get('title', ''),
                        'snippet': result.get('snippet', ''),
                        'doc_type': doc_type
                    })
                    logger.debug(f"Accepted {doc_type}: {url}")
                else:
                    logger.debug(f"Filtered out unsupported document: {url}")
            
            # Filter and rank by relevance
            filtered_results = self._filter_relevant_results(results, plant_name)
            
            logger.info(f"Filtered to {len(filtered_results)} relevant results")
            return filtered_results[:self.max_sources + 5]
            
        except Exception as e:
            logger.error(f"Error searching SerpAPI: {str(e)}")
            return []

    def _filter_relevant_results(self, results: List[Dict[str, str]], plant_name: str) -> List[Dict[str, str]]:
        """Filter and rank search results by relevance"""
        plant_terms = plant_name.lower().split()
        genus = plant_terms[0] if plant_terms else ""
        
        scored_results = []
        seen_urls = set()
        
        for result in results:
            url = result['url']
            title = result['title'].lower()
            snippet = result.get('snippet', '').lower()
            doc_type = result.get('doc_type', 'html')
            
            # Skip duplicates and unwanted domains
            if url in seen_urls:
                continue
            if any(skip in url.lower() for skip in ['pinterest.com', 'youtube.com', 'amazon.com', 'ebay.com']):
                continue
                
            seen_urls.add(url)
            
            # Calculate relevance score
            score = 0
            
            # PDF bonus (academic PDFs are valuable)
            if doc_type == 'pdf':
                score += 5
            
            # Exact plant name match
            if plant_name.lower() in title or plant_name.lower() in snippet:
                score += 10
            
            # Genus match
            if genus and (genus in title or genus in snippet):
                score += 5
            
            # Individual term matches
            for term in plant_terms:
                if term in title:
                    score += 3
                if term in snippet:
                    score += 1
            
            # Plant-related keywords
            plant_keywords = ['plant', 'botanical', 'species', 'cultivation', 'growing', 'care', 'garden']
            for keyword in plant_keywords:
                if keyword in title or keyword in snippet:
                    score += 1
            
            # Trusted domains get bonus
            domain = urlparse(url).netloc
            for trusted_domain in self.domain_reliability.keys():
                if trusted_domain in domain:
                    score += 8
                    break
            
            # Prefer specific plant pages
            if any(specific in url.lower() for specific in ['/plant/', '/species/', '/wiki/']):
                score += 3
            
            scored_results.append((score, result))
        
        # Sort by score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [result for score, result in scored_results if score > 0]

    def extract_plant_info(self, url: str, doc_type: str = 'html') -> Optional[Source]:
        """
        Extract plant information from a URL based on document type
        
        Args:
            url: URL to extract from
            doc_type: Type of document ('html', 'pdf', or 'text')
        """
        try:
            if doc_type == 'pdf':
                content = self.extract_pdf_content(url)
                title = url.split('/')[-1].replace('.pdf', '').replace('_', ' ').replace('-', ' ').title()
            elif doc_type == 'text':
                content = self.extract_text_file(url)
                title = url.split('/')[-1].replace('.txt', '').replace('_', ' ').replace('-', ' ').title()
            else:  # html
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', '.ad', '.advertisement']):
                    element.decompose()
                
                title = self._extract_title(soup, url)
                content = self._extract_content(soup, url)

            if not content or len(content.strip()) < 100:
                logger.debug(f"Insufficient content from {url} (length: {len(content) if content else 0})")
                return None

            # Calculate reliability score
            domain = urlparse(url).netloc
            reliability_score = self._calculate_reliability(domain, content)

            # Create metadata
            metadata = {
                'source': self._get_source_name(domain, title),
                'reliability': self._get_reliability_level(reliability_score),
                'url': url,
                'domain': domain,
                'title': title,
                'scraped_date': datetime.now().strftime('%Y-%m-%d'),
                'content_type': self._classify_content_type(content, url),
                'document_type': doc_type
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
        """Extract page title"""
        selectors = [
            'h1.plant-name',
            'h1.entry-title',
            'h1.title',
            '.plant-header__title',
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
        """Extract main content based on domain"""
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
        """Extract from Wikipedia"""
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
        """Extract from The Spruce"""
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
        """Extract from extension sites"""
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
        """Extract from Britannica"""
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
        """Extract from RHS"""
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
        """Generic content extraction"""
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
        """Check if text is actual content"""
        text_lower = text.lower()
        skip_phrases = [
            'cookie', 'privacy', 'subscribe', 'newsletter', 'advertisement',
            'menu', 'navigation', 'share this', 'follow us', 'contact us'
        ]
        return not any(phrase in text_lower for phrase in skip_phrases)

    def _calculate_reliability(self, domain: str, content: str) -> float:
        """Calculate reliability score"""
        base_score = 0.5
        
        for known_domain, score in self.domain_reliability.items():
            if known_domain in domain:
                base_score = score
                break
        
        content_lower = content.lower()
        if any(term in content_lower for term in ['scientific name', 'botanical', 'taxonomy']):
            base_score += 0.1
        if len(content) > 1000:
            base_score += 0.05
        
        return min(1.0, base_score)

    def _get_reliability_level(self, score: float) -> str:
        """Convert score to level"""
        if score >= 0.9:
            return "very_high"
        elif score >= 0.8:
            return "high"
        elif score >= 0.7:
            return "medium"
        else:
            return "low"

    def _get_source_name(self, domain: str, title: str) -> str:
        """Get clean source name"""
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
            'up.ac.za': 'University of Pretoria'
        }
        return source_names.get(domain, title.split(' - ')[0] if ' - ' in title else domain.replace('www.', '').title())

    def _classify_content_type(self, content: str, url: str) -> str:
        """Classify content type"""
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
        """
        Main method to collect plant sources using SerpAPI
        Returns sources in RAG-optimized format
        """
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
            if domain_counts[domain] >= 3:
                continue
            
            processed_urls.add(url)
            logger.info(f"Processing [{doc_type}]: {result['title'][:60]}...")
            
            try:
                source = self.extract_plant_info(url, doc_type)
                
                if source and len(source.text.strip()) > 150:
                    rag_source = {
                        "text": source.text,
                        "metadata": source.metadata
                    }
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
        """Get sorting score for RAG system"""
        reliability_scores = {
            'very_high': 1.0,
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
        
        base_score = reliability_scores.get(metadata.get('reliability', 'low'), 0.4)
        
        content_type_bonus = {
            'botanical_reference': 0.2,
            'plant_description': 0.15,
            'cultivation_guide': 0.1,
            'ecological_information': 0.1,
            'general_information': 0.0
        }
        
        base_score += content_type_bonus.get(metadata.get('content_type', 'general_information'), 0.0)
        
        # PDF bonus for academic content
        if metadata.get('document_type') == 'pdf':
            base_score += 0.05
        
        return min(1.0, base_score)

    def save_sources_for_rag(self, sources: List[Dict], filename: str, plant_name: str):
        """Save sources in RAG-optimized format"""
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


def search(name=None, serpapi_key="your_serpapi_key_here"):
    """
    Main search function
    """
    spider = EnhancedPlantSpider(
        serpapi_key=os.getenv('SERP_API_KEY') or serpapi_key,
        delay=1.5,
        max_sources=20
    )

    plant_name = name if name else "Rosa rubiginosa"
    sources = spider.collect_plant_sources(plant_name)

    filename = f"{plant_name.replace(' ', '_')}_enhanced_sources.json"
    spider.save_sources_for_rag(sources, filename, plant_name)

    print(f"\n{'='*60}")
    print(f"ENHANCED PLANT SPIDER RESULTS FOR: {plant_name}")
    print(f"{'='*60}")
    print(f"Total sources collected: {len(sources)}")
    print()

    for i, source in enumerate(sources, 1):
        metadata = source['metadata']
        doc_type = metadata.get('document_type', 'html')
        print(f"{i}. {metadata['source']} [{doc_type.upper()}]")
        print(f"   Title: {metadata['title']}")
        print(f"   Reliability: {metadata['reliability']}")
        print(f"   Content type: {metadata['content_type']}")
        print(f"   URL: {metadata['url']}")
        print()
    
    return sources


# Example usage
if __name__ == "__main__":
    API_KEY = os.getenv('SERP_API_KEY')
    sources = search("Acanthopsis Harv", serpapi_key=API_KEY)