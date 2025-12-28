"""
Theme management service for handling custom theme configurations
"""
import os
import json
from datetime import datetime

class ThemeManager:
    """Manages theme configurations and color customization"""
    
    # Default theme presets
    DEFAULT_THEMES = {
        'default': {
            'name': 'Classic Clean',
            'primary_color': '#0085A1',
            'secondary_color': '#6c757d',
            'background_color': '#ffffff',
            'text_color': '#212529',
            'navbar_bg': '#ffffff',
            'navbar_text': '#212529',
            'footer_bg': '#f8f9fa',
            'footer_text': '#6c757d',
            'link_color': '#0085A1',
            'link_hover': '#006d84',
            'masthead_overlay': 0.5,
            'font_family_base': 'Lora',
            'font_family_headings': 'Open Sans'
        },
        'theme1': {
            'name': 'Modern Dark',
            'primary_color': '#7DD3E8',
            'secondary_color': '#10b981',
            'background_color': '#1a1a1a',
            'text_color': '#f8f9fa',
            'navbar_bg': '#1a1a1a',
            'navbar_text': '#adb5bd',
            'footer_bg': '#0a0a0a',
            'footer_text': '#adb5bd',
            'link_color': '#7DD3E8',
            'link_hover': '#00B4D8',
            'masthead_overlay': 0.7,
            'font_family_base': 'Roboto',
            'font_family_headings': 'Ubuntu'
        },
        'nature': {
            'name': 'Nature Green',
            'primary_color': '#10b981',
            'secondary_color': '#059669',
            'background_color': '#f0fdf4',
            'text_color': '#064e3b',
            'navbar_bg': '#ffffff',
            'navbar_text': '#064e3b',
            'footer_bg': '#ecfdf5',
            'footer_text': '#065f46',
            'link_color': '#10b981',
            'link_hover': '#059669',
            'masthead_overlay': 0.4,
            'font_family_base': 'Lora',
            'font_family_headings': 'Open Sans'
        },
        'botanical': {
            'name': 'Botanical Purple',
            'primary_color': '#8b5cf6',
            'secondary_color': '#a78bfa',
            'background_color': '#faf5ff',
            'text_color': '#4c1d95',
            'navbar_bg': '#ffffff',
            'navbar_text': '#5b21b6',
            'footer_bg': '#f5f3ff',
            'footer_text': '#6d28d9',
            'link_color': '#8b5cf6',
            'link_hover': '#7c3aed',
            'masthead_overlay': 0.5,
            'font_family_base': 'Lora',
            'font_family_headings': 'Open Sans'
        },
        'sunset': {
            'name': 'Warm Sunset',
            'primary_color': '#f59e0b',
            'secondary_color': '#ef4444',
            'background_color': '#fffbeb',
            'text_color': '#78350f',
            'navbar_bg': '#ffffff',
            'navbar_text': '#92400e',
            'footer_bg': '#fef3c7',
            'footer_text': '#92400e',
            'link_color': '#f59e0b',
            'link_hover': '#d97706',
            'masthead_overlay': 0.4,
            'font_family_base': 'Lora',
            'font_family_headings': 'Open Sans'
        },
        'ocean': {
            'name': 'Ocean Blue',
            'primary_color': '#0ea5e9',
            'secondary_color': '#06b6d4',
            'background_color': '#f0f9ff',
            'text_color': '#0c4a6e',
            'navbar_bg': '#ffffff',
            'navbar_text': '#075985',
            'footer_bg': '#e0f2fe',
            'footer_text': '#0369a1',
            'link_color': '#0ea5e9',
            'link_hover': '#0284c7',
            'masthead_overlay': 0.5,
            'font_family_base': 'Lora',
            'font_family_headings': 'Open Sans'
        }
    }
    
    # Available fonts
    AVAILABLE_FONTS = {
        'serif': ['Lora', 'Merriweather', 'Georgia', 'Times New Roman'],
        'sans-serif': ['Open Sans', 'Roboto', 'Ubuntu', 'Helvetica', 'Arial'],
        'monospace': ['Courier New', 'Monaco', 'Consolas']
    }
    
    def __init__(self):
        self.custom_themes_path = 'custom_themes.json'
        self.load_custom_themes()
    
    def load_custom_themes(self):
        """Load custom themes from file"""
        if os.path.exists(self.custom_themes_path):
            try:
                with open(self.custom_themes_path, 'r') as f:
                    self.custom_themes = json.load(f)
            except Exception as e:
                print(f"Error loading custom themes: {e}")
                self.custom_themes = {}
        else:
            self.custom_themes = {}
    
    def save_custom_theme(self, theme_name, theme_config):
        """Save a custom theme configuration"""
        self.custom_themes[theme_name] = {
            **theme_config,
            'created_at': datetime.now().isoformat(),
            'custom': True
        }
        
        try:
            with open(self.custom_themes_path, 'w') as f:
                json.dump(self.custom_themes, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving custom theme: {e}")
            return False
    
    def get_theme(self, theme_name):
        """Get theme configuration by name"""
        # Check custom themes first
        if theme_name in self.custom_themes:
            return self.custom_themes[theme_name]
        
        # Fall back to default themes
        if theme_name in self.DEFAULT_THEMES:
            return self.DEFAULT_THEMES[theme_name]
        
        # Return default theme if not found
        return self.DEFAULT_THEMES['default']
    
    def get_all_themes(self):
        """Get all available themes (default + custom)"""
        all_themes = {}
        
        # Add default themes
        for key, theme in self.DEFAULT_THEMES.items():
            all_themes[key] = {**theme, 'custom': False}
        
        # Add custom themes
        for key, theme in self.custom_themes.items():
            all_themes[key] = theme
        
        return all_themes
    
    def delete_custom_theme(self, theme_name):
        """Delete a custom theme"""
        if theme_name in self.custom_themes:
            del self.custom_themes[theme_name]
            try:
                with open(self.custom_themes_path, 'w') as f:
                    json.dump(self.custom_themes, f, indent=2)
                return True
            except Exception as e:
                print(f"Error deleting custom theme: {e}")
                return False
        return False
    
    def apply_theme_to_config(self, gh_manager, theme_config):
        """Apply theme configuration to _config.yml"""
        try:
            config_file = gh_manager.get_config_yml()
            if not config_file:
                return False
            
            import yaml
            config = yaml.safe_load(config_file['content'])
            
            # Update theme configuration
            config['theme_colors'] = {
                'primary': theme_config['primary_color'],
                'secondary': theme_config['secondary_color'],
                'background': theme_config['background_color'],
                'text': theme_config['text_color'],
                'navbar_bg': theme_config['navbar_bg'],
                'navbar_text': theme_config['navbar_text'],
                'footer_bg': theme_config['footer_bg'],
                'footer_text': theme_config['footer_text'],
                'link': theme_config['link_color'],
                'link_hover': theme_config['link_hover']
            }
            
            config['theme_settings'] = {
                'masthead_overlay': theme_config.get('masthead_overlay', 0.5),
                'font_family_base': theme_config.get('font_family_base', 'Lora'),
                'font_family_headings': theme_config.get('font_family_headings', 'Open Sans')
            }
            
            # Save to GitHub
            yaml_content = yaml.dump(config, default_flow_style=False, allow_unicode=True)
            commit_msg = f"Update theme colors - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            return gh_manager.update_file('_config.yml', yaml_content, commit_msg, config_file['sha'])
            
        except Exception as e:
            print(f"Error applying theme: {e}")
            return False
    
    def generate_css_variables(self, theme_config):
        """Generate CSS variables from theme configuration"""
        css = ":root {\n"
        css += f"  --primary-color: {theme_config['primary_color']};\n"
        css += f"  --secondary-color: {theme_config['secondary_color']};\n"
        css += f"  --background-color: {theme_config['background_color']};\n"
        css += f"  --text-color: {theme_config['text_color']};\n"
        css += f"  --navbar-bg: {theme_config['navbar_bg']};\n"
        css += f"  --navbar-text: {theme_config['navbar_text']};\n"
        css += f"  --footer-bg: {theme_config['footer_bg']};\n"
        css += f"  --footer-text: {theme_config['footer_text']};\n"
        css += f"  --link-color: {theme_config['link_color']};\n"
        css += f"  --link-hover: {theme_config['link_hover']};\n"
        css += f"  --masthead-overlay: {theme_config.get('masthead_overlay', 0.5)};\n"
        css += f"  --font-family-base: '{theme_config.get('font_family_base', 'Lora')}', serif;\n"
        css += f"  --font-family-headings: '{theme_config.get('font_family_headings', 'Open Sans')}', sans-serif;\n"
        css += "}\n"
        return css
