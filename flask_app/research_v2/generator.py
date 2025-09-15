"""
Enhanced article generation module with improved content validation and expansion.
Fixes prompt leaking and ensures proper paragraph structure.
"""
from transformers import pipeline
import re
import random
from typing import List, Dict, Optional, Set
from datetime import datetime
import logging
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentCleaner:
    """Cleans generated content to remove prompt artifacts and improve quality"""
    
    PROMPT_ARTIFACTS = [
        # Direct prompt instructions
        r'write about.*?\.?',
        r'describe.*?\.?', 
        r'explain.*?\.?',
        r'discuss.*?\.?',
        r'focus on.*?\.?',
        r'based on this information.*?\.?',
        r'according to.*?research.*?\.?',
        
        # AI-like phrases
        r'as an ai.*?\.?',
        r'i cannot.*?\.?',
        r'i don\'t have.*?\.?',
        r'it\'s worth noting.*?\.?',
        r'it should be noted.*?\.?',
        
        # Meta references
        r'this article.*?\.?',
        r'in this section.*?\.?',
        r'the following.*?\.?',
        r'here we.*?\.?',
    ]
    
    FILLER_PHRASES = [
        r'furthermore,?\s*',
        r'moreover,?\s*',
        r'additionally,?\s*',
        r'in addition,?\s*',
        r'also,?\s*',
        r'however,?\s*',
        r'therefore,?\s*',
        r'thus,?\s*',
    ]

    @classmethod
    def clean_content(cls, text: str) -> str:
        """Remove prompt artifacts and clean up content"""
        if not text:
            return ""
        
        # Convert to lowercase for pattern matching but preserve original case
        text_lower = text.lower()
        cleaned = text
        
        # Remove prompt artifacts
        for pattern in cls.PROMPT_ARTIFACTS:
            # Find matches in lowercase version
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in reversed(list(matches)):  # Reverse to maintain indices
                start, end = match.span()
                # Remove from original text
                cleaned = cleaned[:start] + cleaned[end:]
                text_lower = text_lower[:start] + text_lower[end:]
        
        # Clean up excessive filler phrases at sentence starts
        sentences = re.split(r'(?<=[.!?])\s+', cleaned)
        clean_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 5:
                continue
                
            # Remove filler phrases from sentence start
            for filler_pattern in cls.FILLER_PHRASES:
                sentence = re.sub(f'^{filler_pattern}', '', sentence, flags=re.IGNORECASE).strip()
            
            # Ensure sentence starts with capital letter
            if sentence and sentence[0].islower():
                sentence = sentence[0].upper() + sentence[1:]
            
            if len(sentence) > 10:  # Only keep substantial sentences
                clean_sentences.append(sentence)
        
        result = '. '.join(clean_sentences)
        if result and not result.endswith('.'):
            result += '.'
        
        return result.strip()

class TopicValidator:
    """Validates content relevance to botanical topics"""

    BOTANICAL_KEYWORDS = {
        'plant_terms': ['plant', 'species', 'flower', 'leaf', 'stem', 'root', 'seed', 'petal', 
                       'bloom', 'botanical', 'flora', 'vegetation', 'foliage', 'blossom'],
        'botanical_science': ['botanical', 'botany', 'taxonomy', 'genus', 'family', 'species',
                            'cultivar', 'hybrid', 'variety', 'subspecies', 'scientific name'],
        'plant_features': ['height', 'color', 'shape', 'size', 'texture', 'form', 'appearance',
                          'characteristics', 'features', 'structure', 'morphology'],
        'habitat': ['habitat', 'native', 'grows', 'environment', 'climate', 'soil', 'rainfall',
                   'distribution', 'range', 'ecosystem', 'biome', 'landscape'],
        'geography': ['south africa', 'african', 'cape', 'kwazulu', 'natal', 'western cape',
                     'eastern cape', 'gauteng', 'mpumalanga', 'limpopo', 'fynbos', 'karoo'],
        'uses': ['medicinal', 'traditional', 'cultural', 'ornamental', 'garden', 'landscaping',
                'healing', 'remedy', 'therapeutic', 'medicine', 'treatment'],
        'conservation': ['conservation', 'endangered', 'threatened', 'protected', 'status',
                        'preservation', 'biodiversity', 'ecosystem', 'sustainability']
    }

    @classmethod
    def is_botanical_content(cls, text: str, plant_name: str = '') -> bool:
        """Check if content is botanically relevant"""
        if not text or len(text.strip()) < 20:
            return False

        text_lower = text.lower()
        
        # Count botanical relevance indicators
        botanical_score = 0
        total_keywords = 0

        for category, keywords in cls.BOTANICAL_KEYWORDS.items():
            total_keywords += len(keywords)
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    botanical_score += 1

        # Check if plant name is mentioned
        if plant_name and plant_name.lower() in text_lower:
            botanical_score += 3

        # Check for plant-related patterns
        plant_patterns = [
            r'\b(grows?|flowering|blooms?|native to|found in)\b',
            r'\b(evergreen|perennial|annual|deciduous)\b',
            r'\b(cultivation|propagation|gardening)\b'
        ]

        for pattern in plant_patterns:
            if re.search(pattern, text_lower):
                botanical_score += 2

        relevance_ratio = botanical_score / max(total_keywords * 0.1, 1)
        return relevance_ratio >= 0.15

