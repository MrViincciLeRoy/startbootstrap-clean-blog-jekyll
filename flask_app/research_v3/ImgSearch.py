
"""
Wikimedia Commons Image Search - Integrated with Article Generator
Searches for 5 images and adds them to article sections

import requests
import json
from typing import List, Dict, Any

Wikimedia Commons Image Search - Integrated with Article Generator
Searches for 5 images and adds them to article sections
"""
import requests
import json
import re
from datetime import datetime
import random
from typing import List, Dict, Any


class WikiCommonsImageFetcher:
    """Fetch images from Wikimedia Commons for article sections"""

    def __init__(self):
        self.base_url = "https://commons.wikimedia.org/w/api.php"
        self.headers = {
            "User-Agent": "PlantArticleBot/1.0 (Educational purposes)"
        }

    def search_images(self, search_term: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for images on Wikimedia Commons.

        Args:
            search_term: The keyword to search for
            limit: Maximum number of results to return (default: 5)

        Returns:
            List of dictionaries containing image information
        """
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": "6",  # File namespace
            "gsrsearch": search_term,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 800  # Larger width for article images
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

                        # Extract description if available
                        description = ""
                        if "extmetadata" in img_info and "ImageDescription" in img_info["extmetadata"]:
                            description = img_info["extmetadata"]["ImageDescription"].get("value", "")

                        # Extract artist if available
                        artist = ""
                        if "extmetadata" in img_info and "Artist" in img_info["extmetadata"]:
                            artist = img_info["extmetadata"]["Artist"].get("value", "")

                        # Extract license
                        license_info = ""
                        if "extmetadata" in img_info and "LicenseShortName" in img_info["extmetadata"]:
                            license_info = img_info["extmetadata"]["LicenseShortName"].get("value", "")

                        result = {
                            "title": page_data.get("title", ""),
                            "url": img_info.get("url", ""),
                            "thumb_url": img_info.get("thumburl", ""),
                            "descriptionurl": img_info.get("descriptionurl", ""),
                            "width": img_info.get("width", 0),
                            "height": img_info.get("height", 0),
                            "size": img_info.get("size", 0),
                            "mime": img_info.get("mime", ""),
                            "description": description,
                            "artist": artist,
                            "license": license_info
                        }
                        results.append(result)

            return results

        except requests.exceptions.RequestException as e:
            print(f"Error fetching images: {e}")
            return []

    def get_images_for_plant(self, plant_name: str) -> List[Dict[str, Any]]:
        """
        Get 5 images for a plant article (one per section)

        Args:
            plant_name: Name of the plant

        Returns:
            List of 5 image dictionaries
        """
        images = self.search_images(plant_name, limit=5)

        # Ensure we have exactly 5 images (pad with duplicates if needed)
        while len(images) < 5 and len(images) > 0:
            images.append(images[0])

        return images[:5]  # Return exactly 5 images


def create_image_html(image: Dict[str, Any], plant_name: str, section_name: str) -> str:
    """
    Create HTML for image with caption and attribution

    Args:
        image: Image dictionary from WikiCommons
        plant_name: Name of the plant
        section_name: Name of the section (Introduction, Facts, etc.)

    Returns:
        HTML string for the image
    """
    # Clean up artist info (remove HTML tags for simple display)
    artist = image.get('artist', 'Unknown')
    if '<' in artist:
        # Simple HTML tag removal
        import re
        artist = re.sub('<[^<]+?>', '', artist)

    license_info = image.get('license', '')

    html = f'''<div class="article-image-container">
    <img class="img-fluid section-image"
         src="{image['thumb_url']}"
         alt="{plant_name} - {section_name}"
         onerror="this.src='/img/posts/default-plant.jpg'">
    <span class="caption text-muted">
        {plant_name} | Photo: {artist[:100]} |
        <a href="{image['descriptionurl']}" target="_blank" rel="noopener">Source</a>
        {f" | License: {license_info}" if license_info else ""}
    </span>
</div>

'''
    return html


# Modified Article Generator Integration
class EnhancedPlantArticleGenerator:
    """
    Generates structured plant articles with 5 sections and images from Wikimedia Commons
    """

    def __init__(self, rag_system=None, fetch_images=True):
        """
        Initialize the generator with optional RAG system and image fetching

        Args:
            rag_system: Instance of RAGSystem for AI-powered content generation
            fetch_images: Whether to fetch images from Wikimedia Commons
        """
        self.rag_system = rag_system
        self.fetch_images = fetch_images
        self.image_fetcher = WikiCommonsImageFetcher() if fetch_images else None

    def generate_introduction(self, plant_name: str, research_data: List[Dict],
                            image: Dict = None) -> str:
        """Generate engaging introduction section with image"""
        section_html = []

        # Add image at the top
        if image:
            section_html.append(create_image_html(image, plant_name, "Introduction"))

        section_html.append('<h2 class="section-heading">Introduction</h2>')

        if self.rag_system and research_data:
            query = f"Write an engaging introduction about {plant_name}, including its origin and significance"
            result = self.rag_system.query(query, k=3, max_new_tokens=300, temperature=0.7)
            intro = result['answer']
        else:
            intro = f"""Welcome to our comprehensive guide on {plant_name}, one of South Africa's most
            fascinating indigenous plants. This remarkable species has captured the attention of botanists,
            gardeners, and plant enthusiasts worldwide due to its unique characteristics and cultural significance.
            In this article, we'll explore everything you need to know about this extraordinary plant, from its
            natural habitat to practical care tips."""

        section_html.append(f'<p>{intro}</p>')
        return '\n'.join(section_html)

    def generate_facts_section(self, plant_name: str, research_data: List[Dict],
                              image: Dict = None) -> str:
        """Generate interesting facts section with image"""
        section_html = []

        # Add image at the top
        if image:
            section_html.append(create_image_html(image, plant_name, "Facts"))

        section_html.append('<h2 class="section-heading">Fascinating Facts</h2>')

        if self.rag_system and research_data:
            query = f"What are the most interesting botanical facts about {plant_name}?"
            result = self.rag_system.query(query, k=5, max_new_tokens=400, temperature=0.7)
            facts_content = result['answer']
            section_html.append(f'<p>{facts_content}</p>')
        else:
            fact_items = []
            for item in research_data:
                content = item.get('content', '').strip()
                if len(content) > 100 and any(keyword in content.lower()
                    for keyword in ['native', 'species', 'family', 'discovered', 'named']):
                    fact_items.append(content[:250] + '...' if len(content) > 250 else content)
                    if len(fact_items) >= 3:
                        break

            if fact_items:
                section_html.append('<ul class="plant-facts">')
                for fact in fact_items:
                    section_html.append(f'<li>{fact}</li>')
                section_html.append('</ul>')
            else:
                section_html.append(f'''<p>{plant_name} is part of South Africa's incredible botanical heritage,
                which includes over 20,000 plant species. This plant has evolved unique adaptations to thrive
                in its native environment.</p>
                <ul class="plant-facts">
                    <li>Indigenous to South Africa's diverse ecosystems</li>
                    <li>Adapted to local climate conditions</li>
                    <li>Important role in the local ecosystem</li>
                </ul>''')

        return '\n'.join(section_html)

    def generate_care_section(self, plant_name: str, research_data: List[Dict],
                            image: Dict = None) -> str:
        """Generate plant care section with image"""
        section_html = []

        # Add image at the top
        if image:
            section_html.append(create_image_html(image, plant_name, "Care & Cultivation"))

        section_html.append('<h2 class="section-heading">Care & Cultivation</h2>')

        if self.rag_system and research_data:
            query = f"How do you care for and cultivate {plant_name}? Include watering, light, soil, and propagation."
            result = self.rag_system.query(query, k=5, max_new_tokens=500, temperature=0.6)
            care_content = result['answer']
            section_html.append(f'<p>{care_content}</p>')
        else:
            section_html.append(f'''<p>Proper care is essential for helping your {plant_name} thrive.</p>

                <h3>Light Requirements</h3>
                <p>Most South African plants prefer full sun to partial shade.</p>

                <h3>Watering</h3>
                <p>Water moderately during growing season. Reduce in winter.</p>

                <h3>Soil & Fertilization</h3>
                <p>Use well-draining soil with organic content.</p>''')

        return '\n'.join(section_html)

    def generate_benefits_section(self, plant_name: str, research_data: List[Dict],
                                 image: Dict = None) -> str:
        """Generate benefits section with image"""
        section_html = []

        # Add image at the top
        if image:
            section_html.append(create_image_html(image, plant_name, "Benefits"))

        section_html.append('<h2 class="section-heading">Benefits & Traditional Uses</h2>')

        if self.rag_system and research_data:
            query = f"What are the medicinal, ecological, and cultural benefits of {plant_name}?"
            result = self.rag_system.query(query, k=5, max_new_tokens=400, temperature=0.7)
            benefits_content = result['answer']
            section_html.append(f'<p>{benefits_content}</p>')
        else:
            section_html.append(f'''<p>{plant_name} offers multiple benefits:</p>

                <h3>Ecological Value</h3>
                <p>Provides food and habitat for various species.</p>

                <h3>Traditional Knowledge</h3>
                <p>Indigenous communities have recognized its value for generations.</p>''')

        return '\n'.join(section_html)

    def generate_conclusion(self, plant_name: str, research_data: List[Dict],
                          image: Dict = None) -> str:
        """Generate conclusion with image"""
        section_html = []

        # Add image at the top
        if image:
            section_html.append(create_image_html(image, plant_name, "Conclusion"))

        section_html.append('<h2 class="section-heading">Conclusion</h2>')

        if self.rag_system and research_data:
            query = f"Summarize the key points about {plant_name}"
            result = self.rag_system.query(query, k=5, max_new_tokens=350, temperature=0.6)
            conclusion = result['answer']
            section_html.append(f'<p>{conclusion}</p>')
        else:
            section_html.append(f'''<p>{plant_name} exemplifies South Africa's botanical diversity.
            By understanding and preserving these species, we contribute to conservation efforts.</p>''')

        return '\n'.join(section_html)

    def generate_full_article(self, plant_name: str, research_data: List[Dict],
                            include_front_matter: bool = True) -> str:
        """
        Generate complete article with all 5 sections and images

        Args:
            plant_name: Name of the plant
            research_data: List of research data dictionaries
            include_front_matter: Whether to include Jekyll front matter

        Returns:
            Complete HTML article with images
        """
        from datetime import datetime
        import random

        # Fetch images for all 5 sections
        images = []
        if self.fetch_images:
            print(f"Fetching images for {plant_name}...")
            images = self.image_fetcher.get_images_for_plant(plant_name)
            print(f"Found {len(images)} images")

        # Pad with None if not enough images
        while len(images) < 5:
            images.append(None)

        date = datetime.now()

        # Generate Jekyll front matter
        if include_front_matter:
            front_matter = f"""---
layout: post
title: "The Complete Guide to {plant_name}"
subtitle: "Discover the facts, care tips, and benefits of this remarkable plant"
date: {date.strftime('%Y-%m-%d %H:%M:%S')}
background: '/img/posts/{random.randint(1, 6):02d}.jpg'
categories: [South African Plants, Botany, Plant Care]
tags: [{plant_name.lower()}, indigenous-plants, plant-guide]
---

"""
        else:
            front_matter = ""

        # Generate all sections with their respective images
        sections = [
            self.generate_introduction(plant_name, research_data, images[0]),
            self.generate_facts_section(plant_name, research_data, images[1]),
            self.generate_care_section(plant_name, research_data, images[2]),
            self.generate_benefits_section(plant_name, research_data, images[3]),
            self.generate_conclusion(plant_name, research_data, images[4])
        ]

        # Combine everything
        article_body = '\n\n'.join(sections)
        full_article = front_matter + article_body

        return full_article


# Factory function for compatibility
def create_enhanced_generator(rag_system=None, fetch_images=True):
    """
    Factory function to create generator with image fetching

    Args:
        rag_system: RAG system instance
        fetch_images: Whether to fetch images from Wikimedia Commons
    """
    return EnhancedPlantArticleGenerator(rag_system, fetch_images)

"""
# Standalone test
if __name__ == "__main__":
    # Test image fetching
    fetcher = WikiCommonsImageFetcher()
    images = fetcher.get_images_for_plant("Rosa rubiginosa")

    print(f"Found {len(images)} images:")
    for i, img in enumerate(images, 1):
        print(f"{i}. {img['title']}")
        print(f"   URL: {img['thumb_url']}")
        print()
    rag = RAGSystem(        embedding_model='all-MiniLM-L6-v2',
        llm_model = 'LiquidAI/LFM2-1.2B-RAG'  # or any HF model
    )
    # Example without RAG (will use fallback content)

    # Sample research data structure
    sample_research = [
        {
            'source': 'PlantZAfrica',
            'content': 'King Protea (Protea cynaroides) is South Africa\'s national flower...',
            'url': 'https://example.com',
            'type': 'general_info'
        }
    ]
    sources = data
    # Your existing data
    texts = [
        #"America is a climbing rose that was introduced in 1976 and was bred by William A. Warriner. This is a vigorous climber that produces coral-pink blossoms throughout the growing season. It is hardy in zones 5-9 and prefers full sun. The flowers are fragrant and can reach 4-5 inches in diameter.",
       #X['text'] for X in Source
    ]

    metadata = [

        #x['metadata'] for x in Source
        # Add more metadata here
    ]
    for x in sources:
         #print(x)
         texts.append(x['text'])
         metadata.append(x['metadata'])
    # Build index (this doesn't require GPU)
    rag.build_index(texts, metadata)

    # Load LLM (this step loads the model into memory)
    # Use load_in_8bit=True if you have limited GPU memory
    rag.load_llm(device='auto', load_in_8bit=False)
    # Test article generation with images
    generator = EnhancedPlantArticleGenerator(rag_system=None, fetch_images=True)

    sample_research = []

    article = generator.generate_full_article(
        plant_name="Rosa rubiginosa",
        research_data=data,
        include_front_matter=True
    )

    # Save to file
    with open('test_with_images.html', 'w', encoding='utf-8') as f:
        f.write(article)

    print("\nArticle generated and saved to test_with_images.html")
    print(f"Total length: {len(article)} characters")"""