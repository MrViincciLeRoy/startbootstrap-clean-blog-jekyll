# Research V4 - Configuration-Driven Architecture

## Overview
Research V4 is a refactored version of V3 that derives all configuration values from JSON files instead of hardcoding them. This maintains all functionality while enabling easy configuration management.

## File Structure

```
flask_app/research_v4/
├── .ai_settings.json           # AI and database settings
├── config.json                 # Application configuration
├── article_config.json         # Article generation headings
├── domain_reliability.json     # Domain reliability scores
├── search_config.json          # Search parameters
├── FloraDatabase.py            # Database operations (unchanged)
├── FloraWikipediaScraper.py    # Wikipedia scraping (unchanged)
├── ImgSearch.py                # Article generation (unchanged)
├── RagSys.py                   # RAG system (unchanged)
├── Spider.py                   # Main spider (refactored for JSON config)
└── ConfigManager.py            # NEW: Centralized config management
```

## Key Changes from V3

### 1. **ConfigManager.py** (NEW)
Centralized configuration management that loads and provides access to all JSON settings.

### 2. **JSON Configuration Files**

#### `.ai_settings.json`
```json
{
  "include_front_matter": true,
  "fetch_images": true,
  "embedding_model": "all-MiniLM-L6-v2",
  "llm_model": "LiquidAI/LFM2-1.2B-RAG",
  "config_path": "research_v4/article_config.json",
  "database_path": "research_v4/flora_data.db",
  "device": "cpu",
  "load_in_8bit": false,
  "max_articles_per_run": 1,
  "search_config_path": "research_v4/search_config.json"
}
```

#### `config.json`
```json
{
  "app_name": "South African Flora Research System",
  "version": "4.0",
  "debug": false,
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  },
  "api": {
    "serpapi_key_env": "SERP_API_KEY",
    "request_timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 2
  },
  "scraping": {
    "delay_between_requests": 1.5,
    "max_sources": 20,
    "request_headers": {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
  },
  "output": {
    "posts_directory": "_posts",
    "enable_preview": true,
    "save_json": true
  }
}
```

#### `search_config.json`
```json
{
  "search": {
    "delay": 1.5,
    "max_sources": 20,
    "add_search_terms": false
  },
  "supported_extensions": [".html", ".htm", ".php", ".asp", ".aspx", ".pdf", ".txt"],
  "unsupported_extensions": [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar", ".tar", ".gz", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".mp4", ".avi", ".mov", ".mp3", ".wav"],
  "skip_domains": ["pinterest.com", "youtube.com", "amazon.com", "ebay.com"],
  "search_strategy": {
    "prioritize_sa": true,
    "sa_domains_first": true,
    "general_sa_second": true,
    "international_last": true
  },
  "questions": [
    "what are the benefits",
    "interesting facts",
    "care and cultivation guide",
    "what does it look like physical description"
  ]
}
```

#### `domain_reliability.json`
```json
{
  "south_african": {
    "up.ac.za": 0.98,
    "uct.ac.za": 0.98,
    "wits.ac.za": 0.98,
    "sun.ac.za": 0.98,
    "ru.ac.za": 0.97,
    "ukzn.ac.za": 0.97,
    "ufs.ac.za": 0.97,
    "unisa.ac.za": 0.96,
    "nwu.ac.za": 0.96,
    "sanbi.org": 0.98,
    "sanbi.org.za": 0.98,
    "plantzafrica.com": 0.97,
    "ispotnature.org": 0.95,
    "biodiversityadvisor.sanbi.org": 0.97,
    "redlist.sanbi.org": 0.97,
    "pza.sanbi.org": 0.97
  },
  "international_botanical": {
    "en.wikipedia.org": 0.93,
    "kew.org": 0.95,
    "powo.science.kew.org": 0.95,
    "missouribotanicalgarden.org": 0.88,
    "britannica.com": 0.87,
    "rhs.org.uk": 0.86
  },
  "educational": {
    "extension.wisc.edu": 0.80,
    "ces.ncsu.edu": 0.80,
    "extension.umn.edu": 0.80
  },
  "general_gardening": {
    "thespruce.com": 0.70,
    "plants.usda.gov": 0.85,
    "plantnet.rbgsyd.nsw.gov.au": 0.82
  }
}
```

#### `article_config.json`
```json
{
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
    "remove_source_markers": true,
    "remove_incomplete_paragraphs": true,
    "min_paragraph_length": 50,
    "remove_citations": true
  }
}
```

## Usage

The V4 system loads all configuration at startup:

```python
from research_v4.ConfigManager import ConfigManager

# Initialize configuration
config = ConfigManager()

# Access settings
ai_settings = config.get_ai_settings()
search_config = config.get_search_config()
domain_reliability = config.get_domain_reliability()

# Use throughout the application
spider = EnhancedPlantSpider(
    serpapi_key=config.get_api_key(),
    delay=config.get_search_delay(),
    max_sources=config.get_max_sources()
)
```

## Benefits

1. **Easy Configuration**: Change settings without modifying code
2. **Environment-Specific Settings**: Different configs for dev/prod
3. **Centralized Management**: All settings in one place
4. **No Code Changes**: Existing classes remain unchanged
5. **Backward Compatible**: Works exactly like V3
6. **JSON Validation**: Can validate configs on startup

## Migration from V3

1. Copy all `.py` files from V3 to V4
2. Add `ConfigManager.py` to V4
3. Create JSON configuration files (provided above)
4. Update imports to use V4
5. No changes needed to existing Python files
