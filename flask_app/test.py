"""
Standalone script to test article generation about South African plants.
Updated to work with research_v3 folder structure and output Jekyll HTML files.
"""
import os
import sys
import random
import time
from datetime import datetime

# Add the current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import from your research_v3 module structure
try:
    from research_v3.Spider import search 
    print("✓ Successfully imported search from research_v3.Spider")
except ImportError as e:
    print(f"❌ Error importing search: {e}")
    print("Make sure research_v3/Spider.py exists and contains the search function")
    sys.exit(1)

try:
    from research_v3.FloraDatabase import FloraDatabase 
    print("✓ Successfully imported FloraDatabase from research_v3.FloraDatabase")
except ImportError as e:
    print(f"❌ Error importing FloraDatabase: {e}")
    print("Make sure research_v3/FloraDatabase.py exists and contains the FloraDatabase class")
    sys.exit(1)

generator_imported = False
try:
    from research_v3.ImgSearch import WikiCommonsImageFetcher, EnhancedPlantArticleGenerator 
    print("✓ Successfully imported WikiCommonsImageFetcher, EnhancedPlantArticleGenerator from research_v3.ImgSearch")
    generator_imported = True 
except ImportError as e:
    print(f"❌ Error importing image search classes: {e}")
    print("Make sure research_v3/ImgSearch.py exists and contains the required classes")
    sys.exit(1)

try:
    from research_v3.RagSys import RAGSystem 
    print("✓ Successfully imported RAGSystem from research_v3.RagSys")
except ImportError as e:
    print(f"❌ Error importing RAGSystem: {e}")
    print("Make sure research_v3/RagSys.py exists and contains the RAGSystem class")
    sys.exit(1)


# Simple fallback generator if none found
class BasicJekyllGenerator:
    """Basic Jekyll article generator as fallback"""
    
    def generate_article(self, research_data, plant_name, include_front_matter=True):
        """Generate a basic Jekyll article"""
        date = datetime.now()
        
        # Create front matter
        front_matter = f"""---
layout: post
title: "Discovering {plant_name}: A South African Botanical Wonder"
subtitle: "Exploring the unique characteristics and heritage of this remarkable indigenous plant"
date: {date.strftime('%Y-%m-%d %H:%M:%S')}
background: '/img/posts/{random.randint(1, 6):02d}.jpg'
---

"""
        
        # Generate content based on research data
        content_parts = []
        
        # Introduction
        content_parts.append(f"<p>We're excited to share comprehensive information about {plant_name}, one of South Africa's fascinating indigenous plant species! Our research system has gathered detailed information from leading botanical databases to bring you accurate and up-to-date knowledge about this remarkable plant.</p>")
        
        # Research sources section
        content_parts.append("<h2>Botanical Research Sources</h2>")
        content_parts.append(f"<p>Our comprehensive research on {plant_name} draws from authoritative botanical sources including:</p>")
        content_parts.append("<ul>")
        content_parts.append("    <li>South African National Biodiversity Institute (SANBI)</li>")
        content_parts.append("    <li>PlantZAfrica</li>")
        content_parts.append("    <li>Wikipedia</li>")
        content_parts.append("    <li>Academic databases (PubMed, OpenAlex)</li>")
        content_parts.append("    <li>Botanical websites and databases</li>")
        content_parts.append("</ul>")
        
        # Content from research data
        if research_data:
            content_parts.append("<h2>Research Findings</h2>")
            
            # Group content by type
            general_content = []
            characteristics_content = []
            benefits_content = []
            
            for item in research_data:
                content_text = item.get('text', '').strip()
                if len(content_text) > 50:  # Only use substantial content
                    content_type = item.get('metadata', {}).get('type', 'general_info')
                    if content_type == 'characteristics':
                        characteristics_content.append(content_text[:300] + "..." if len(content_text) > 300 else content_text)
                    elif content_type == 'benefits':
                        benefits_content.append(content_text[:300] + "..." if len(content_text) > 300 else content_text)
                    else:
                        general_content.append(content_text[:400] + "..." if len(content_text) > 400 else content_text)
            
            # Add general information
            if general_content:
                for i, content in enumerate(general_content[:2]):  # Limit to 2 items
                    content_parts.append(f"<p>{content}</p>")
            
            # Add characteristics if found
            if characteristics_content:
                content_parts.append("<h2>Plant Characteristics</h2>")
                for content in characteristics_content[:1]:  # Limit to 1 item
                    content_parts.append(f"<p>{content}</p>")
            
            # Add benefits/uses if found
            if benefits_content:
                content_parts.append("<h2>Traditional Uses & Benefits</h2>")
                for content in benefits_content[:1]:  # Limit to 1 item
                    content_parts.append(f"<p>{content}</p>")
        
        # Default content sections
        content_parts.append("<h2>South African Botanical Heritage</h2>")
        content_parts.append(f"<p>{plant_name} represents the extraordinary diversity of South Africa's flora. As an indigenous species, it has evolved unique adaptations to thrive in the region's diverse landscapes and challenging environmental conditions.</p>")
        
        content_parts.append("<h2>Conservation & Future</h2>")
        content_parts.append(f"<p>Understanding and preserving native species like {plant_name} is crucial for maintaining South Africa's position as one of the world's most biodiverse countries. These plants contribute to ecosystem health and may hold keys to future discoveries in medicine and sustainable agriculture.</p>")
        
        # Final paragraph
        content_parts.append("<p>Our ongoing research into South African flora continues to reveal fascinating insights about these remarkable plants. We remain committed to providing accurate, comprehensive information about botanical treasures like this one.</p>")
        
        # Combine all parts
        html_content = '\n\n'.join(content_parts)
        
        if include_front_matter:
            return front_matter + html_content
        else:
            return html_content


