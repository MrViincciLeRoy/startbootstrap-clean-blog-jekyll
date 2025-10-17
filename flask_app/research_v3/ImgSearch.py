"""
Enhanced Plant Article Generator with JSON Configuration
Includes heading rotation and better content cleaning
"""
import requests
import json
import re
from datetime import datetime
import random
from typing import List, Dict, Any
from pathlib import Path


class ArticleConfig:
    """Load and manage article configuration from JSON"""
    
    def __init__(self, config_path: str = "article_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create default config if not exists
            default_config = {
                "headings": [
                    {
                        "title": "The Complete Guide to {plant_name}",
                        "subtitle": "Discover the facts, care tips, and benefits of this remarkable plant"
                    },
                    {
                        "title": "Everything You Need to Know About {plant_name}",
                        "subtitle": "A comprehensive guide to growing and caring for this beautiful species"
                    },
                    {
                        "title": "{plant_name}: Nature's Hidden Treasure",
                        "subtitle": "Uncover the secrets of this extraordinary South African plant"
                    },
                    {
                        "title": "Growing {plant_name}: Expert Tips and Insights",
                        "subtitle": "Master the art of cultivating this stunning native plant"
                    },
                    {
                        "title": "{plant_name} Revealed",
                        "subtitle": "Explore the fascinating world of this unique botanical specimen"
                    }
                ],
                "image_settings": {
                    "width": 800,
                    "height": 600,
                    "default_fallback": "/img/posts/default-plant.jpg"
                },
                "content_cleaning": {
                    "remove_source_markers": True,
                    "remove_incomplete_paragraphs": True,
                    "min_paragraph_length": 50,
                    "remove_citations": True
                }
            }
            
            # Save default config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
            
            return default_config
    
    def get_random_heading(self, plant_name: str) -> Dict[str, str]:
        """Get random title and subtitle with plant name inserted"""
        heading = random.choice(self.config["headings"])
        return {
            "title": heading["title"].format(plant_name=plant_name),
            "subtitle": heading["subtitle"].format(plant_name=plant_name)
        }
    
    def get_image_settings(self) -> Dict[str, Any]:
        """Get image configuration settings"""
        return self.config.get("image_settings", {
            "width": 800,
            "height": 600,
            "default_fallback": "/img/posts/default-plant.jpg"
        })
    
    def get_cleaning_settings(self) -> Dict[str, Any]:
        """Get content cleaning settings"""
        return self.config.get("content_cleaning", {
            "remove_source_markers": True,
            "remove_incomplete_paragraphs": True,
            "min_paragraph_length": 50,
            "remove_citations": True
        })


class ContentCleaner:
    """Advanced content cleaning and formatting"""
    
    def __init__(self, cleaning_settings: Dict):
        self.settings = cleaning_settings
    
    def remove_citations(self, text: str) -> str:
        """Remove citation markers like [1], [2], etc."""
        if not self.settings.get("remove_citations", True):
            return text
        
        # Remove [number] citations
        text = re.sub(r'\[\d+\]', '', text)
        
        # Remove source lines like "Source: [3]" or "[Source: 3]"
        text = re.sub(r'\[?[Ss]ource:?\s*\d+\]?', '', text)
        
        # Remove "Ref: [alphanumeric]"
        text = re.sub(r'Ref:\s*\[[a-zA-Z0-9]+\]', '', text)
        
        return text
    
    def remove_incomplete_paragraphs(self, text: str) -> str:
        """Remove incomplete sentences and paragraphs"""
        if not self.settings.get("remove_incomplete_paragraphs", True):
            return text
        
        min_length = self.settings.get("min_paragraph_length", 50)
        
        # Split into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        cleaned_paragraphs = []
        
        for para in paragraphs:
            # Skip if it's HTML tag
            if para.strip().startswith('<') and para.strip().endswith('>'):
                cleaned_paragraphs.append(para)
                continue
            
            # Clean the paragraph
            para = para.strip()
            
            # Skip very short paragraphs
            if len(para) < min_length:
                continue
            
            # Check if paragraph ends properly (with punctuation)
            if para and not para[-1] in '.!?":)]':
                # Try to find last complete sentence
                sentences = re.split(r'[.!?]+\s+', para)
                if len(sentences) > 1:
                    # Keep all but the last incomplete sentence
                    para = '. '.join(sentences[:-1]) + '.'
                else:
                    # Skip if entire paragraph is incomplete
                    continue
            
            # Check if paragraph starts with incomplete sentence
            if para and para[0].islower() and not para.startswith(('e.g.', 'i.e.')):
                # Try to find first complete sentence
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
        
        # Remove [/INST] markers
        text = re.sub(r'\[/?INST\]', '', text)
        
        # Remove standalone numbers in square brackets at end of paragraphs
        text = re.sub(r'\[\d+\]\s*$', '', text, flags=re.MULTILINE)
        
        return text
    
    def clean_content(self, text: str) -> str:
        """Apply all cleaning operations"""
        text = self.remove_citations(text)
        text = self.clean_source_markers(text)
        text = self.remove_incomplete_paragraphs(text)
        
        # Remove multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing whitespace
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        
        return text.strip()


class HTMLContentFormatter:
    """Format and clean HTML content for proper display"""
    
    def __init__(self, image_settings: Dict, content_cleaner: ContentCleaner):
        self.image_width = image_settings.get("width", 800)
        self.image_height = image_settings.get("height", 600)
        self.default_image = image_settings.get("default_fallback", "/img/posts/default-plant.jpg")
        self.cleaner = content_cleaner
    
    def convert_markdown_bold_to_html(self, text: str) -> str:
        """Convert markdown-style bold (**text**) to HTML <strong> tags"""
        text = re.sub(r'\*\*(.+?)\*\*', r'<br>\n<strong>\1</strong>', text)
        return text
    
    def format_emoji_sections(self, text: str) -> str:
        """Format emoji label sections (💧 **Label:**)"""
        pattern = r'([\U0001F300-\U0001F9FF])\s*\*\*([^*:]+):\*\*'
        
        def replace_emoji_label(match):
            emoji = match.group(1)
            label = match.group(2)
            return f'\n\n<p><strong>{emoji} {label}:</strong></p>\n<p>'
        
        text = re.sub(pattern, replace_emoji_label, text)
        return text
    
    def clean_content(self, content: str) -> str:
        """Apply all formatting fixes to content"""
        # First apply content cleaning
        content = self.cleaner.clean_content(content)
        
        # Convert markdown bold to HTML
        content = self.convert_markdown_bold_to_html(content)
        
        # Format emoji sections
        content = self.format_emoji_sections(content)
        
        # Ensure proper paragraph structure
        content = re.sub(r'<p>\s*</p>', '', content)
        
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append(line)
                continue
            
            # Check if line is already HTML
            if stripped.startswith(('<h', '<ul', '<ol', '<div', '<img', '<p>', '</p>', '<br')):
                formatted_lines.append(line)
            elif stripped and not stripped.startswith('<'):
                # Wrap plain text in paragraph
                if not any(x in line for x in ['<strong>', '<a ', '<span']):
                    formatted_lines.append(f'<p>{stripped}</p>')
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        content = '\n'.join(formatted_lines)
        
        return content


class WikiCommonsImageFetcher:
    """Fetch images from Wikimedia Commons for article sections"""

    def __init__(self):
        self.base_url = "https://commons.wikimedia.org/w/api.php"
        self.headers = {
            "User-Agent": "PlantArticleBot/1.0 (Educational purposes)"
        }

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
            response = requests.get(self.base_url, params=params, headers=self.headers)
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
            print(f"Error fetching images: {e}")
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

    def __init__(self, rag_system=None, fetch_images=True, config_path="article_config.json"):
        self.rag_system = rag_system
        self.fetch_images = fetch_images
        self.image_fetcher = WikiCommonsImageFetcher() if fetch_images else None
        
        # Load configuration
        self.config = ArticleConfig(config_path)
        image_settings = self.config.get_image_settings()
        cleaning_settings = self.config.get_cleaning_settings()
        
        # Initialize cleaners and formatters
        self.content_cleaner = ContentCleaner(cleaning_settings)
        self.formatter = HTMLContentFormatter(image_settings, self.content_cleaner)
        
        self.image_width = image_settings["width"]
        self.image_height = image_settings["height"]
        self.default_image = image_settings["default_fallback"]

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
            result = self.rag_system.query(query, k=10, max_new_tokens=400, temperature=0.7)
            content = result['answer']
        else:
            content = default_content or f"Information about {plant_name} for {section_name}."

        formatted_content = self.formatter.clean_content(content)
        section_html.append(formatted_content)

        return '\n'.join(section_html)

    def generate_full_article(self, plant_name: str, research_data: List[Dict],
                            include_front_matter: bool = True) -> str:
        """Generate complete article with all sections"""
        # Fetch images
        images = []
        if self.fetch_images:
            print(f"Fetching images for {plant_name}...")
            images = self.image_fetcher.get_images_for_plant(plant_name)
            print(f"Found {len(images)} images")

        while len(images) < 5:
            images.append(None)

        # Get random heading
        heading = self.config.get_random_heading(plant_name)
        date = datetime.now()

        # Generate Jekyll front matter
        if include_front_matter:
            front_matter = f"""---
layout: post
title: "{heading['title']}"
subtitle: "{heading['subtitle']}"
date: {date.strftime('%Y-%m-%d %H:%M:%S')}
background: '/img/posts/{random.randint(1, 6):02d}.jpg'
categories: [South African Plants, Botany, Plant Care]
tags: [{plant_name.lower()}, indigenous-plants, plant-guide]
---

"""
        else:
            front_matter = ""

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

        return full_article


# Example usage
if __name__ == "__main__":
    generator = EnhancedPlantArticleGenerator(
        rag_system=None,
        fetch_images=True,
        config_path="article_config.json"
    )

    article = generator.generate_full_article(
        plant_name="Adiantum",
        research_data=[],
        include_front_matter=True
    )

    output_file = f'_posts/{datetime.now().strftime("%Y-%m-%d")}-adiantum.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(article)

    print(f"\nArticle generated: {output_file}")
    print(f"Total length: {len(article)} characters")
