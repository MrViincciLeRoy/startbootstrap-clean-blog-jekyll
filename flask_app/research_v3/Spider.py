 

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


import requests
import json
import time
from typing import Dict, Any, Optional


      

class GoogleAIModeClient:
    """
    Client for querying Google AI Mode via SerpAPI
    """

    def __init__(self, serpapi_key: str):
        """
        Initialize the Google AI Mode client.

        Args:
            serpapi_key: Your SerpApi API key
        """
        self.serpapi_key = os.getenv('SERP_API_KEY') or serpapi_key
        self.base_url = "https://serpapi.com/search"

    def ask_question(self, plant_name: str, question: str) -> Dict[str, any]:
        """
        Ask Google AI Mode a question about a plant.

        Args:
            plant_name: The plant name
            question: The question to ask

        Returns:
            Dictionary containing the AI response
        """
        try:
            query = f"{plant_name} {question}"
            logger.info(f"Asking Google AI Mode: {query}")

            params = {
                "engine": "google_ai_mode",
                "q": query,
                "api_key": self.serpapi_key
            }

            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract text blocks
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
                                      'document_type': "AI Answer" ,
                                      'scraped_date': datetime.now().strftime('%Y-%m-%d'),
                                       "reliability" : 0.95, 
                                      "title": question
                  } 
            }

        except Exception as e:
            logger.error(f"Error querying Google AI Mode: {str(e)}")
            return {
                "text": "" ,
                "metadata": {"question": question,"query": f"{plant_name} {question}","answer": f"Error: {str(e)}","references": []}
            }

    def ask_multiple_questions(self, plant_name: str) -> Dict[str, any]:
        """
        Ask multiple predefined questions about a plant.

        Args:
            plant_name: The plant name

        Returns:
            Dictionary containing all AI responses
        """
        questions = [
            "what are the benefits",
            "interesting facts",
            "care and cultivation guide",
            "what does it look like physical description"
        ]

        results = {
            "plant_name": plant_name,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "questions": []
        }

        for question in questions:
            logger.info(f"Processing question: {question}")
            result = self.ask_question(plant_name, question)
            results["questions"].append(result)
            time.sleep(2)  # Rate limiting

        return results




class PlantWikipediaSearch:
    """
    A class for searching and retrieving plant information from Wikipedia.
    """
    
    def __init__(self, user_agent='PlantSearchBot (contact@example.com)', language='en'):
        """
        Initialize the Wikipedia API client.
        
        Args:
            user_agent (str): User agent string for Wikipedia API
            language (str): Language code for Wikipedia (default: 'en')
        """
        self.wiki = wikipediaapi.Wikipedia(
            user_agent=user_agent,
            language=language
        )
        self.current_page = None
    
    def search_plant(self, plant_name):
        """
        Search for a plant on Wikipedia.
        
        Args:
            plant_name (str): Name of the plant to search
            
        Returns:
            bool: True if plant page exists, False otherwise
        """
        self.current_page = self.wiki.page(plant_name)
        return self.current_page.exists()
    
    def get_summary(self):
        """
        Get the summary of the current plant page.
        
        Returns:
            str: Summary text or error message
        """
        if self.current_page and self.current_page.exists():
            return self.current_page.summary
        return "No page loaded or page does not exist."
    
    def get_full_text(self):
        """
        Get the full text of the current plant page.
        
        Returns:
            str: Full page text or error message
        """
        if self.current_page and self.current_page.exists():
            return self.current_page.text
        return "No page loaded or page does not exist."
    
    def get_sections(self):
        """
        Get all sections of the current plant page.
        
        Returns:
            list: List of section titles or empty list
        """
        if self.current_page and self.current_page.exists():
            return [section.title for section in self.current_page.sections]
        return []
    
    def get_section_by_title(self, section_title):
        """
        Get text from a specific section.
        
        Args:
            section_title (str): Title of the section to retrieve
            
        Returns:
            str: Section text or error message
        """
        if self.current_page and self.current_page.exists():
            section = self.current_page.section_by_title(section_title)
            if section:
                return section.text
            return f"Section '{section_title}' not found."
        return "No page loaded or page does not exist."
    
    def get_categories(self):
        """
        Get all categories of the current plant page.
        
        Returns:
            list: List of category titles or empty list
        """
        if self.current_page and self.current_page.exists():
            return list(self.current_page.categories.keys())
        return []
    
    def get_links(self):
        """
        Get all links from the current plant page.
        
        Returns:
            list: List of linked page titles or empty list
        """
        if self.current_page and self.current_page.exists():
            return list(self.current_page.links.keys())
        return []
    
    def get_page_url(self):
        """
        Get the URL of the current plant page.
        
        Returns:
            str: Full URL or error message
        """
        if self.current_page and self.current_page.exists():
            return self.current_page.fullurl
        return "No page loaded or page does not exist."
    
    def get_page_info(self):
        """
        Get comprehensive information about the current plant page.
        
        Returns:
            dict: Dictionary containing page information
        """
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
            "language": self.current_page.pagelanguage,"reliability":1,
            "last_modified": self.current_page.touched
        }