class ExpandedArticleGenerator:
    """Article generator with expanded sections and no prompt leaking"""

    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        self.model_name = model_name
        self.summarizer = None
        self.used_content_hashes = set()
        self.topic_validator = TopicValidator()
        self.content_cleaner = ContentCleaner()
        self._load_model()

    def _load_model(self):
        """Load the AI summarization model with error handling."""
        try:
            logger.info(f"Loading AI model: {self.model_name}")
            self.summarizer = pipeline("summarization", model=self.model_name)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            logger.info("Falling back to template-based generation")
            self.summarizer = None

    def _hash_content(self, content: str) -> str:
        """Generate a hash for content to detect duplicates."""
        return hashlib.md5(content.encode()).hexdigest()

    def extract_relevant_content(self, research_data: List[Dict], plant_name: str, 
                               section_type: str, max_items: int = 3) -> str:
        """Extract content that is relevant to the plant and section type."""
        relevant_content = []
        local_used_hashes = set()

        for item in research_data:
            if not isinstance(item, dict):
                continue

            content = item.get('content', '').strip()
            if not content or len(content) < 30:
                continue

            # Validate botanical relevance
            if not self.topic_validator.is_botanical_content(content, plant_name):
                continue

            # Generate content hash for deduplication
            content_hash = self._hash_content(content)

            if content_hash in self.used_content_hashes or content_hash in local_used_hashes:
                continue

            content_lower = content.lower()
            plant_name_lower = plant_name.lower()

            # Must contain plant name or closely related terms
            if not any(term in content_lower for term in [plant_name_lower, 
                      plant_name_lower.replace(' ', '')]):
                continue

            relevant_content.append(content)
            local_used_hashes.add(content_hash)
            self.used_content_hashes.add(content_hash)

            if len(relevant_content) >= max_items:
                break

        return ' '.join(relevant_content)

    def generate_expanded_section(self, content: str, plant_name: str, section_type: str) -> List[str]:
        """Generate 2-3 paragraphs for each section using AI or templates"""
        
        if not content and self.summarizer is None:
            return self._generate_template_paragraphs(plant_name, section_type)
        
        paragraphs = []
        
        try:
            if self.summarizer and content:
                # Generate multiple focused summaries for different aspects
                aspects = self._get_section_aspects(section_type)
                
                for aspect in aspects:
                    # Create a clean, focused input without prompt language
                    focused_content = f"{plant_name} {aspect}. {content[:400]}"
                    
                    summary = self.summarizer(
                        focused_content,
                        max_length=50,
                        min_length=30,
                        do_sample=True,
                        temperature=0.7
                    )
                    
                    if summary and len(summary) > 0:
                        paragraph = self.content_cleaner.clean_content(summary[0]['summary_text'])
                        
                        # Ensure paragraph mentions the plant name
                        if plant_name.lower() not in paragraph.lower() and paragraph:
                            paragraph = f"{plant_name} {paragraph.lower()}"
                        
                        if paragraph and len(paragraph) > 30:
                            paragraphs.append(paragraph)
                    
                    if len(paragraphs) >= 3:
                        break
            
        except Exception as e:
            logger.warning(f"Error in AI generation: {str(e)}")
        
        # Fallback to templates if AI generation failed or produced insufficient content
        if len(paragraphs) < 2:
            paragraphs = self._generate_template_paragraphs(plant_name, section_type)
        
        return paragraphs[:3]  # Limit to 3 paragraphs

    def _get_section_aspects(self, section_type: str) -> List[str]:
        """Get different aspects to focus on for each section type"""
        aspects_map = {
            'characteristics': [
                'displays distinctive physical features including',
                'exhibits unique structural characteristics with',
                'showcases remarkable botanical traits through'
            ],
            'habitat': [
                'thrives naturally in environments characterized by',
                'has adapted to specific ecological conditions including',
                'grows in distinctive habitats featuring'
            ],
            'cultural': [
                'holds significant cultural importance through',
                'serves traditional purposes including',
                'represents cultural heritage with'
            ],
            'conservation': [
                'faces conservation challenges related to',
                'benefits from protection efforts focusing on',
                'requires sustainable management through'
            ]
        }
        return aspects_map.get(section_type, ['is notable for', 'demonstrates', 'features'])

    def _generate_template_paragraphs(self, plant_name: str, section_type: str) -> List[str]:
        """Generate 2-3 template-based paragraphs for each section"""
        
        templates = {
            'introduction': [
                f"{plant_name} represents one of South Africa's most distinctive indigenous plant species. This remarkable succulent has evolved unique characteristics that allow it to thrive in the challenging conditions of the country's arid regions. Its specialized adaptations showcase the incredible diversity of South African flora.",
                f"Endemic to specific regions of South Africa, {plant_name} has captured the attention of botanists and plant enthusiasts worldwide. The species demonstrates remarkable resilience and has developed fascinating survival strategies over millennia of evolution.",
                f"As part of South Africa's rich botanical heritage, {plant_name} contributes to the country's status as one of the world's most biodiverse nations. Its unique characteristics make it a subject of ongoing scientific study and conservation interest."
            ],
            'characteristics': [
                f"{plant_name} exhibits distinctive morphological features that set it apart from other succulent species. Its compact, button-like form represents a highly specialized adaptation to extreme environmental conditions, with thick, fleshy leaves that efficiently store water during prolonged dry periods.",
                f"The plant's unique structure includes specialized tissues that can expand and contract based on water availability. During favorable conditions, the leaves become plump and rounded, while in drought periods they may appear more wrinkled and withdrawn, demonstrating remarkable physiological flexibility.",
                f"Color variations in {plant_name} range from subtle green tones to more vibrant hues, often influenced by environmental factors such as light exposure and seasonal changes. The plant's surface texture and patterns create intricate geometric designs that serve both functional and aesthetic purposes in nature."
            ],
            'habitat': [
                f"{plant_name} inhabits the specialized ecosystems of South Africa's arid interior regions. These environments are characterized by extreme temperature fluctuations, minimal rainfall, and intense solar radiation, conditions that have shaped the plant's remarkable adaptations over thousands of years.",
                f"The natural habitat of {plant_name} typically features rocky outcrops, quartzite substrates, and well-draining mineral soils. These geological formations provide the perfect combination of drainage, protection, and mineral nutrients that the species requires for optimal growth and reproduction.",
                f"Seasonal patterns in the plant's native range include brief but intense rainfall periods followed by extended dry seasons. {plant_name} has evolved to maximize water uptake during these short favorable periods while maintaining metabolic functions throughout the challenging dry months."
            ],
            'cultural': [
                f"{plant_name} holds special significance in South Africa's botanical and cultural landscape. Indigenous communities have long recognized the unique properties of this remarkable plant, incorporating knowledge of its characteristics into traditional ecological wisdom passed down through generations.",
                f"The species serves as an important indicator of ecosystem health in its native habitat. Local conservation efforts increasingly recognize {plant_name} as a flagship species for protecting the unique biodiversity of South Africa's succulent regions.",
                f"Modern horticultural interest in {plant_name} has led to its cultivation by specialized growers worldwide. This attention helps raise awareness of South Africa's remarkable succulent diversity and supports conservation initiatives in the plant's natural habitat."
            ],
            'conservation': [
                f"{plant_name} faces various conservation challenges typical of South Africa's specialized succulent flora. Habitat degradation, climate change impacts, and collection pressures contribute to concerns about the long-term survival of wild populations.",
                f"Protection efforts for {plant_name} focus on habitat preservation and sustainable management of natural populations. These initiatives involve collaboration between conservation organizations, research institutions, and local communities to ensure effective protection strategies.",
                f"The species benefits from inclusion in specialized botanical collections and research programs that study South African succulents. These ex-situ conservation efforts complement habitat protection and contribute valuable scientific knowledge about the plant's biology and ecology."
            ]
        }
        
        return templates.get(section_type, templates['introduction'])

    def generate_jekyll_front_matter(self, plant_name: str, title: str) -> str:
        """Generate Jekyll front matter for the article."""
        slug = re.sub(r'[^a-z0-9]+', '-', plant_name.lower()).strip('-')
        current_date = datetime.now().strftime('%Y-%m-%d')

        front_matter = f"""---
layout: post
title: "{title}"
date: {current_date}
categories: [south-african-plants, botanical-guide]
tags: [flora, indigenous, conservation, ecology]
plant_name: "{plant_name}"
slug: "{slug}"
featured_image: "/assets/images/plants/{slug}.jpg"
description: "Explore {plant_name}, a remarkable South African plant species with unique adaptations and ecological significance."
author: "Botanical Research Team"
---

"""
        return front_matter

    def generate_focused_article(self, research_data: List[Dict], plant_name: str, 
                               include_front_matter: bool = True) -> str:
        """Generate a focused, expanded article with 2-3 paragraphs per section"""

        if not plant_name:
            raise ValueError("Plant name is required")

        logger.info(f"Generating expanded article for {plant_name}")

        # Reset content tracking
        self.used_content_hashes = set()

        # Generate title
        title_templates = [
            f"{plant_name}: A Remarkable South African Plant Species",
            f"Discovering {plant_name}: Botanical Treasures of South Africa",
            f"{plant_name}: Unique Adaptations in South African Flora",
            f"The Fascinating World of {plant_name}: South African Botanical Heritage"
        ]
        selected_title = random.choice(title_templates)

        # Build sections with expanded content
        html_sections = []

        # Introduction - 2-3 paragraphs
        intro_content = self.extract_relevant_content(research_data, plant_name, 'general', max_items=2)
        intro_paragraphs = self.generate_expanded_section(intro_content, plant_name, 'introduction')
        
        for paragraph in intro_paragraphs:
            html_sections.append(f'<p class="intro-paragraph">{paragraph}</p>')

        # Physical Characteristics - 2-3 paragraphs
        char_content = self.extract_relevant_content(research_data, plant_name, 'characteristics', max_items=3)
        char_paragraphs = self.generate_expanded_section(char_content, plant_name, 'characteristics')
        
        html_sections.append('<h2 class="section-heading">Physical Characteristics</h2>')
        for paragraph in char_paragraphs:
            html_sections.append(f'<p class="characteristics-paragraph">{paragraph}</p>')

        # Natural Habitat - 2-3 paragraphs
        habitat_content = self.extract_relevant_content(research_data, plant_name, 'habitat', max_items=3)
        habitat_paragraphs = self.generate_expanded_section(habitat_content, plant_name, 'habitat')
        
        html_sections.append('<h2 class="section-heading">Natural Habitat</h2>')
        for paragraph in habitat_paragraphs:
            html_sections.append(f'<p class="habitat-paragraph">{paragraph}</p>')

        # Cultural Significance - 2-3 paragraphs
        cultural_content = self.extract_relevant_content(research_data, plant_name, 'cultural', max_items=3)
        cultural_paragraphs = self.generate_expanded_section(cultural_content, plant_name, 'cultural')
        
        html_sections.append('<h2 class="section-heading">Ecological and Cultural Significance</h2>')
        for paragraph in cultural_paragraphs:
            html_sections.append(f'<p class="cultural-paragraph">{paragraph}</p>')

        # Conservation - 2-3 paragraphs
        conservation_paragraphs = self.generate_expanded_section('', plant_name, 'conservation')
        
        html_sections.append('<h2 class="section-heading">Conservation Status</h2>')
        for paragraph in conservation_paragraphs:
            html_sections.append(f'<p class="conservation-paragraph">{paragraph}</p>')

        # Compile final article
        article_parts = []

        if include_front_matter:
            article_parts.append(self.generate_jekyll_front_matter(plant_name, selected_title))

        article_parts.append('\n\n'.join(html_sections))

        final_article = '\n'.join(article_parts)

        logger.info(f"Expanded article generated successfully for {plant_name}")
        return final_article

    def generate_article(self, research_data: List[Dict], plant_name: str, 
                        include_front_matter: bool = True) -> str:
        """Backward compatibility method - calls generate_focused_article."""
        return self.generate_focused_article(research_data, plant_name, include_front_matter)

# Alias for backward compatibility
ArticleGenerator = ExpandedArticleGenerator

# Convenience functions for backward compatibility
def generate_article(research_data: List[Dict], plant_name: str) -> str:
    """Generate article using default settings (backward compatibility)."""
    generator = ArticleGenerator()
    return generator.generate_focused_article(research_data, plant_name, include_front_matter=False)

def generate_plant_title(plant_name: str) -> str:
    """Generate an engaging title for the plant article (backward compatibility)."""
    title_templates = [
        f"{plant_name}: A Remarkable South African Plant Species",
        f"Discovering {plant_name}: Botanical Treasures of South Africa", 
        f"{plant_name}: Unique Adaptations in South African Flora",
        f"The Fascinating World of {plant_name}: South African Botanical Heritage"
    ]
    return random.choice(title_templates)

def generate_focused_article(research_data: List[Dict], plant_name: str) -> str:
    """Generate a focused article using the improved generator."""
    generator = ExpandedArticleGenerator()
    return generator.generate_focused_article(research_data, plant_name, include_front_matter=False)