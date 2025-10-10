from FloraDatabase import FloraDatabase  # ✅ Correct - this class exists
from Spider import search
from ImgSearch import WikiCommonsImageFetcher, EnhancedPlantArticleGenerator
from RagSys import RAGSystem

def run():
    db = FloraDatabase("flora_data.db")
    incomplete_plants = db.get_all_incomplete_plants()
    data = None
    plant_name = None

    # Try each incomplete plant until we find one with valid search data
    for x in incomplete_plants:
        title = str(x[1])
        sci_name = db.get_scientific_name_by_title(title)
        if not sci_name:
            print(f"Warning: No scientific name found for title '{title}'. Skipping.")
            continue

        plant_name = sci_name
        is_complete = db.check_if_complete(sci_name)
        if not is_complete:
            print(f"Plant '{sci_name}' is already complete. Skipping.")
            continue

        # Attempt to fetch external data
        data = search(sci_name)
        if data:
            print(f"Successfully retrieved data for: {sci_name}")
            break  # Found valid data — exit loop
        else:
            print(f"No data found for '{sci_name}'. Trying next plant...")
            data = None
            plant_name = None
    else:
        # This runs if the loop completes without breaking (i.e., no plant worked)
        print("No suitable incomplete plant with available data was found.")
        return

    # Proceed only if we have valid data and plant_name
    if data is not None and plant_name is not None:
        # Test image fetching (optional; can also use plant_name instead of hardcoded)
        fetcher = WikiCommonsImageFetcher()
        images = fetcher.get_images_for_plant(plant_name)  # Use actual plant name

        print(f"Found {len(images)} images:")
        for i, img in enumerate(images, 1):
            print(f"{i}. {img['title']}")
            print(f"   URL: {img['thumb_url']}")
            print()

        rag = RAGSystem(
            embedding_model='all-MiniLM-L6-v2',
            llm_model='LiquidAI/LFM2-1.2B-RAG'  # or any HF model
        )

        # Prepare texts and metadata
        texts = []
        metadata = []
        for item in data:
            texts.append(item['text'])
            metadata.append(item['metadata'])

        # Build index
        rag.build_index(texts, metadata)

        # Load LLM
        rag.load_llm(device='cpu', load_in_8bit=False)

        # Generate article
        generator = EnhancedPlantArticleGenerator(rag_system=rag, fetch_images=True)
        article = generator.generate_full_article(
            plant_name=plant_name,
            research_data=data,
            include_front_matter=True
        )

        # Save to file
        filename = f'{plant_name.capitalize().strip()}.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(article)

        print(f"\n✅ Article generated and saved to {filename}")
        print(f"Total length: {len(article), article[600:1800]} characters")