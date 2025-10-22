"""
ImgSearch.py - Research V4
Enhanced Plant Article Generator with JSON Configuration
All settings loaded from ConfigManager
"""
import requests
import json
import re
from datetime import datetime
import random
from typing import List, Dict, Any
from pathlib import Path
import logging

try:
    from .ConfigManager import ConfigManager
except ImportError:
    from FlaskApp.services.v4.ConfigManager import ConfigManager

logger = logging.getLogger(__name__)


class ContentCleaner:
    """Advanced content cleaning and formatting"""
    
    def __init__(self, cleaning_settings: Dict):
        self.settings = cleaning_settings
    
    def remove_citations(self, text: str) -> str:
        """Remove citation markers like [1], [2], etc."""
        if not self.settings.get("remove_citations", True):
            return text
        
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\[?[Ss]ource:?\s*\d+\]?', '', text)
        text = re.sub(r'Ref:\s*\[[a-zA-Z0-9]+\]', '', text)
        text = re.sub(r'\(\(https?://[^\)]+\)\)', '', text)
        text = re.sub(r':\s*\{[^}]*serpapi[^}]*\}', '', text)
        text = re.sub(r"^Source: \[[0-9a-fA-F]+\]\n", "", text, flags=re.MULTILINE)

        return text
    
    def convert_markdown_to_html(self, text: str) -> str:
        """Convert markdown syntax to HTML"""
        text = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^##\s+(.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^#\s+(.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        
        text = re.sub(r'\*\*(.+?)\*\*', r'<br>\n<strong>\1</strong>', text)
        text = re.sub(r'\*([^*]+?)\*', r'<em>\1</em>', text)
        
        lines = text.split('\n')
        in_list = False
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('* ', '- ')):
                if not in_list:
                    new_lines.append('<ul>')
                    in_list = True
                content = stripped[2:].strip()
                new_lines.append(f'<li>{content}</li>')
            else:
                if in_list:
                    new_lines.append('</ul>')
                    in_list = False
                new_lines.append(line)
        
        if in_list:
            new_lines.append('</ul>')
        
        text = '\n'.join(new_lines)
        return text
    
    def remove_non_paragraph_content(self, text: str) -> str:
        """Remove lines that don't look like proper paragraph content"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith('<'):
                cleaned_lines.append(line)
                continue
            
            if not stripped:
                cleaned_lines.append(line)
                continue
            
            if any(pattern in stripped for pattern in [
                "{'id':", '{"id":', 'serpapi.com', 'json_endpoint',
                'raw_html_file', 'created_at', 'processed_at'
            ]):
                continue
            
            if stripped.startswith(':'):
                continue
            
            if len(stripped) < 20 and not any(c in stripped for c in '.!?'):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def remove_incomplete_paragraphs(self, text: str) -> str:
        """Remove incomplete sentences and paragraphs"""
        if not self.settings.get("remove_incomplete_paragraphs", True):
            return text
        
        min_length = self.settings.get("min_paragraph_length", 50)
        paragraphs = re.split(r'\n\s*\n', text)
        cleaned_paragraphs = []
        
        for para in paragraphs:
            if para.strip().startswith('<') and para.strip().endswith('>'):
                cleaned_paragraphs.append(para)
                continue
            
            if '<h2>' in para or '<h3>' in para or '<ul>' in para or '<li>' in para:
                cleaned_paragraphs.append(para)
                continue
            
            para = para.strip()
            
            if len(para) < min_length:
                continue
            
            if para and not para[-1] in '.!?":)]>':
                sentences = re.split(r'[.!?]+\s+', para)
                if len(sentences) > 1:
                    para = '. '.join(sentences[:-1]) + '.'
                else:
                    continue
            
            if para and para[0].islower() and not para.startswith(('e.g.', 'i.e.')) and not para.startswith('<'):
                match = re.search(r'[.!?]\s+([A-Z])', para)
                if match:
                    para = para[match.start() + 2:]
                else:
                    continue
            
            cleaned_paragraphs.append(para)
        
        return '\n\n'.join(cleaned_paragraphs)
    
    def clean_source_markers(self, text: str) -> str:
        """Remove source markers and references"""
        if not self.settings.get("remove_source_markers", True):
            return text
        
        text = re.sub(r'\[/?INST\]', '', text)
        text = re.sub(r'\[\d+\]\s*$', '', text, flags=re.MULTILINE)
        
        return text
    
    def clean_content(self, text: str) -> str:
        """Apply all cleaning operations"""
        text = self.remove_citations(text)
        text = self.clean_source_markers(text)
        text = self.convert_markdown_to_html(text)
        text = self.remove_non_paragraph_content(text)
        text = self.remove_incomplete_paragraphs(text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()


class HTMLContentFormatter:
    """Format and clean HTML content for proper display"""
    
    def __init__(self, image_settings: Dict, content_cleaner: ContentCleaner):
        self.image_width = image_settings.get("width", 800)
        self.image_height = image_settings.get("height", 600)
        self.default_image = image_settings.get("default_fallback", "/img/posts/default-plant.jpg")
        self.cleaner = content_cleaner
    
    def format_emoji_sections(self, text: str) -> str:
        """Format emoji label sections"""
        pattern = r'([\U0001F300-\U0001F9FF])\s*\*\*([^*:]+):\*\*'
        
        def replace_emoji_label(match):
            emoji = match.group(1)
            label = match.group(2)
            return f'\n\n<p><strong>{emoji} {label}:</strong></p>\n<p>'
        
        text = re.sub(pattern, replace_emoji_label, text)
        return text
    
    def clean_content(self, content: str) -> str:
        """Apply all formatting fixes to content"""
        content = self.cleaner.clean_content(content)
        content = self.format_emoji_sections(content)
        content = re.sub(r'<p>\s*</p>', '', content)
        
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append(line)
                continue
            
            if stripped.startswith(('<h', '<ul', '<ol', '<div', '<img', '<p>', '</p>', '<br', '<li', '</ul>', '</ol>')):
                formatted_lines.append(line)
            elif stripped.startswith('</'):
                formatted_lines.append(line)
            elif stripped and not stripped.startswith('<'):
                if '<strong>' in line or '<em>' in line or '<a ' in line:
                    formatted_lines.append(f'<p>{stripped}</p>')
                elif len(stripped) > 30:
                    formatted_lines.append(f'<p>{stripped}</p>')
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        content = '\n'.join(formatted_lines)
        content = re.sub(r'<p>\s*</p>', '', content)
        
        return content


class WikiCommonsImageFetcher:
    """Fetch images from Wikimedia Commons for article sections"""

    def __init__(self, config: ConfigManager = None):
        if config is None:
            config = ConfigManager()
        
        self.config = config
        self.base_url = "https://commons.wikimedia.org/w/api.php"
        self.headers = config.get_request_headers()

    def search_images(self, search_term: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for images on Wikimedia Commons"""
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrsearch": search_term,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 800
        }

        try:
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=self.config.get_request_timeout())
            response.raise_for_status()
            data = response.json()

            results = []

            if "query" in data and "pages" in data["query"]:
                for page_id, page_data in data["query"]["pages"].items():
                    if "imageinfo" in page_data:
                        img_info = page_data["imageinfo"][0]

                        artist = ""
                        if "extmetadata" in img_info and "Artist" in img_info["extmetadata"]:
                            artist = img_info["extmetadata"]["Artist"].get("value", "")

                        license_info = ""
                        if "extmetadata" in img_info and "LicenseShortName" in img_info["extmetadata"]:
                            license_info = img_info["extmetadata"]["LicenseShortName"].get("value", "")

                        result = {
                            "title": page_data.get("title", ""),
                            "url": img_info.get("url", ""),
                            "thumb_url": img_info.get("thumburl", ""),
                            "descriptionurl": img_info.get("descriptionurl", ""),
                            "artist": artist,
                            "license": license_info
                        }
                        results.append(result)

            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching images: {e}")
            return []

    def get_images_for_plant(self, plant_name: str) -> List[Dict[str, Any]]:
        """Get 5 images for a plant article"""
        images = self.search_images(plant_name, limit=5)

        while len(images) < 5 and len(images) > 0:
            images.append(images[0])

        return images[:5]


