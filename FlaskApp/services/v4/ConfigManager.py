"""
ConfigManager.py - Centralized configuration management for Research V4
Loads and provides access to all JSON configuration files
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """
    Centralized configuration manager that loads all JSON settings.
    All configuration is read-only to prevent accidental modifications.
    """
    
    def __init__(self, config_dir: str = "services/v4/config", verbose: bool = False):
        """
        Initialize ConfigManager and load all configuration files.
        
        Args:
            config_dir: Directory containing configuration files
            verbose: Print debug information during loading
        """
        self.config_dir = Path(config_dir)
        self.verbose = verbose
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize all configurations
        self._configs = {}
        self._load_all_configs()
    
    def _load_config(self, filename: str, default: Optional[Dict] = None) -> Dict:
        """
        Load a JSON configuration file.
        
        Args:
            filename: Name of the JSON file
            default: Default configuration if file doesn't exist
            
        Returns:
            Configuration dictionary
        """
        filepath = self.config_dir / filename
        
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if self.verbose:
                    print(f"✓ Loaded {filename}")
                return config
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing {filename}: {e}")
                return default or {}
            except Exception as e:
                print(f"❌ Error loading {filename}: {e}")
                return default or {}
        else:
            if self.verbose:
                print(f"⚠️  {filename} not found, using defaults")
            # Create default config if doesn't exist
            if default:
                self._save_config(filename, default)
            return default or {}
    
    def _save_config(self, filename: str, config: Dict) -> None:
        """Save configuration to JSON file."""
        filepath = self.config_dir / filename
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            if self.verbose:
                print(f"✓ Saved {filename}")
        except Exception as e:
            print(f"❌ Error saving {filename}: {e}")
    
    def _load_all_configs(self) -> None:
        """Load all configuration files with defaults."""
        
        # AI Settings
        ai_settings_default = {
            "include_front_matter": True,
            "fetch_images": True,
            "embedding_model": "all-MiniLM-L6-v2",
            "llm_model": "LiquidAI/LFM2-1.2B-RAG",
            "config_path": "research_v4/article_config.json",
            "database_path": "research_v4/flora_data.db",
            "device": "cpu",
            "load_in_8bit": False,
            "max_articles_per_run": 1,
            "search_config_path": "research_v4/search_config.json"
        }
        self._configs['ai_settings'] = self._load_config('.ai_settings.json', ai_settings_default)
        
        # Main Config
        config_default = {
            "app_name": "South African Flora Research System",
            "version": "4.0",
            "debug": False,
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
                "enable_preview": True,
                "save_json": True
            }
        }
        self._configs['config'] = self._load_config('config.json', config_default)
        
        # Search Config
        search_config_default = {
            "search": {
                "delay": 1.5,
                "max_sources": 20,
                "add_search_terms": False
            },
            "supported_extensions": [".html", ".htm", ".php", ".asp", ".aspx", ".pdf", ".txt"],
            "unsupported_extensions": [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar", ".tar", ".gz", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".mp4", ".avi", ".mov", ".mp3", ".wav"],
            "skip_domains": ["pinterest.com", "youtube.com", "amazon.com", "ebay.com"],
            "search_strategy": {
                "prioritize_sa": True,
                "sa_domains_first": True,
                "general_sa_second": True,
                "international_last": True
            },
            "questions": [
                "what are the benefits",
                "interesting facts",
                "care and cultivation guide",
                "what does it look like physical description"
            ]
        }
        self._configs['search_config'] = self._load_config('search_config.json', search_config_default)
        
        # Domain Reliability
        domain_reliability_default = {
            "south_african": {
                "up.ac.za": 0.98, "uct.ac.za": 0.98, "wits.ac.za": 0.98,
                "sun.ac.za": 0.98, "ru.ac.za": 0.97, "ukzn.ac.za": 0.97,
                "ufs.ac.za": 0.97, "unisa.ac.za": 0.96, "nwu.ac.za": 0.96,
                "sanbi.org": 0.98, "sanbi.org.za": 0.98, "plantzafrica.com": 0.97,
                "ispotnature.org": 0.95, "biodiversityadvisor.sanbi.org": 0.97,
                "redlist.sanbi.org": 0.97, "pza.sanbi.org": 0.97
            },
            "international_botanical": {
                "en.wikipedia.org": 0.93, "kew.org": 0.95, "powo.science.kew.org": 0.95,
                "missouribotanicalgarden.org": 0.88, "britannica.com": 0.87, "rhs.org.uk": 0.86
            },
            "educational": {
                "extension.wisc.edu": 0.80, "ces.ncsu.edu": 0.80, "extension.umn.edu": 0.80
            },
            "general_gardening": {
                "thespruce.com": 0.70, "plants.usda.gov": 0.85, "plantnet.rbgsyd.nsw.gov.au": 0.82
            }
        }
        self._configs['domain_reliability'] = self._load_config('domain_reliability.json', domain_reliability_default)
        
        # Article Config
        article_config_default = {
            "headings": [
                {"title": "The Complete Guide to {plant_name}", "subtitle": "Discover the facts, care tips, and benefits of this remarkable plant"},
                {"title": "Everything You Need to Know About {plant_name}", "subtitle": "A comprehensive guide to growing and caring for this beautiful species"},
                {"title": "{plant_name}: Nature's Hidden Treasure", "subtitle": "Uncover the secrets of this extraordinary South African plant"},
                {"title": "Growing {plant_name}: Expert Tips and Insights", "subtitle": "Master the art of cultivating this stunning native plant"},
                {"title": "{plant_name} Revealed", "subtitle": "Explore the fascinating world of this unique botanical specimen"}
            ],
            "image_settings": {"width": 800, "height": 600, "default_fallback": "/img/posts/default-plant.jpg"},
            "content_cleaning": {"remove_source_markers": True, "remove_incomplete_paragraphs": True, "min_paragraph_length": 50, "remove_citations": True}
        }
        self._configs['article_config'] = self._load_config('article_config.json', article_config_default)
    
    # AI Settings Access
    def get_ai_settings(self) -> Dict[str, Any]:
        """Get AI settings."""
        return self._configs['ai_settings']
    
    def get_embedding_model(self) -> str:
        """Get embedding model name."""
        return self._configs['ai_settings'].get('embedding_model', 'all-MiniLM-L6-v2')
    
    def get_llm_model(self) -> str:
        """Get LLM model name."""
        return self._configs['ai_settings'].get('llm_model', 'LiquidAI/LFM2-1.2B-RAG')
    
    def get_device(self) -> str:
        """Get device for model loading."""
        return self._configs['ai_settings'].get('device', 'cpu')
    
    def get_load_in_8bit(self) -> bool:
        """Get 8-bit loading setting."""
        return self._configs['ai_settings'].get('load_in_8bit', False)
    
    def get_database_path(self) -> str:
        """Get database file path."""
        return self._configs['ai_settings'].get('database_path', 'research_v4/flora_data.db')
    
    def get_include_front_matter(self) -> bool:
        """Get front matter inclusion setting."""
        return self._configs['ai_settings'].get('include_front_matter', True)
    
    def get_fetch_images(self) -> bool:
        """Get image fetching setting."""
        return self._configs['ai_settings'].get('fetch_images', True)
    
    # Search Config Access
    def get_search_config(self) -> Dict[str, Any]:
        """Get search configuration."""
        return self._configs['search_config']
    
    def get_search_delay(self) -> float:
        """Get delay between requests."""
        return self._configs['search_config'].get('search', {}).get('delay', 1.5)
    
    def get_max_sources(self) -> int:
        """Get maximum sources to collect."""
        return self._configs['search_config'].get('search', {}).get('max_sources', 20)
    
    def get_skip_domains(self) -> list:
        """Get list of domains to skip."""
        return self._configs['search_config'].get('skip_domains', [])
    
    def get_search_questions(self) -> list:
        """Get predefined search questions."""
        return self._configs['search_config'].get('questions', [])
    
    # API Config Access
    def get_api_key_env_name(self) -> str:
        """Get environment variable name for API key."""
        return self._configs['config'].get('api', {}).get('serpapi_key_env', 'SERP_API_KEY')
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        env_name = self.get_api_key_env_name()
        return os.getenv(env_name)
    
    def get_request_timeout(self) -> int:
        """Get request timeout in seconds."""
        return self._configs['config'].get('api', {}).get('request_timeout', 30)
    
    def get_retry_attempts(self) -> int:
        """Get retry attempts count."""
        return self._configs['config'].get('api', {}).get('retry_attempts', 3)
    
    # Output Config Access
    def get_posts_directory(self) -> str:
        """Get posts output directory."""
        return self._configs['config'].get('output', {}).get('posts_directory', '_posts')
    
    def get_enable_preview(self) -> bool:
        """Get preview enabling setting."""
        return self._configs['config'].get('output', {}).get('enable_preview', True)
    
    # Domain Reliability Access
    def get_domain_reliability(self) -> Dict[str, Dict[str, float]]:
        """Get all domain reliability scores."""
        return self._configs['domain_reliability']
    
    def get_domain_score(self, domain: str) -> Optional[float]:
        """Get reliability score for a specific domain."""
        for category, domains in self._configs['domain_reliability'].items():
            if domain in domains:
                return domains[domain]
        return None
    
    # Article Config Access
    def get_article_config(self) -> Dict[str, Any]:
        """Get article configuration."""
        return self._configs['article_config']
    
    def get_headings(self) -> list:
        """Get article heading templates."""
        return self._configs['article_config'].get('headings', [])
    
    def get_image_settings(self) -> Dict[str, Any]:
        """Get image settings."""
        return self._configs['article_config'].get('image_settings', {})
    
    def get_content_cleaning_settings(self) -> Dict[str, Any]:
        """Get content cleaning settings."""
        return self._configs['article_config'].get('content_cleaning', {})
    
    # Utility Methods
    def get_app_version(self) -> str:
        """Get application version."""
        return self._configs['config'].get('version', '4.0')
    
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self._configs['config'].get('debug', False)
    
    def get_request_headers(self) -> Dict[str, str]:
        """Get default request headers."""
        return self._configs['config'].get('scraping', {}).get('request_headers', {})
    
    def print_summary(self) -> None:
        """Print configuration summary."""
        print("\n" + "="*60)
        print("🔧 Configuration Summary - Research V4")
        print("="*60)
        
        print(f"\n📊 Application:")
        print(f"  Version: {self.get_app_version()}")
        print(f"  Debug: {self.is_debug()}")
        
        print(f"\n🤖 AI Settings:")
        print(f"  Embedding Model: {self.get_embedding_model()}")
        print(f"  LLM Model: {self.get_llm_model()}")
        print(f"  Device: {self.get_device()}")
        print(f"  Load 8-bit: {self.get_load_in_8bit()}")
        
        print(f"\n🔍 Search Settings:")
        print(f"  Delay: {self.get_search_delay()}s")
        print(f"  Max Sources: {self.get_max_sources()}")
        print(f"  Skip Domains: {len(self.get_skip_domains())}")
        
        print(f"\n📁 Output:")
        print(f"  Posts Directory: {self.get_posts_directory()}")
        print(f"  Enable Preview: {self.get_enable_preview()}")
        
        print(f"\n📚 Domain Categories:")
        for category in self._configs['domain_reliability'].keys():
            count = len(self._configs['domain_reliability'][category])
            print(f"  {category}: {count} domains")
        
        print("="*60 + "\n")


# Example usage
if __name__ == "__main__":
    # Initialize configuration
    config = ConfigManager(verbose=True)
    
    # Print summary
    config.print_summary()
    
    # Access individual settings
    print("Sample Accesses:")
    print(f"  Embedding Model: {config.get_embedding_model()}")
    print(f"  Search Delay: {config.get_search_delay()}s")
    print(f"  Database Path: {config.get_database_path()}")
    print(f"  API Key exists: {config.get_api_key() is not None}")