# Example usage
def wiki(plant_name=None):
    # Initialize the search class
    plant_search = PlantWikipediaSearch()
    
    # Search for a plant
    plant_name = plant_name if plant_name else "Rose"
    print(f"Searching for: {plant_name}")
    
    if plant_search.search_plant(plant_name):
        print(f"\n✓ Page exists for '{plant_name}'\n")
        
        # Get summary
        print("Summary:")
        print(plant_search.get_summary()[:300] + "...")
        
        # Get sections
        print("\n\nAvailable sections:")
        for section in plant_search.get_sections():
            print(f"  - {section}")
        
        # Get page URL
        print(f"\n\nPage URL: {plant_search.get_page_url()}")
        
        # Get comprehensive info
        print("\n\nPage Info:")
        info = plant_search.get_page_info()
        print(f"  Title: {info['title']}")
        print(f"  Page ID: {info['pageid']}")
        print(f"  Language: {info['language']}")
        print(f"  Number of categories: {len(info['categories'])}")
        return [{"text":plant_search.get_full_text(), "metadata" : info }] 
    else:
        print(f"\n✗ Page does not exist for '{plant_name}'")
        return [{"text": plant_name , "metadata" : {"url" : "", "source" :"" } }] 
        #exit() 
    

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

        # Initialize AI and Wikipedia clients
        self.ai_client = GoogleAIModeClient(self.serpapi_key)
        self.wiki_searcher = PlantWikipediaSearch() 

        # Domain reliability scores - PRIORITIZE SOUTH AFRICAN DOMAINS
        self.domain_reliability = {
            # South African institutions - HIGHEST PRIORITY
            'up.ac.za': 0.98,  # University of Pretoria
            'uct.ac.za': 0.98,  # University of Cape Town
            'wits.ac.za': 0.98,  # University of Witwatersrand
            'sun.ac.za': 0.98,  # Stellenbosch University
            'ru.ac.za': 0.97,  # Rhodes University
            'ukzn.ac.za': 0.97,  # University of KwaZulu-Natal
            'ufs.ac.za': 0.97,  # University of Free State
            'unisa.ac.za': 0.96,  # University of South Africa
            'nwu.ac.za': 0.96,  # North-West University
            'sanbi.org': 0.98,  # South African National Biodiversity Institute
            'sanbi.org.za': 0.98,
            'plantzafrica.com': 0.97,  # PlantZAfrica
            'ispotnature.org': 0.95,  # iSpot Nature (includes SA observations)
            'biodiversityadvisor.sanbi.org': 0.97,
            'redlist.sanbi.org': 0.97,
            'pza.sanbi.org': 0.97,

            # International botanical institutions
            'en.wikipedia.org': 0.93,
            'kew.org': 0.95,
            'powo.science.kew.org': 0.95,
            'missouribotanicalgarden.org': 0.88,
            'britannica.com': 0.87,
            'rhs.org.uk': 0.86,

            # Educational extensions (US/Europe)
            'extension.wisc.edu': 0.80,
            'ces.ncsu.edu': 0.80,
            'extension.umn.edu': 0.80,

            # General gardening sites
            'thespruce.com': 0.70,
            'plants.usda.gov': 0.85,
            'plantnet.rbgsyd.nsw.gov.au': 0.82,
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
        Search for plant information using SerpAPI - PRIORITIZING .ac.za DOMAINS

        Returns:
            List of dicts with 'url', 'title', and 'snippet' keys
        """
        try:
            logger.info(f"Searching SerpAPI for: {plant_name}")

            # First search: ONLY .ac.za domains
            query_za = f"{plant_name} plant site:.ac.za"

            params = {
                "q": query_za,
                "api_key": self.serpapi_key,
                "num": 30,
                "engine": "google"
            }

            response = requests.get("https://serpapi.com/search", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = []
            organic_results = data.get("organic_results", [])

            logger.info(f"SerpAPI returned {len(organic_results)} .ac.za results")

            for result in organic_results:
                url = result.get('link', '')

                # Filter by document type
                is_supported, doc_type = self.is_supported_document(url)

                if is_supported:
                    results.append({
                        'url': url,
                        'title': result.get('title', ''),
                        'snippet': result.get('snippet', ''),
                        'doc_type': doc_type,
                        'priority': 'high'  # SA academic sources
                    })
                    logger.debug(f"Accepted {doc_type}: {url}")

            # Second search: General South African domains
            time.sleep(1)
            query_za_general = f"{plant_name} plant site:.za"
            params["q"] = query_za_general

            response = requests.get("https://serpapi.com/search", params=params, timeout=30)
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
                            'priority': 'medium'  # General SA sources
                        })

            # Third search: International sources (if needed)
            if len(results) < self.max_sources:
                time.sleep(1)
                query_international = f"{plant_name} plant botanical"
                params["q"] = query_international

                response = requests.get("https://serpapi.com/search", params=params, timeout=30)
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
                                'priority': 'low'  # International sources
                            })

            # Filter and rank by relevance
            filtered_results = self._filter_relevant_results(results, plant_name)

            logger.info(f"Filtered to {len(filtered_results)} relevant results")
            return filtered_results[:self.max_sources + 5]

        except Exception as e:
            logger.error(f"Error searching SerpAPI: {str(e)}")
            return []

    def _filter_relevant_results(self, results: List[Dict[str, str]], plant_name: str) -> List[Dict[str, str]]:
        """Filter and rank search results by relevance - PRIORITIZING SA SOURCES"""
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

            # Skip duplicates and unwanted domains
            if url in seen_urls:
                continue
            if any(skip in url.lower() for skip in ['pinterest.com', 'youtube.com', 'amazon.com', 'ebay.com']):
                continue

            seen_urls.add(url)

            # Calculate relevance score
            score = 0

            # PRIORITY BONUS - South African sources get massive boost
            if priority == 'high':  # .ac.za domains
                score += 25
            elif priority == 'medium':  # .za domains
                score += 15

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
                    # Extra bonus for SA domains
                    if '.za' in trusted_domain or 'sanbi' in trusted_domain:
                        score += 12
                    else:
                        score += 5
                    break

            # Prefer specific plant pages
            if any(specific in url.lower() for specific in ['/plant/', '/species/', '/wiki/', '/flora/']):
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
        """Calculate reliability score - PRIORITIZING SA SOURCES"""
        base_score = 0.5

        for known_domain, score in self.domain_reliability.items():
            if known_domain in domain:
                base_score = score
                break

        content_lower = content.lower()
        if any(term in content_lower for term in ['scientific name', 'botanical', 'taxonomy']):
            base_score += 0.05
        if len(content) > 1000:
            base_score += 0.03

        return min(1.0, base_score)

    def _get_reliability_level(self, score: float) -> str:
        """Convert score to level"""
        if score >= 0.95:
            return "very_high"
        elif score >= 0.85:
            return "high"
        elif score >= 0.75:
            return "medium"
        else:
            return "low"

    def _get_source_name(self, domain: str, title: str) -> str:
        """Get clean source name"""
        source_names = {
            # South African institutions
            'up.ac.za': 'University of Pretoria',
            'uct.ac.za': 'University of Cape Town',
            'wits.ac.za': 'University of Witwatersrand',
            'sun.ac.za': 'Stellenbosch University',
            'ru.ac.za': 'Rhodes University',
            'ukzn.ac.za': 'University of KwaZulu-Natal',
            'ufs.ac.za': 'University of Free State',
            'unisa.ac.za': 'University of South Africa',
            'nwu.ac.za': 'North-West University',
            'sanbi.org': 'South African National Biodiversity Institute',
            'sanbi.org.za': 'South African National Biodiversity Institute',
            'plantzafrica.com': 'PlantZAfrica',

            # International sources
            'en.wikipedia.org': 'Wikipedia',
            'www.britannica.com': 'Encyclopædia Britannica',
            'www.thespruce.com': 'The Spruce',
            'hort.extension.wisc.edu': 'Wisconsin Horticulture Extension',
            'plants.ces.ncsu.edu': 'NC State Extension Plants',
            'extension.umn.edu': 'University of Minnesota Extension',
            'www.rhs.org.uk': 'Royal Horticultural Society',
            'www.kew.org': 'Royal Botanic Gardens, Kew',
            'powo.science.kew.org': 'Plants of the World Online',
            'www.missouribotanicalgarden.org': 'Missouri Botanical Garden'
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

            # Allow more sources from SA domains
            max_per_domain = 5 if '.za' in domain else 3
            if domain_counts[domain] >= max_per_domain:
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
        """Get sorting score for RAG system - PRIORITIZING SA SOURCES"""
        reliability_scores = {
            'very_high': 1.0,
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }

        base_score = reliability_scores.get(metadata.get('reliability', 'low'), 0.4)

        # MASSIVE bonus for South African sources
        if metadata.get('is_south_african', False):
            base_score += 0.25

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

        return min(1.5, base_score)  # Allow scores above 1.0 for SA sources

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
    Main search function with AI questions and Wikipedia integration
    """
    spider = EnhancedPlantSpider(
        serpapi_key=os.getenv('SERP_API_KEY') or serpapi_key,
        delay=1.5,
        max_sources=20
    )

    plant_name = name if name else "Rosa rubiginosa"

    print(f"\n{'='*80}")
    print(f"ENHANCED PLANT RESEARCH SYSTEM")
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

    # Also save legacy format for backward compatibility
    legacy_filename = f"{plant_name.replace(' ', '_')}_enhanced_sources.json"
    spider.save_sources_for_rag(sources, legacy_filename, plant_name)

    # Print summary
    print(f"{'='*80}")
    print(f"RESEARCH SUMMARY FOR: {plant_name}")
    print(f"{'='*80}\n")

    # Web sources summary
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
        print(f"   URL: {metadata['url']}")
        print()

    if len(sources) > 10:
        print(f"   ... and {len(sources) - 10} more sources\n")

    # AI insights summary
    print(f"{'='*80}")
    print(f"🤖 GOOGLE AI MODE INSIGHTS:")
    print(f"{'─'*80}")
    for q_data in ai_results.get('questions', []):
        question = q_data['metadata'].get('question', '')
        answer = q_data.get('text', '')
        print(f"\n❓ {question.upper()}")
        print(f"{'─'*80}")
        if answer and len(answer) > 10:
            # Print first 500 chars of answer
            print(answer[:500] + ('...' if len(answer) > 500 else ''))
        else:
            print("No answer available")
        print()

    # Wikipedia summary
    print(f"{'='*80}")
    print(f"📖 WIKIPEDIA INFORMATION:")
    print(f"{'─'*80}")
    print(wiki_results) 
    print(f"\n{'='*80}")
    print(f"📁 FILES SAVED:")
    print(f"{'─'*80}")
    print(f"  • Complete research: {filename}")
    print(f"  • RAG sources: {legacy_filename}")
    print(f"  • RAG sources only: {legacy_filename.replace('.json', '_sources_only.json')}")
    print(f"{'='*80}\n")
    len(sources) 
    sources.extend(ai_results.get('questions', []))
    len(sources) 
    sources.append(wiki_results[0])
    len(sources) 
    return sources


# Example usage
if __name__ == "__main__":
    #API_KEY = os.getenv('SERP_API_KEY')
    results = search("Acanthopsis Harv", serpapi_key=API_KEY)
