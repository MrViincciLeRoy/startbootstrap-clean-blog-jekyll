"""
Wikimedia Commons Image Search - Integrated with Article Generator
WITH PROPER HTML FORMATTING AND STANDARDIZED IMAGES

Searches for 5 images and adds them to article sections with clean HTML formatting
"""
import requests
import json
import re
from datetime import datetime
import random
from typing import List, Dict, Any


class HTMLContentFormatter:
    """Format and clean HTML content for proper display"""
    
    def __init__(self, standard_image_width: int = 800, standard_image_height: int = 600):
        """
        Initialize formatter with standard image dimensions
        
        Args:
            standard_image_width: Standard width for all images (default: 800px)
            standard_image_height: Standard height for all images (default: 600px)
        """
        self.image_width = standard_image_width
        self.image_height = standard_image_height
    
    def convert_markdown_bold_to_html(self, text: str) -> str:
        """Convert markdown-style bold (**text**) to HTML <strong> tags"""
        text = re.sub(r'<br>\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        return text
    
    def fix_line_breaks(self, text: str) -> str:
        """Fix line breaks for proper HTML display"""
        # Don't modify content inside HTML tags
        parts = re.split(r'(<[^>]+>)', text)
        
        for i, part in enumerate(parts):
            if not part.startswith('<'):
                # Replace double newlines with paragraph breaks
                part = re.sub(r'\n\s*\n', '</p>\n\n<p>', part)
                # Replace single newlines with <br>
                part = re.sub(r'(?<!>)\n(?!<)', '<br>\n', part)
                parts[i] = part
        
        return ''.join(parts)
    
    def format_emoji_sections(self, text: str) -> str:
        """Format emoji label sections (💧 **Label:**)"""
        # Match emoji followed by bold text and colon
        pattern = r'([\U0001F300-\U0001F9FF])\s*\*\*([^*:]+):\*\*'
        
        def replace_emoji_label(match):
            emoji = match.group(1)
            label = match.group(2)
            return f'\n\n<p><strong>{emoji} {label}:</strong></p>\n<p>'
        
        text = re.sub(pattern, replace_emoji_label, text)
        return text
    
    def clean_content(self, content: str) -> str:
        """Apply all formatting fixes to content"""
        # Step 1: Convert markdown bold to HTML
        content = self.convert_markdown_bold_to_html(content)
        
        # Step 2: Format emoji sections
        content = self.format_emoji_sections(content)
        
        # Step 3: Ensure proper paragraph structure
        # Remove any stray <p> tags first
        content = re.sub(r'<p>\s*</p>', '', content)
        
        # Wrap loose text in paragraphs if not already wrapped
        lines = content.split('\n')
        formatted_lines = []
        in_tag = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append(line)
                continue
                
            # Check if line is already HTML
            if stripped.startswith('<h') or stripped.startswith('<ul') or stripped.startswith('<ol') or stripped.startswith('<div') or stripped.startswith('<img'):
                formatted_lines.append(line)
            elif stripped.startswith('<p>') or stripped.startswith('</p>'):
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
            "gsrnamespace": "6",  # File namespace
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

                        # Extract metadata
                        description = ""
                        if "extmetadata" in img_info and "ImageDescription" in img_info["extmetadata"]:
                            description = img_info["extmetadata"]["ImageDescription"].get("value", "")

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
        """Get 5 images for a plant article"""
        images = self.search_images(plant_name, limit=5)

        # Ensure we have exactly 5 images
        while len(images) < 5 and len(images) > 0:
            images.append(images[0])

        return images[:5]


def create_image_html(image: Dict[str, Any], plant_name: str, section_name: str,
                     width: int = 800, height: int = 600) -> str:
    """
    Create HTML for image with standardized dimensions and proper attribution
    
    Args:
        image: Image dictionary from WikiCommons
        plant_name: Name of the plant
        section_name: Name of the section
        width: Image width
        height: Image height
    """
    # Clean up artist info
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
         onerror="this.src='/img/posts/default-plant.jpg'">
    <span class="caption text-muted">
        {plant_name} | Photo: {artist[:100]} |
        <a href="{image['descriptionurl']}" target="_blank" rel="noopener">Source</a>
        {f" | License: {license_info}" if license_info else ""}
    </span>
</div>

'''
    return html


class EnhancedPlantArticleGenerator:
    """
    Generates structured plant articles with 5 sections, images, and proper HTML formatting
    """

    def __init__(self, rag_system=None, fetch_images=True, 
                 image_width=800, image_height=600):
        """
        Initialize the generator
        
        Args:
            rag_system: Instance of RAGSystem for AI-powered content generation
            fetch_images: Whether to fetch images from Wikimedia Commons
            image_width: Standard width for all images
            image_height: Standard height for all images
        """
        self.rag_system = rag_system
        self.fetch_images = fetch_images
        self.image_fetcher = WikiCommonsImageFetcher() if fetch_images else None
        self.formatter = HTMLContentFormatter(image_width, image_height)
        self.image_width = image_width
        self.image_height = image_height

    def generate_introduction(self, plant_name: str, research_data: List[Dict],
                            image: Dict = None) -> str:
        """Generate introduction section with formatted HTML"""
        section_html = []

        # Add image
        if image:
            section_html.append(create_image_html(image, plant_name, "Introduction",
                                                  self.image_width, self.image_height))

        section_html.append('<h2 class="section-heading">Introduction</h2>')

        if self.rag_system and research_data:
            query = f"Write an engaging introduction about {plant_name}, including its origin and significance"
            result = self.rag_system.query(query, k=5, max_new_tokens=300, temperature=0.7)
            intro = result['answer']
        else:
            intro = f"""The {plant_name}, also known as the Veiled Fern or Veiled Clumping Fern, is a fascinating member of the fern family native to South Africa. This clumping fern finds its home in a variety of habitats, including moist woodlands, grasslands, and rocky slopes, where it thrives in well-drained, nutrient-rich soils.

{plant_name} capillus-veneris, the more commonly encountered variety, is characterized by its delicate, arching fronds that display a striking contrast between the upper and lower surfaces. The fronds are adorned with wiry black stems, adding an intriguing visual dimension to the plant's overall appearance.

This plant's slow, yet steady, spread through its creeping rhizomes makes it an excellent choice for ground cover, creating a lush, verdant carpet that enhances the natural beauty of its surroundings."""

        # Format the content
        formatted_intro = self.formatter.clean_content(intro)
        section_html.append(formatted_intro)
        
        return '\n'.join(section_html)

    def generate_facts_section(self, plant_name: str, research_data: List[Dict],
                              image: Dict = None) -> str:
        """Generate facts section with formatted HTML"""
        section_html = []

        if image:
            section_html.append(create_image_html(image, plant_name, "Facts",
                                                  self.image_width, self.image_height))

        section_html.append('<h2 class="section-heading">Fascinating Facts</h2>')

        if self.rag_system and research_data:
            query = f"What are the most interesting botanical facts about {plant_name}?"
            result = self.rag_system.query(query, k=10, max_new_tokens=600, temperature=0.7)
            facts_content = result['answer']
        else:
            facts_content = f"""{plant_name} capillus-veneris, commonly known as the Velvet Fern, possesses several interesting botanical characteristics that make it a noteworthy species in the Adiantaceae family.

The Velvet Fern is native to South Africa and is characterized by its drooping, clumping habit. Its fronds exhibit wiry black stems that arch elegantly, adding a dynamic element to its appearance. The plant's delicate, finely textured foliage is highly prized for its soft texture and attractive appearance, making it a favorite among gardeners and botanists alike.

One of the most fascinating aspects of {plant_name} capillus-veneris is its propagation method. The plant spreads slowly through short creeping rhizomes, allowing it to expand its habitat naturally. This unique method of growth not only highlights the plant's adaptability but also its ability to thrive in various conditions."""

        formatted_facts = self.formatter.clean_content(facts_content)
        section_html.append(formatted_facts)

        return '\n'.join(section_html)

    def generate_care_section(self, plant_name: str, research_data: List[Dict],
                            image: Dict = None) -> str:
        """Generate care section with formatted HTML"""
        section_html = []

        if image:
            section_html.append(create_image_html(image, plant_name, "Care & Cultivation",
                                                  self.image_width, self.image_height))

        section_html.append('<h2 class="section-heading">Care & Cultivation</h2>')

        if self.rag_system and research_data:
            query = f"How do you care for and cultivate {plant_name}? Include watering, light, soil, and propagation."
            result = self.rag_system.query(query, k=10, max_new_tokens=700, temperature=0.6)
            care_content = result['answer']
        else:
            care_content = f"""{plant_name}, commonly known as Maidenhair fern or Lady's Mantle, is a delicate fern native to South Africa. Cultivating it effectively involves attention to its specific needs for moisture, light, soil, and propagation.

💧 **Watering:** {plant_name} prefers consistently moist conditions but should not be waterlogged. Allow the top inch of soil to dry out between waterings. During the growing season (spring/summer), watering every 1-2 weeks is suitable. In winter, reduce watering to once a month or less. Use lukewarm water, avoiding hot baths or direct showers which can shock the fern.

💡 **Light:** This fern thrives in bright, indirect light. It can tolerate some shade, but lacks flowering potential under low light conditions. Place it near a window with filtered light or in a bright room away from direct sunlight. East or north-facing windows are ideal.

🌱 **Soil:** {plant_name} requires well-draining, slightly acidic soil. A mix of peat moss, perlite, and orchid bark works well. Avoid heavy or clay-rich soils which can retain too much moisture. Ensure the pot has drainage holes to prevent root rot.

🌿 **Propagation:** There are several ways to propagate {plant_name}:

**Division:** In spring or early summer, carefully divide the rhizomes into smaller sections, each containing a root ball. Replant these sections immediately.

**Stem Cuttings:** Take stem cuttings during the growing season. Allow the cuttings to callus for a few days, then plant them in moist sphagnum moss. Keep the moss slightly moist until roots develop.

Remember, providing optimal conditions is key to thriving {plant_name}. It's a relatively low-maintenance fern once established, making it a great choice for beginners or those seeking a subtle, elegant addition to their indoor or outdoor spaces."""

        formatted_care = self.formatter.clean_content(care_content)
        section_html.append(formatted_care)

        return '\n'.join(section_html)

    def generate_benefits_section(self, plant_name: str, research_data: List[Dict],
                                 image: Dict = None) -> str:
        """Generate benefits section with formatted HTML"""
        section_html = []

        if image:
            section_html.append(create_image_html(image, plant_name, "Benefits",
                                                  self.image_width, self.image_height))

        section_html.append('<h2 class="section-heading">Benefits & Traditional Uses</h2>')

        if self.rag_system and research_data:
            query = f"What are the medicinal, ecological, and cultural benefits of {plant_name}?"
            result = self.rag_system.query(query, k=10, max_new_tokens=600, temperature=0.7)
            benefits_content = result['answer']
        else:
            benefits_content = f"""{plant_name}, commonly known as the feather fern or velvet fern, offers a range of benefits that extend beyond its aesthetic appeal. These benefits can be categorized into medicinal, ecological, and cultural domains.

**Ecological Benefits:**

{plant_name} plays a crucial role in its native habitat by contributing to soil stabilization and moisture retention. The fern's extensive rhizome system helps bind soil particles together, reducing erosion, particularly in areas prone to heavy rainfall or wind. This root structure also enhances water infiltration and retention, promoting a healthy microhabitat for other plant species and microorganisms.

The fern's delicate fronds and soft texture provide essential cover and food sources for a variety of insects, including pollinators and decomposers. This supports local biodiversity and contributes to the overall health of the ecosystem.

**Cultural Benefits:**

Historically, {plant_name} has been valued by indigenous communities for its medicinal properties. Traditional healers have utilized various parts of the plant, including the rhizomes and fronds, to treat ailments such as digestive issues, skin conditions, and respiratory problems. These practices underscore the fern's role in traditional medicine and its potential for further scientific exploration.

In modern times, {plant_name}'s unique appearance and gentle texture have made it a popular choice for indoor landscaping and ornamental gardens. Its ability to thrive in a range of conditions, from low-light environments to well-drained soils, adds to its appeal as a low-maintenance yet visually striking plant."""

        formatted_benefits = self.formatter.clean_content(benefits_content)
        section_html.append(formatted_benefits)

        return '\n'.join(section_html)

    def generate_conclusion(self, plant_name: str, research_data: List[Dict],
                          image: Dict = None) -> str:
        """Generate conclusion with formatted HTML"""
        section_html = []

        if image:
            section_html.append(create_image_html(image, plant_name, "Conclusion",
                                                  self.image_width, self.image_height))

        section_html.append('<h2 class="section-heading">Conclusion</h2>')

        if self.rag_system and research_data:
            query = f"Summarize the key points about {plant_name}"
            result = self.rag_system.query(query, k=10, max_new_tokens=350, temperature=0.7)
            conclusion = result['answer']
        else:
            conclusion = f"""{plant_name} capillus-veneris, commonly known as the velvet fern or velvet adiantum, is a native South African fern species belonging to the Adiantaceae family. It is a clumping fern characterized by its drooping, arching fronds. The plant exhibits wiry, black stems that stand out within its foliage.

This fern thrives in well-drained soil with a neutral to alkaline pH. {plant_name} capillus-veneris demonstrates a slow spreading habit through its creeping rhizomes. A defining feature of its fronds is the presence of fine, delicate, and textured hairs that lend an attractive quality to the plant.

The velvet fern's unique appearance and slow growth make it a desirable addition to gardens and landscapes, particularly in regions where it is native. Its slow spread necessitates careful management to prevent it from outcompeting other plants in its habitat."""

        formatted_conclusion = self.formatter.clean_content(conclusion)
        section_html.append(formatted_conclusion)

        return '\n'.join(section_html)

    def generate_full_article(self, plant_name: str, research_data: List[Dict],
                            include_front_matter: bool = True) -> str:
        """
        Generate complete article with all 5 sections, images, and proper formatting
        
        Args:
            plant_name: Name of the plant
            research_data: List of research data dictionaries
            include_front_matter: Whether to include Jekyll front matter
            
        Returns:
            Complete HTML article with proper formatting
        """
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
def create_enhanced_generator(rag_system=None, fetch_images=True, 
                             image_width=800, image_height=600):
    """
    Factory function to create generator with formatting and image fetching
    
    Args:
        rag_system: RAG system instance
        fetch_images: Whether to fetch images from Wikimedia Commons
        image_width: Standard width for images
        image_height: Standard height for images
    """
    return EnhancedPlantArticleGenerator(rag_system, fetch_images, 
                                        image_width, image_height)


# Utility to clean existing HTML files
def clean_existing_html_file(input_file: str, output_file: str = None,
                            image_width: int = 800, image_height: int = 600):
    """
    Clean an existing HTML file with formatting fixes
    
    Args:
        input_file: Path to input HTML file
        output_file: Path to output file (if None, overwrites input)
        image_width: Standard width for images
        image_height: Standard height for images
    """
    formatter = HTMLContentFormatter(image_width, image_height)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Clean content
    cleaned_content = formatter.clean_content(content)
    
    # Standardize image sizes
    cleaned_content = re.sub(
        r'<img([^>]*?)>',
        lambda m: m.group(0).replace('>', f' style="width: 100%; max-width: {image_width}px; height: {image_height}px; object-fit: cover;">'),
        cleaned_content
    )
    
    output_path = output_file or input_file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    print(f"Cleaned HTML saved to: {output_path}")


# Example usage
if __name__ == "__main__":
    # Example: Generate new article
    generator = EnhancedPlantArticleGenerator(
        rag_system=None, 
        fetch_images=True,
        image_width=800,
        image_height=600
    )

    sample_research = []

    article = generator.generate_full_article(
        plant_name="Adiantum",
        research_data=sample_research,
        include_front_matter=True
    )

    # Save to file
    output_file = '_posts/2025-10-11-adiantum-formatted.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(article)

    print(f"\nFormatted article generated and saved to {output_file}")
    print(f"Total length: {len(article)} characters")
    
    # Example: Clean existing file
    # clean_existing_html_file('_posts/2025-10-11-adiantum.html', 
    #                         '_posts/2025-10-11-adiantum-cleaned.html')
