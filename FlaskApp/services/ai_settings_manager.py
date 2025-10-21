"""
AI settings management for article generation
"""
import os
import json
from datetime import datetime
from FlaskApp.config import Config

class AISettingsManager:
    """Manages AI article generation settings stored in GitHub repo"""
    
    def __init__(self, config_file=None):
        self.config_file = config_file or Config.AI_CONFIG_FILE
        self.github_path = os.path.join('FlaskApp','services', 'v4', '.ai_settings.json')
        self.defaults = {
            'include_front_matter': True,
            'fetch_images': True,
            'embedding_model': 'all-MiniLM-L6-v2',
            'llm_model': 'LiquidAI/LFM2-1.2B-RAG',
            'config_path': 'research_v3/article_config.json',
            'database_path': 'research_v3/flora_data.db',
            'device': 'cpu',
            'load_in_8bit': False,
            'max_articles_per_run': 1
        }
    
    def load_settings_from_github(self, gh_manager):
        """Load AI settings from GitHub repo"""
        try:
            file_data = gh_manager.get_file_content(self.github_path)
            if file_data:
                settings = json.loads(file_data['content'])
                return {**self.defaults, **settings}, file_data
            else:
                print(f"Settings file not found at {self.github_path}, using defaults")
                return self.defaults.copy(), None
        except Exception as e:
            print(f"Error loading AI settings from GitHub: {e}")
            return self.defaults.copy(), None
    
    def load_settings(self):
        """Load AI settings from local file (fallback)"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                    return {**self.defaults, **settings}
            except Exception as e:
                print(f"Error loading local AI settings: {e}")
                return self.defaults.copy()
        return self.defaults.copy()
    
    def save_settings_to_github(self, settings, gh_manager, file_data=None):
        """Save AI settings to GitHub repo"""
        try:
            validated_settings = {}
            for key in self.defaults:
                if key in settings:
                    validated_settings[key] = settings[key]
                else:
                    validated_settings[key] = self.defaults[key]
            
            json_content = json.dumps(validated_settings, indent=2)
            
            sha = file_data['sha'] if file_data else None
            commit_msg = f"Update AI settings - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            if gh_manager.update_file(self.github_path, json_content, commit_msg, sha):
                print(f"✓ AI settings saved to GitHub: {self.github_path}")
                return True
            else:
                print(f"✗ Failed to save AI settings to GitHub")
                return False
                
        except Exception as e:
            print(f"✗ Error saving AI settings to GitHub: {e}")
            return False
    
    def get_setting(self, key, default=None):
        """Get a specific setting from local file"""
        settings = self.load_settings()
        return settings.get(key, default or self.defaults.get(key))
    
    def update_setting(self, key, value, gh_manager=None):
        """Update a single setting"""
        if gh_manager:
            settings, file_data = self.load_settings_from_github(gh_manager)
            settings[key] = value
            return self.save_settings_to_github(settings, gh_manager, file_data)
        else:
            settings = self.load_settings()
            settings[key] = value
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(settings, f, indent=2)
                return True
            except Exception as e:
                print(f"Error updating setting locally: {e}")
                return False
