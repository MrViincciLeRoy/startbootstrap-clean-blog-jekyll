"""
V4 JSON configuration file management
"""
import os
import json
from datetime import datetime

class V4ConfigManager:
    """Manages V4 JSON configuration files in GitHub repo"""
    
    V4_PATH = os.path.join('flask_app', 'research_v4')
    
    CONFIG_FILES = {
        'ai_settings': {
            'path': os.path.join(V4_PATH, '.ai_settings.json'), 
            'label': 'AI Settings',
            'icon': 'fa-robot',
            'description': 'Configure embedding and LLM models, device settings, and generation parameters',
            'editable_fields': [
                'include_front_matter', 'fetch_images', 'embedding_model', 'llm_model',
                'config_path', 'database_path', 'device', 'load_in_8bit', 'max_articles_per_run'
            ]
        },
        'article_config': {
            'path': os.path.join(V4_PATH, 'article_config.json'), 
            'label': 'Article Configuration',
            'icon': 'fa-newspaper',
            'description': 'Manage article templates, headings, image settings, and content cleaning rules',
            'editable_fields': ['headings', 'image_settings', 'content_cleaning']
        },
        'search_config': {
            'path': os.path.join(V4_PATH, 'search_config.json'), 
            'label': 'Search Configuration',
            'icon': 'fa-search',
            'description': 'Configure search strategy, domains, and research questions for article generation',
            'editable_fields': ['search', 'supported_extensions', 'skip_domains', 'search_strategy', 'questions']
        },
        'config': {
            'path': os.path.join(V4_PATH, 'config.json'), 
            'label': 'Application Config',
            'icon': 'fa-cogs',
            'description': 'API settings, scraping configuration, and output preferences',
            'editable_fields': ['api', 'scraping', 'output']
        },
        'domain_reliability': {
            'path': os.path.join(V4_PATH, 'domain_reliability.json'), 
            'label': 'Domain Reliability Scores',
            'icon': 'fa-globe',
            'description': 'Source reliability ratings for different domains and research sources',
            'editable_fields': ['south_african', 'international_botanical', 'educational', 'general_gardening']
        }
    }
    
    @staticmethod
    def load_config(gh_manager, config_key):
        """Load a specific config file"""
        if config_key not in V4ConfigManager.CONFIG_FILES:
            return None, None
        
        file_path = V4ConfigManager.CONFIG_FILES[config_key]['path']
        file_data = gh_manager.get_file_content(file_path)
        
        if file_data:
            try:
                config = json.loads(file_data['content'])
                return config, file_data
            except json.JSONDecodeError as e:
                print(f"Error parsing {config_key}: {e}")
                return None, file_data
        
        return None, None
    
    @staticmethod
    def save_config(gh_manager, config_key, config_data, file_data):
        """Save a configuration file"""
        if config_key not in V4ConfigManager.CONFIG_FILES:
            return False
        
        file_path = V4ConfigManager.CONFIG_FILES[config_key]['path']
        json_content = json.dumps(config_data, indent=2)
        commit_msg = f"Update {config_key} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return gh_manager.update_file(file_path, json_content, commit_msg, file_data['sha'])
    
    @staticmethod
    def get_config_schema(config_key):
        """Get schema/metadata for a config"""
        return V4ConfigManager.CONFIG_FILES.get(config_key, {})