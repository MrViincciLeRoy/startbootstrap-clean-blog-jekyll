"""
Enhanced article generation module with improved topic focus and content validation.
Ensures all content stays relevant to the plant being discussed.
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
    
    OFF_TOPIC_KEYWORDS = [
        # Medical/clinical terms not related to plants
        'dna analysis', 'sequencing', 'forensic', 'hepatocellular', 'carcinoma', 'liver resection',
        'microvascular invasion', 'postoperative', 'clinical trial', 'patient', 'hospital',
        'surgery', 'diagnosis', 'treatment protocol', 'medical procedure',
        
        # Technology/engineering
        'façade', 'building', 'architecture', 'construction', 'parametric design', 'kinetic',
        'microclimate modifier', 'energy efficiency', 'ngs', 'next-generation sequencing',
        'technological advancements', 'software', 'algorithm', 'computer',
        
        # Unrelated scientific fields
        'mtdna', 'matrilineal inheritance', 'non-recombining', 'score prediction',
        'biomimicry façade', 'external climate', 'regulatory element'
    ]
    
    @classmethod
    def is_botanical_content(cls, text: str, plant_name: str = '') -> bool:
        """Check if content is botanically relevant"""
        if not text or len(text.strip()) < 20:
            return False
            
        text_lower = text.lower()
        
        # Check for off-topic keywords first
        for off_topic_term in cls.OFF_TOPIC_KEYWORDS:
            if off_topic_term.lower() in text_lower:
                return False
        
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
            botanical_score += 3  # Higher weight for plant name mentions
        
        # Check for plant-related patterns
        plant_patterns = [
            r'\b(grows?|flowering|blooms?|native to|found in)\b',
            r'\b(evergreen|perennial|annual|deciduous)\b',
            r'\b(cultivation|propagation|gardening)\b'
        ]
        
        for pattern in plant_patterns:
            if re.search(pattern, text_lower):
                botanical_score += 2
        
        # Minimum threshold for botanical relevance
        relevance_ratio = botanical_score / max(total_keywords * 0.1, 1)
        return relevance_ratio >= 0.15  # At least 15% botanical relevance

    @classmethod
    def clean_botanical_content(cls, text: str, plant_name: str = '') -> str:
        """Clean content to remove off-topic sentences"""
        if not text:
            return ""
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        clean_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
                
            # Check each sentence for botanical relevance
            if cls.is_botanical_content(sentence, plant_name):
                clean_sentences.append(sentence)
        
        # If we have too few sentences, be more lenient
        if len(clean_sentences) < 2:
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10:
                    # More lenient check - just avoid obvious off-topic content
                    sentence_lower = sentence.lower()
                    is_off_topic = any(term.lower() in sentence_lower 
                                     for term in cls.OFF_TOPIC_KEYWORDS[:5])  # Check main off-topic terms
                    if not is_off_topic:
                        clean_sentences.append(sentence)
        
        result = '. '.join(clean_sentences)
        if result and not result.endswith('.'):
            result += '.'
            
        return result

class FocusedArticleGenerator:
    """Article generator with improved topic focus and validation"""

    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        """Initialize the article generator with specified model."""
        self.model_name = model_name
        self.summarizer = None
        self.used_content_hashes = set()
        self.topic_validator = TopicValidator()
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

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and format text content."""
        if not text:
            return ""

        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        # Fix common punctuation issues
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)

        return text

    def extract_relevant_content(self, research_data: List[Dict], plant_name: str, 
                               section_type: str, max_items: int = 2) -> str:
        """Extract content that is relevant to the plant and section type."""
        relevant_content = []
        local_used_hashes = set()

        for item in research_data:
            if not isinstance(item, dict):
                continue

            content = item.get('content', '').strip()
            if not content or len(content) < 30:
                continue
                
            # Clean content to remove off-topic sentences
            cleaned_content = self.topic_validator.clean_botanical_content(content, plant_name)
            if not cleaned_content or len(cleaned_content) < 30:
                continue
                
            # Validate botanical relevance
            if not self.topic_validator.is_botanical_content(cleaned_content, plant_name):
                continue
                
            # Generate content hash for deduplication
            content_hash = self._hash_content(cleaned_content)
            
            if content_hash in self.used_content_hashes or content_hash in local_used_hashes:
                continue
            
            # Section-specific filtering
            content_lower = cleaned_content.lower()
            plant_name_lower = plant_name.lower()
            
            # Must contain plant name or closely related terms
            if not any(term in content_lower for term in [plant_name_lower, 
                      plant_name_lower.replace(' ', ''), 'strelitzia', 'bird of paradise']):
                continue
            
            if section_type == 'characteristics':
                keywords = ['appearance', 'features', 'characteristics', 'looks', 'size', 
                           'color', 'shape', 'form', 'structure', 'flower', 'leaf']
                if any(keyword in content_lower for keyword in keywords):
                    relevant_content.append(self.clean_text(cleaned_content))
                    local_used_hashes.add(content_hash)
                    self.used_content_hashes.add(content_hash)
                    
            elif section_type == 'habitat':
                keywords = ['habitat', 'grows', 'native', 'environment', 'climate', 'soil', 
                           'distribution', 'south africa', 'cape']
                if any(keyword in content_lower for keyword in keywords):
                    relevant_content.append(self.clean_text(cleaned_content))
                    local_used_hashes.add(content_hash)
                    self.used_content_hashes.add(content_hash)
                    
            elif section_type == 'cultural':
                keywords = ['traditional', 'cultural', 'ornamental', 'garden', 'medicinal', 
                           'symbolic', 'ceremonial']
                if any(keyword in content_lower for keyword in keywords):
                    relevant_content.append(self.clean_text(cleaned_content))
                    local_used_hashes.add(content_hash)
                    self.used_content_hashes.add(content_hash)
                    
            elif section_type == 'general' and len(relevant_content) < max_items:
                relevant_content.append(self.clean_text(cleaned_content))
                local_used_hashes.add(content_hash)
                self.used_content_hashes.add(content_hash)

            if len(relevant_content) >= max_items:
                break

        combined_content = ' '.join(relevant_content)
        if len(combined_content) > 1200:
            combined_content = combined_content[:1200] + "..."
        
        return combined_content

    def generate_focused_section(self, content: str, plant_name: str, section_prompt: str, 
                               max_length: int = 100, min_length: int = 30) -> str:
        """Generate a section with strong focus on the specific plant."""
        if not content or len(content.strip()) < 20:
            return ""

        try:
            if self.summarizer is None:
                # Template-based fallback
                return self._generate_template_content(plant_name, section_prompt)

            # Clean content and ensure relevance
            content = self.topic_validator.clean_botanical_content(content, plant_name)
            if not content:
                return ""

            # Create focused prompt
            focused_prompt = f"Write about {plant_name} specifically. {section_prompt}. Focus only on {plant_name} and avoid unrelated topics."
            
            max_chunk = 600
            if len(content) > max_chunk:
                content = content[:max_chunk]

            input_text = f"{focused_prompt} Based on this information about {plant_name}: {content}"
            
            adjusted_max = min(max_length, max(min_length, len(content) // 6))
            adjusted_min = min(min_length, adjusted_max // 2)

            summary = self.summarizer(
                input_text,
                max_length=adjusted_max,
                min_length=adjusted_min,
                do_sample=False,
                truncation=True
            )

            if summary and len(summary) > 0:
                summary_text = self.clean_text(summary[0]['summary_text'])
                
                # Validate the generated summary
                if (summary_text and len(summary_text) > 15 and 
                    self.topic_validator.is_botanical_content(summary_text, plant_name)):
                    return summary_text

        except Exception as e:
            logger.warning(f"Error generating section: {str(e)}")

        # Fallback to template
        return self._generate_template_content(plant_name, section_prompt)

    def _generate_template_content(self, plant_name: str, section_type: str) -> str:
        """Generate template-based content when AI generation fails."""
        templates = {
            'introduction': [
                f"{plant_name} stands as one of South Africa's most recognizable flowering plants, renowned for its distinctive bird-like blooms and vibrant orange and blue coloration.",
                f"Native to the coastal regions of South Africa, {plant_name} has become an iconic symbol of the country's rich botanical heritage.",
                f"The striking appearance of {plant_name} makes it one of the most photographed and celebrated plants in South African gardens."
            ],
            'characteristics': [
                f"{plant_name} produces distinctive flowers that resemble the head and beak of a tropical bird, featuring brilliant orange sepals and blue petals.",
                f"This evergreen perennial typically grows 1-1.5 meters tall, with large paddle-shaped leaves that can reach up to 45cm in length.",
                f"The plant's most notable feature is its unique flower structure, which has evolved to attract specific bird pollinators."
            ],
            'habitat': [
                f"{plant_name} is indigenous to the coastal areas of South Africa, particularly the Eastern and Western Cape provinces.",
                f"In its natural habitat, {plant_name} thrives in sandy, well-draining soils and benefits from the Mediterranean-like climate of the Cape region.",
                f"The plant naturally occurs along riverbanks and in coastal areas where it receives protection from harsh winds."
            ],
            'cultural': [
                f"{plant_name} serves as South Africa's national flower and appears on the country's 50 cent coin, symbolizing the nation's natural beauty.",
                f"This magnificent plant has significant cultural importance in South Africa and is widely cultivated in gardens for its ornamental value.",
                f"The distinctive appearance of {plant_name} has made it a popular choice for floral arrangements and landscape design."
            ]
        }
        
        # Match section type to template category
        template_key = 'introduction'
        if 'characteristic' in section_type.lower():
            template_key = 'characteristics'
        elif 'habitat' in section_type.lower():
            template_key = 'habitat'
        elif 'cultural' in section_type.lower():
            template_key = 'cultural'
        
        return random.choice(templates.get(template_key, templates['introduction']))

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
description: "Explore {plant_name}, a magnificent South African flowering plant known for its distinctive bird-like blooms and vibrant colors."
author: "Botanical AI Assistant"
---

"""
        return front_matter

    def create_html_paragraphs(self, text: str, section_class: str = "") -> List[str]:
        """Convert text into properly formatted HTML paragraphs."""
        if not text or not text.strip():
            return []

        text = self.clean_text(text)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        paragraphs = []
        current_para = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            if not re.search(r'[.!?]$', sentence):
                sentence += '.'

            current_para.append(sentence)

            if len(current_para) >= random.randint(2, 3):
                para_text = ' '.join(current_para)
                class_attr = f' class="{section_class}"' if section_class else ''
                paragraphs.append(f'<p{class_attr}>{para_text}</p>')
                current_para = []

        if current_para:
            para_text = ' '.join(current_para)
            class_attr = f' class="{section_class}"' if section_class else ''
            paragraphs.append(f'<p{class_attr}>{para_text}</p>')

        return paragraphs

    def generate_focused_article(self, research_data: List[Dict], plant_name: str, 
                               include_front_matter: bool = True) -> str:
        """Generate a focused article that stays on topic."""

        if not plant_name:
            raise ValueError("Plant name is required")

        logger.info(f"Generating focused article for {plant_name}")

        # Reset content tracking
        self.used_content_hashes = set()

        # Generate title
        title_templates = [
            f"The Magnificent {plant_name}: South Africa's Iconic Flowering Plant",
            f"Discovering {plant_name}: A Botanical Treasure of South Africa",
            f"{plant_name}: Beauty and Heritage in South African Flora",
            f"Exploring {plant_name}: Nature's Artistry in South Africa"
        ]
        selected_title = random.choice(title_templates)

        # Build sections with strong topic focus
        html_sections = []

        # Introduction
        intro_content = self.extract_relevant_content(research_data, plant_name, 'general', max_items=1)
        intro_text = self.generate_focused_section(
            intro_content, plant_name, 
            f"Write an engaging introduction about {plant_name} as a South African plant",
            max_length=80, min_length=40
        )
        if not intro_text:
            intro_text = self._generate_template_content(plant_name, 'introduction')
        
        html_sections.extend(self.create_html_paragraphs(intro_text, "intro"))

        # Physical Characteristics
        char_content = self.extract_relevant_content(research_data, plant_name, 'characteristics', max_items=2)
        char_text = self.generate_focused_section(
            char_content, plant_name,
            f"Describe the distinctive physical features and appearance of {plant_name}",
            max_length=100, min_length=50
        )
        if not char_text:
            char_text = self._generate_template_content(plant_name, 'characteristics')
            
        html_sections.append('<h2 class="section-heading">Distinctive Features</h2>')
        html_sections.extend(self.create_html_paragraphs(char_text, "section-characteristics"))

        # Natural Habitat
        habitat_content = self.extract_relevant_content(research_data, plant_name, 'habitat', max_items=2)
        habitat_text = self.generate_focused_section(
            habitat_content, plant_name,
            f"Explain where {plant_name} naturally grows in South Africa and its habitat requirements",
            max_length=100, min_length=50
        )
        if not habitat_text:
            habitat_text = self._generate_template_content(plant_name, 'habitat')
            
        html_sections.append('<h2 class="section-heading">Natural Habitat</h2>')
        html_sections.extend(self.create_html_paragraphs(habitat_text, "section-habitat"))

        # Cultural Significance
        cultural_content = self.extract_relevant_content(research_data, plant_name, 'cultural', max_items=2)
        cultural_text = self.generate_focused_section(
            cultural_content, plant_name,
            f"Discuss the cultural importance and uses of {plant_name} in South Africa",
            max_length=100, min_length=50
        )
        if not cultural_text:
            cultural_text = self._generate_template_content(plant_name, 'cultural')
            
        html_sections.append('<h2 class="section-heading">Cultural Significance</h2>')
        html_sections.extend(self.create_html_paragraphs(cultural_text, "section-cultural"))

        # Conservation note
        conservation_text = f"As South Africa's national flower, {plant_name} represents the country's commitment to preserving its unique botanical heritage. Conservation efforts ensure this iconic species continues to thrive in both natural habitats and cultivated gardens."
        html_sections.append('<h2 class="section-heading">Conservation</h2>')
        html_sections.extend(self.create_html_paragraphs(conservation_text, "section-conservation"))

        # Compile final article
        article_parts = []

        if include_front_matter:
            article_parts.append(self.generate_jekyll_front_matter(plant_name, selected_title))

        article_parts.append('\n\n'.join(html_sections))

        final_article = '\n'.join(article_parts)
        
        logger.info(f"Focused article generated successfully for {plant_name}")
        return final_article

    def generate_article(self, research_data: List[Dict], plant_name: str, 
                        include_front_matter: bool = True) -> str:
        """Backward compatibility method - calls generate_focused_article."""
        return self.generate_focused_article(research_data, plant_name, include_front_matter)


# Alias for backward compatibility - you can import this as ArticleGenerator
ArticleGenerator = FocusedArticleGenerator

# Convenience functions for backward compatibility
def generate_article(research_data: List[Dict], plant_name: str) -> str:
    """Generate article using default settings (backward compatibility)."""
    generator = ArticleGenerator()
    return generator.generate_focused_article(research_data, plant_name, include_front_matter=False)

def generate_plant_title(plant_name: str) -> str:
    """Generate an engaging title for the plant article (backward compatibility)."""
    title_templates = [
        f"The Magnificent {plant_name}: South Africa's Iconic Flowering Plant",
        f"Discovering {plant_name}: A Botanical Treasure of South Africa", 
        f"{plant_name}: Beauty and Heritage in South African Flora",
        f"Exploring {plant_name}: Nature's Artistry in South Africa"
    ]
    return random.choice(title_templates)

def generate_focused_article(research_data: List[Dict], plant_name: str) -> str:
    """Generate a focused article using the improved generator."""
    generator = FocusedArticleGenerator()
    return generator.generate_focused_article(research_data, plant_name, include_front_matter=False)