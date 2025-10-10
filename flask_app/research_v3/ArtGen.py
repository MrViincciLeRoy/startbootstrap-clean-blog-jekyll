
"""
Enhanced Article Generator with 5-Section Structure using RAG System
Sections: Introduction, Facts, Care, Benefits, and Conclusion
"""
import os
import random
from datetime import datetime
from typing import List, Dict, Any

class EnhancedPlantArticleGenerator:
    """
    Generates structured plant articles with 5 sections using RAG system
    """

    def __init__(self, rag_system=None):
        """
        Initialize the generator with optional RAG system

        Args:
            rag_system: Instance of RAGSystem for AI-powered content generation
        """
        self.rag_system = rag_system

    def generate_introduction(self, plant_name: str, research_data: List[Dict]) -> str:
        """Generate engaging introduction section"""
        if self.rag_system and research_data:
            # Use RAG to generate introduction
            query = f"Write an engaging introduction about {plant_name}, including its origin and significance"
            result = self.rag_system.query(query, k=3, max_new_tokens=300, temperature=0.7)
            intro = result['answer']
        else:
            # Fallback introduction
            intro = f"""Welcome to our comprehensive guide on {plant_name}, one of South Africa's most
            fascinating indigenous plants. This remarkable species has captured the attention of botanists,
            gardeners, and plant enthusiasts worldwide due to its unique characteristics and cultural significance.
            In this article, we'll explore everything you need to know about this extraordinary plant, from its
            natural habitat to practical care tips."""

        return f"""<h2 class="section-heading">Introduction</h2>
<p>{intro}</p>"""

    def generate_facts_section(self, plant_name: str, research_data: List[Dict]) -> str:
        """Generate interesting facts section"""
        facts_html = ['<h2 class="section-heading">Fascinating Facts</h2>']

        if self.rag_system and research_data:
            # Use RAG to generate facts
            query = f"What are the most interesting botanical facts about {plant_name}?"
            result = self.rag_system.query(query, k=5, max_new_tokens=400, temperature=0.7)
            facts_content = result['answer']
            facts_html.append(f'<p>{facts_content}</p>')
        else:
            # Extract facts from research data
            fact_items = []
            for item in research_data:
                content = item.get('content', '').strip()
                if len(content) > 100 and any(keyword in content.lower()
                    for keyword in ['native', 'species', 'family', 'discovered', 'named']):
                    fact_items.append(content[:250] + '...' if len(content) > 250 else content)
                    if len(fact_items) >= 3:
                        break

            if fact_items:
                facts_html.append('<ul class="plant-facts">')
                for fact in fact_items:
                    facts_html.append(f'<li>{fact}</li>')
                facts_html.append('</ul>')
            else:
                # Fallback facts
                facts_html.append(f'''<p>{plant_name} is part of South Africa's incredible botanical heritage,
                which includes over 20,000 plant species. This plant has evolved unique adaptations to thrive
                in its native environment, showcasing nature's remarkable ability to create specialized solutions
                for survival.</p>
                <ul class="plant-facts">
                    <li>Indigenous to South Africa's diverse ecosystems</li>
                    <li>Adapted to local climate conditions and soil types</li>
                    <li>Plays an important role in the local ecosystem</li>
                    <li>Part of the Cape Floral Kingdom, a UNESCO World Heritage Site</li>
                </ul>''')

        return '\n'.join(facts_html)

    def generate_care_section(self, plant_name: str, research_data: List[Dict]) -> str:
        """Generate plant care and cultivation section"""
        care_html = ['<h2 class="section-heading">Care & Cultivation</h2>']

        if self.rag_system and research_data:
            # Use RAG for care instructions
            query = f"How do you care for and cultivate {plant_name}? Include watering, light, soil, and propagation."
            result = self.rag_system.query(query, k=5, max_new_tokens=500, temperature=0.6)
            care_content = result['answer']
            care_html.append(f'<p>{care_content}</p>')
        else:
            # Extract care info from research
            care_info = []
            for item in research_data:
                content = item.get('content', '').strip()
                if any(keyword in content.lower() for keyword in
                    ['water', 'soil', 'sun', 'light', 'grow', 'plant', 'care', 'propagat']):
                    care_info.append(content[:300] + '...' if len(content) > 300 else content)
                    if len(care_info) >= 2:
                        break

            if care_info:
                for info in care_info:
                    care_html.append(f'<p>{info}</p>')
            else:
                # Fallback care guide
                care_html.append(f'''<p>Proper care is essential for helping your {plant_name} thrive.
                Here are the key requirements:</p>

                <h3>Light Requirements</h3>
                <p>Most South African plants prefer full sun to partial shade, depending on their natural
                habitat. Research the specific light needs of your plant to ensure optimal growth.</p>

                <h3>Watering</h3>
                <p>Water moderately during the growing season, allowing soil to dry between waterings.
                Reduce watering in winter months to prevent root rot.</p>

                <h3>Soil & Fertilization</h3>
                <p>Use well-draining soil with good organic content. Feed during the growing season with
                a balanced fertilizer designed for indigenous plants.</p>

                <h3>Maintenance</h3>
                <p>Prune after flowering to maintain shape and encourage new growth. Remove dead or
                diseased material promptly.</p>''')

        return '\n'.join(care_html)

    def generate_benefits_section(self, plant_name: str, research_data: List[Dict]) -> str:
        """Generate benefits and uses section"""
        benefits_html = ['<h2 class="section-heading">Benefits & Traditional Uses</h2>']

        if self.rag_system and research_data:
            # Use RAG for benefits
            query = f"What are the medicinal, ecological, and cultural benefits of {plant_name}?"
            result = self.rag_system.query(query, k=5, max_new_tokens=400, temperature=0.7)
            benefits_content = result['answer']
            benefits_html.append(f'<p>{benefits_content}</p>')
        else:
            # Extract benefits from research
            benefits_info = []
            for item in research_data:
                content = item.get('content', '').strip()
                if any(keyword in content.lower() for keyword in
                    ['medicin', 'tradition', 'use', 'benefit', 'treat', 'heal', 'cultur']):
                    benefits_info.append(content[:300] + '...' if len(content) > 300 else content)
                    if len(benefits_info) >= 2:
                        break

            if benefits_info:
                for info in benefits_info:
                    benefits_html.append(f'<p>{info}</p>')
            else:
                # Fallback benefits
                benefits_html.append(f'''<p>{plant_name} offers multiple benefits to both ecosystems and people:</p>

                <h3>Ecological Value</h3>
                <p>This plant plays a crucial role in its native ecosystem, providing food and habitat for
                various species including pollinators, birds, and insects. It contributes to biodiversity
                and helps maintain ecological balance.</p>

                <h3>Traditional Knowledge</h3>
                <p>Indigenous communities have long recognized the value of South African plants. Traditional
                knowledge systems have identified various uses for native species, from medicinal applications
                to practical household purposes.</p>

                <h3>Horticultural Appeal</h3>
                <p>For gardeners, this plant offers beauty, drought tolerance, and adaptability. It's an
                excellent choice for water-wise gardens and adds authentic South African character to
                landscapes.</p>''')

        return '\n'.join(benefits_html)

    def generate_conclusion(self, plant_name: str, research_data: List[Dict]) -> str:
        """Generate conclusion/summary section using HF model"""
        conclusion_html = ['<h2 class="section-heading">Conclusion</h2>']

        if self.rag_system and research_data:
            # Use RAG to generate comprehensive summary
            query = f"Summarize the key points about {plant_name} including its importance, care needs, and value"
            result = self.rag_system.query(query, k=5, max_new_tokens=350, temperature=0.6)
            conclusion = result['answer']
            conclusion_html.append(f'<p>{conclusion}</p>')
        else:
            # Fallback conclusion
            conclusion_html.append(f'''<p>{plant_name} exemplifies the extraordinary botanical diversity
            of South Africa. From its unique adaptations to its ecological importance and practical benefits,
            this plant represents a valuable component of our natural heritage.</p>

            <p>Whether you're a gardener looking to cultivate indigenous species, a researcher studying
            South African flora, or simply someone who appreciates the beauty of native plants, {plant_name}
            offers much to explore and appreciate. By understanding and preserving these species, we contribute
            to conservation efforts and maintain the rich biodiversity that makes South Africa's flora world-renowned.</p>

            <p>We hope this comprehensive guide has provided valuable insights into this remarkable plant.
            Continue exploring the wonderful world of South African botanical treasures!</p>''')

        return '\n'.join(conclusion_html)

    def generate_full_article(self, plant_name: str, research_data: List[Dict],
                            include_front_matter: bool = True) -> str:
        """
        Generate complete article with all 5 sections

        Args:
            plant_name: Name of the plant
            research_data: List of research data dictionaries
            include_front_matter: Whether to include Jekyll front matter

        Returns:
            Complete HTML article
        """
        date = datetime.now()

        # Generate Jekyll front matter
        if include_front_matter:
            front_matter = f"""---
layout: post
title: "The Complete Guide to {plant_name}"
subtitle: "Discover the facts, care tips, and benefits of this remarkable South African plant"
date: {date.strftime('%Y-%m-%d %H:%M:%S')}
background: '/img/posts/{random.randint(1, 6):02d}.jpg'
categories: [South African Plants, Botany, Plant Care]
tags: [{plant_name.lower()}, indigenous-plants, south-african-flora, plant-guide]
---

"""
        else:
            front_matter = ""

        # Generate all sections
        sections = [
            self.generate_introduction(plant_name, research_data),
            self.generate_facts_section(plant_name, research_data),
            self.generate_care_section(plant_name, research_data),
            self.generate_benefits_section(plant_name, research_data),
            self.generate_conclusion(plant_name, research_data)
        ]

        # Add image placeholder (optional)
        image_section = f'''<img class="img-fluid" src="/img/plants/{plant_name.lower().replace(' ', '-')}.jpg"
             alt="{plant_name}" onerror="this.src='/img/posts/default-plant.jpg'">
<span class="caption text-muted">{plant_name} in its natural habitat</span>

'''

        # Combine everything
        article_body = '\n\n'.join(sections)
        full_article = front_matter + image_section + article_body

        return full_article