def get_posts_directory():
    """Get the correct path to the _posts directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    posts_dir = os.path.join(script_dir, '_posts')
    os.makedirs(posts_dir, exist_ok=True)
    return posts_dir


def show_article_preview(full_article, plant_name):
    """Show a preview of the generated article"""
    print(f"\n📝 Article Preview for '{plant_name}':")
    print("=" * 80)
    
    # Split front matter and content for better preview
    if full_article.startswith('---'):
        parts = full_article.split('---', 2)
        if len(parts) >= 3:
            front_matter = f"---{parts[1]}---"
            content = parts[2].strip()
            
            print("FRONT MATTER:")
            print(front_matter)
            print(f"\nCONTENT PREVIEW (first 400 chars):")
            preview = content[:400]
            if len(content) > 400:
                preview += "..."
            print(preview)
        else:
            print("FULL PREVIEW (first 500 chars):")
            print(full_article[:500] + "..." if len(full_article) > 500 else full_article)
    else:
        print("FULL PREVIEW (first 500 chars):")
        print(full_article[:500] + "..." if len(full_article) > 500 else full_article)
    
    print("=" * 80)


def save_article(full_article, plant_name):
    """Save the article to a file"""
    date = datetime.now()
    clean_name = plant_name.lower().replace(' ', '-').replace('(', '').replace(')', '')
    clean_name = ''.join(c for c in clean_name if c.isalnum() or c in '-_')
    filename = f"{date.strftime('%Y-%m-%d')}-{clean_name}.html"

    posts_dir = get_posts_directory()
    filepath = os.path.join(posts_dir, filename)

    print(f"📁 Saving article to {filename}...")
    print(f"📂 Posts directory: {posts_dir}")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_article)

    print(f"✓ Article saved successfully!")
    print(f"📄 Full path: {filepath}")
    print(f"📊 File size: {len(full_article):,} characters")
    
    return filepath

def run():
    """Main function to generate article from incomplete plant in database"""
    try:
        db_path = os.path.join('research_v3', 'flora_data.db')

        if not os.path.exists(db_path):
            print(f"❌ Database not found at: {db_path}")
            # ... error handling

        db = FloraDatabase(db_path)
        # db = FloraDatabase("flora_data.db")
        incomplete_plants = db.get_all_incomplete_plants()
        
        if not incomplete_plants:
            print("No incomplete plants found in database.")
            return False
        
        data = None
        plant_name = None

        # Try each incomplete plant until we find one with valid search data
        for x in incomplete_plants:
            title = str(x[1])
            sci_name = db.get_scientific_name_by_title(title)
            if not sci_name:
                print(f"Warning: No scientific name found for title '{title}'. Skipping.")
                continue

            # Check if already complete (FIXED LOGIC)
            is_complete = db.check_if_complete(sci_name)
            if is_complete == False:
                print(f"Plant '{sci_name}' is already complete. Skipping.")
                continue

            print(f"\n🔍 Attempting to fetch data for: {sci_name}")
            
            # Attempt to fetch external data
            data = search(sci_name)
            if data:
                print(f"✓ Successfully retrieved data for: {sci_name}")
                plant_name = sci_name
                break  # Found valid data — exit loop
            else:
                print(f"⚠️ No data found for '{sci_name}'. Trying next plant...")
        else:
            # This runs if the loop completes without breaking
            print("\n❌ No suitable incomplete plant with available data was found.")
            return False

        # Proceed only if we have valid data and plant_name
        if data is not None and plant_name is not None:
            print(f"\n🌿 Processing: {plant_name}")
            print(f"📊 Retrieved {len(data)} data items")
            
            # Test image fetching
            print("\n🖼️ Fetching images...")
            fetcher = WikiCommonsImageFetcher()
            images = fetcher.get_images_for_plant(plant_name)

            print(f"Found {len(images)} images:")
            for i, img in enumerate(images[:5], 1):  # Show first 5
                print(f"{i}. {img['title']}")
                print(f"   URL: {img['thumb_url']}")

            # Initialize RAG system
            print("\n🤖 Initializing RAG system...")
            rag = RAGSystem(
                embedding_model='all-MiniLM-L6-v2',
                llm_model='LiquidAI/LFM2-1.2B-RAG'
            )

            # Prepare texts and metadata
            texts = []
            metadata = []
            for item in data:
                texts.append(item['text'])
                metadata.append(item['metadata'])

            # Build index
            print("📚 Building vector index...")
            rag.build_index(texts, metadata)

            # Load LLM
            print("🧠 Loading language model...")
            rag.load_llm(device='cpu', load_in_8bit=False)

            # Generate article
            print("✍️ Generating article...")
            generator = EnhancedPlantArticleGenerator(rag_system=rag, fetch_images=True)
            article = generator.generate_full_article(
                plant_name=plant_name,
                research_data=data,
                include_front_matter=True
            )

            # Save to file
            filepath = save_article(article, plant_name)
            
            # Show preview
            show_article_preview(article, plant_name)

            # Mark as complete in database
            print(f"\n✅ Marking '{plant_name}' as complete in database...")
            db.mark_plant_complete(plant_name, complete=False)

            print(f"\n🎉 SUCCESS! Article generated and saved to {filepath}")
            print(f"📏 Total length: {len(article)} characters")
            
            return True
        
        return False
        
    except Exception as e:
        print(f"\n❌ Error in run(): {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_setup():
    """Test the setup and show configuration"""
    print("🧪 Testing setup...")
    
    # Test posts directory
    posts_dir = get_posts_directory()
    print(f"✓ Posts directory: {posts_dir}")
    print(f"✓ Directory exists: {os.path.exists(posts_dir)}")
    
    # Test imports
    print(f"✓ Research module: research_v3")
    print(f"✓ Generator imported: {generator_imported}")
    
    # Show file structure
    print(f"\nFile structure check:")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script location: {os.path.dirname(os.path.abspath(__file__))}")
    
    if os.path.exists('research_v3'):
        print("✓ research_v3 directory found")
        research_files = [f for f in os.listdir('research_v3') if f.endswith('.py')]
        print(f"  Python files: {research_files}")
    else:
        print("❌ research_v3 directory not found")
        print("Make sure you're running this script from the correct directory")
    
    # Test database connection
    try:
        db = FloraDatabase("flora_data.db")
        incomplete = db.get_all_incomplete_plants()
        print(f"\n✓ Database connection successful")
        print(f"✓ Found {len(incomplete)} incomplete plants")
        
        if incomplete:
            print("\nFirst 5 incomplete plants:")
            for i, plant in enumerate(incomplete[:5], 1):
                print(f"  {i}. {plant[1]}")
    except Exception as e:
        print(f"\n❌ Database error: {e}")


def show_usage():
    """Display usage instructions"""
    print("🌿 South African Plant Article Generator")
    print("=" * 50)
    
    posts_dir = get_posts_directory()
    print(f"📁 Posts will be saved to: {posts_dir}")
    print(f"🤖 Generator status: {'Loaded' if generator_imported else 'Not loaded'}")
    
    print("\nUsage:")
    print("  Generate article: python test_generator.py")
    print("  Test setup:       python test_generator.py --test")
    print("  Help:             python test_generator.py --help")
    
    print("\nThe script will:")
    print("  1. Find an incomplete plant in the database")
    print("  2. Search for information about the plant")
    print("  3. Generate a comprehensive article with images")
    print("  4. Save it as a Jekyll-compatible HTML file")
    print("  5. Mark the plant as complete in the database")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test':
            test_setup()
        elif sys.argv[1] in ['--help', '-h']:
            show_usage()
        else:
            print("Unknown argument. Use --help for usage information.")
    else:
        # Run the main generation process
        print("🚀 Starting article generation process...\n")
        success = run()
        
        if success:
            print("\n✅ Article generation completed successfully!")
            print("📂 Check the _posts directory for your new Jekyll article!")
        else:
            print("\n❌ Article generation failed. Check the error messages above.")
            sys.exit(1)