def create_image_html(image: Dict[str, Any], plant_name: str, section_name: str,
                     width: int, height: int, default_image: str) -> str:
    """Create HTML for image with standardized dimensions"""
    artist = image.get('artist', 'Unknown')
    if '<' in artist:
        artist = re.sub('<[^<]+?>', '', artist)

    license_info = image.get('license', '')
    image_url = image.get('thumb_url') or image.get('url', '')

    html = f'''<div class="article-image-container">
    <img class="img-fluid section-image"
         src="{image_url}"
         alt="{plant_name} - {section_name}"
         style="width: 100%; max-width: {width}px; height: {height}px; object-fit: cover; display: block; margin: 0 auto;"
         onerror="this.src='{default_image}'">
    <span class="caption text-muted">
        {plant_name} | Photo: {artist[:100]} |
        <a href="{image['descriptionurl']}" target="_blank" rel="noopener">Source</a>
        {f" | License: {license_info}" if license_info else ""}
    </span>
</div>

'''
    return html


class EnhancedPlantArticleGenerator:
    """Generate structured plant articles with proper formatting and cleaning"""

    def __init__(self, config: ConfigManager = None, rag_system=None, fetch_images: bool = True):
        if config is None:
            config = ConfigManager()
        
        self.config = config
        self.rag_system = rag_system
        self.fetch_images = fetch_images and config.get_fetch_images()
        self.image_fetcher = WikiCommonsImageFetcher(config) if self.fetch_images else None
        
        image_settings = config.get_image_settings()
        cleaning_settings = config.get_content_cleaning_settings()
        
        self.content_cleaner = ContentCleaner(cleaning_settings)
        self.formatter = HTMLContentFormatter(image_settings, self.content_cleaner)
        
        self.image_width = image_settings["width"]
        self.image_height = image_settings["height"]
        self.default_image = image_settings["default_fallback"]
        
        logger.info("Enhanced Plant Article Generator initialized with config")

    def generate_section(self, section_name: str, plant_name: str, 
                        research_data: List[Dict], image: Dict = None,
                        query: str = None, default_content: str = None) -> str:
        """Generic section generator"""
        section_html = []

        if image:
            section_html.append(create_image_html(
                image, plant_name, section_name,
                self.image_width, self.image_height, self.default_image
            ))

        section_html.append(f'<h2 class="section-heading">{section_name}</h2>')

        if self.rag_system and research_data and query:
            result = self.rag_system.query(query, k=10, max_new_tokens=400, temperature=0.75)
            content = result['answer']
        else:
            content = default_content or f"Information about {plant_name} for {section_name}."

        formatted_content = self.formatter.clean_content(content)
        section_html.append(formatted_content)

        return '\n'.join(section_html)

    def generate_full_article(self, plant_name: str, research_data: List[Dict]) -> str:
        """Generate complete article with all sections"""
        images = []
        
        if self.fetch_images:
            logger.info(f"Fetching images for {plant_name}...")
            print(f"Fetching images for {plant_name}...")
            images = self.image_fetcher.get_images_for_plant(plant_name)
            logger.info(f"Found {len(images)} images")
            print(f"Found {len(images)} images")

        while len(images) < 5:
            images.append(None)

        # Get random heading from config
        headings = self.config.get_headings()
        heading = random.choice(headings)
        heading_text = {
            "title": heading["title"].format(plant_name=plant_name),
            "subtitle": heading["subtitle"].format(plant_name=plant_name)
        }
        
        date = datetime.now()

        # Generate Jekyll front matter
        front_matter = f"""---
layout: post
title: "{heading_text['title']}"
subtitle: "{heading_text['subtitle']}"
date: {date.strftime('%Y-%m-%d %H:%M:%S')}
background: '/img/posts/{random.randint(1, 17):02d}.jpg'
categories: [South African Plants, Botany, Plant Care]
tags: [{plant_name.lower()}, indigenous-plants, plant-guide]
---

"""

        # Generate sections
        sections = [
            self.generate_section(
                "Introduction", plant_name, research_data, images[0],
                query=f"Write an engaging introduction about {plant_name}, including its origin and significance"
            ),
            self.generate_section(
                "Fascinating Facts", plant_name, research_data, images[1],
                query=f"What are the most interesting botanical facts about {plant_name}?"
            ),
            self.generate_section(
                "Care & Cultivation", plant_name, research_data, images[2],
                query=f"How do you care for and cultivate {plant_name}? Include watering, light, soil, and propagation."
            ),
            self.generate_section(
                "Benefits & Traditional Uses", plant_name, research_data, images[3],
                query=f"What are the medicinal, ecological, and cultural benefits of {plant_name}?"
            ),
            self.generate_section(
                "Conclusion", plant_name, research_data, images[4],
                query=f"Summarize the key points about {plant_name}"
            )
        ]

        article_body = '\n\n'.join(sections)
        full_article = front_matter + article_body

        logger.info(f"Article generated: {len(full_article)} characters")
        return full_article


if __name__ == "__main__":
    config = ConfigManager(verbose=True)
    config.print_summary()
    
    generator = EnhancedPlantArticleGenerator(
        config=config,
        rag_system=None,
        fetch_images=True
    )

    article = generator.generate_full_article(
        plant_name="Adiantum",
        research_data=[]
    )

    output_file = f'_posts/{datetime.now().strftime("%Y-%m-%d")}-adiantum.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(article)

    print(f"\nArticle generated: {output_file}")
    print(f"Total length: {len(article)} characters")
