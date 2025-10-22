"""
V4 JSON configuration file management - Fixed Version
"""
import os
import json
from datetime import datetime

class V4ConfigManager:
    """Manages V4 JSON configuration files in GitHub repo"""
    
    CONFIG_FILES = {
        'ai_settings': {
            'filename': 'ai_settings.json',
            'label': 'AI Settings',
            'icon': 'fa-robot',
            'description': 'Configure embedding and LLM models, device settings, and generation parameters'
        },
        'article_config': {
            'filename': 'article_config.json',
            'label': 'Article Configuration',
            'icon': 'fa-newspaper',
            'description': 'Manage article templates, headings, image settings, and content cleaning rules'
        },
        'search_config': {
            'filename': 'search_config.json',
            'label': 'Search Configuration',
            'icon': 'fa-search',
            'description': 'Configure search strategy, domains, and research questions for article generation'
        },
        'config': {
            'filename': 'config.json',
            'label': 'Application Config',
            'icon': 'fa-cogs',
            'description': 'API settings, scraping configuration, and output preferences'
        },
        'domain_reliability': {
            'filename': 'domain_reliability.json',
            'label': 'Domain Reliability Scores',
            'icon': 'fa-globe',
            'description': 'Source reliability ratings for different domains and research sources'
        }
    }
    
    @staticmethod
    def get_file_path(config_key):
        """Get the full GitHub path for a config file using os.path.join"""
        if config_key not in V4ConfigManager.CONFIG_FILES:
            return None
        
        filename = V4ConfigManager.CONFIG_FILES[config_key]['filename']
        # Use os.path.join like ai_settings_manager
        return os.path.join('FlaskApp', 'services', 'v4', 'config', filename)
    
    @staticmethod
    def load_config(gh_manager, config_key):
        """
        Load a specific config file from GitHub
        
        Returns:
            tuple: (config_dict, file_data) or (None, None) if error
        """
        if config_key not in V4ConfigManager.CONFIG_FILES:
            print(f"Invalid config key: {config_key}")
            return None, None
        
        file_path = V4ConfigManager.get_file_path(config_key)
        print(f"Loading config from: {file_path}")
        
        try:
            file_data = gh_manager.get_file_content(file_path)
            
            if not file_data:
                print(f"File not found: {file_path}")
                return None, None
            
            config = json.loads(file_data['content'])
            print(f"Successfully loaded {config_key}")
            return config, file_data
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error in {config_key}: {e}")
            return None, file_data
        except Exception as e:
            print(f"Error loading {config_key}: {e}")
            return None, None
    
    @staticmethod
    def save_config(gh_manager, config_key, config_data, file_data):
        """
        Save a configuration file to GitHub
        
        Args:
            gh_manager: GitHub manager instance
            config_key: Configuration key (e.g., 'article_config')
            config_data: Dictionary containing the configuration
            file_data: Existing file data with SHA
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        if config_key not in V4ConfigManager.CONFIG_FILES:
            print(f"Invalid config key: {config_key}")
            return False
        
        file_path = V4ConfigManager.get_file_path(config_key)
        label = V4ConfigManager.CONFIG_FILES[config_key]['label']
        
        try:
            # Convert config to formatted JSON
            json_content = json.dumps(config_data, indent=2, ensure_ascii=False)
            
            # Create commit message
            commit_msg = f"Update {label} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Get SHA from file_data
            sha = file_data['sha'] if file_data else None
            
            print(f"Saving to: {file_path}")
            print(f"Commit message: {commit_msg}")
            print(f"SHA: {sha}")
            
            # Update file in GitHub
            success = gh_manager.update_file(file_path, json_content, commit_msg, sha)
            
            if success:
                print(f"✓ Successfully saved {label}")
                return True
            else:
                print(f"✗ Failed to save {label}")
                return False
                
        except Exception as e:
            print(f"✗ Error saving {config_key}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def get_config_schema(config_key):
        """Get schema/metadata for a config"""
        return V4ConfigManager.CONFIG_FILES.get(config_key, {})
    
    @staticmethod
    def get_all_configs():
        """Get list of all available configs"""
        return list(V4ConfigManager.CONFIG_FILES.keys())