# Integration function for existing test_generator.py
def create_enhanced_generator(rag_system=None):
    """
    Factory function to create generator compatible with test_generator.py

    Usage in test_generator.py:
        from enhanced_generator import create_enhanced_generator
        generator = create_enhanced_generator(rag_system)
        article = generator.generate_full_article(plant_name, research_data)
    """
    return EnhancedPlantArticleGenerator(rag_system)

"""
# Standalone usage example
if __name__ == "__main__":
    rag = RAGSystem(
        embedding_model='all-MiniLM-L6-v2',
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

    # Query the system
    #question = "How to care for roses?"
    #result = rag.query(question, k=5, max_new_tokens=900, temperature=0.7)

    # Display results
    print("\n" + "="*70)
    #print("QUESTION:", result['question'])
    print("\n" + "-"*70)
    #print("ANSWER:", result['answer'])
    print("\n" + "-"*70)
    print("SOURCES:")
    #for i, source in enumerate(result['sources'], 1):
        #print(f"{i}. {source.get('title', 'Unknown')} ({source.get('source', 'Unknown')})")
        #print(f"   URL: {source.get('url', 'N/A')}")

    # Show retrieved documents with similarity scores
    print("\n" + "-"*70)
    print("RETRIEVED DOCUMENTS:")
    #for i, doc in enumerate(result['retrieved_docs'], 1):
        #print(f"\n{i}. Similarity: {doc['similarity']:.3f} | Distance: {doc['distance']:.3f}")
        #print(f"   Source: {doc['metadata'].get('title', 'Unknown')}")
        #print(f"   Text: {doc['text'][:150]}...")
    #print("="*
    generator = EnhancedPlantArticleGenerator()

    # Generate article
    article = generator.generate_full_article(
        plant_name="Rosa rubiginosa" ,
        research_data=data,
        include_front_matter=True
    )
    with open('test.html','w') as f:
        f.write(article)
    print(article[700:1800] + "...")
    print(f"\nTotal length: {len(article)} characters")"""