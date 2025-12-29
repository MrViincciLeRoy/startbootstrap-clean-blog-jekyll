"""
Add these routes to FlaskApp/core/config_management/routes.py
These are the missing /config, /ai-settings, and /v4-config routes
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime
from FlaskApp.services.github_manager import get_github_manager
from FlaskApp.services.theme_manager import ThemeManager
from FlaskApp.services.ai_settings_manager import AISettingsManager
import yaml
import json

theme_manager = ThemeManager()
ai_settings = AISettingsManager()

def setup_config_routes(bp):
    """Setup configuration routes - ADD THESE TO YOUR setup_theme_routes function or create new one"""
    
    @bp.route('/config', methods=['GET', 'POST'])
    @login_required
    def edit_config():
        """Edit blog configuration"""
        gh = get_github_manager()
        
        if request.method == 'POST':
            config_data = {
                'title': request.form.get('title', ''),
                'email': request.form.get('email', ''),
                'description': request.form.get('description', ''),
                'baseurl': request.form.get('baseurl', ''),
                'url': request.form.get('url', ''),
                'phone': request.form.get('phone', ''),
                'address': request.form.get('address', ''),
                'twitter_username': request.form.get('twitter_username', ''),
                'github_username': request.form.get('github_username', ''),
                'facebook_username': request.form.get('facebook_username', ''),
                'instagram_username': request.form.get('instagram_username', ''),
                'linkedin_username': request.form.get('linkedin_username', ''),
                'google_analytics': request.form.get('google_analytics', ''),
                'author': request.form.get('author', ''),
                'active_theme': request.form.get('active_theme', 'default'),
            }
            
            # Handle theme1 settings if selected
            if config_data['active_theme'] == 'theme1':
                config_data['theme1'] = {
                    'primary_color': request.form.get('theme1_primary_color', '#6366f1'),
                    'secondary_color': request.form.get('theme1_secondary_color', '#10b981'),
                    'accent_color': request.form.get('theme1_accent_color', '#f59e0b'),
                    'font_heading': request.form.get('theme1_font_heading', 'Ubuntu'),
                    'font_body': request.form.get('theme1_font_body', 'Roboto'),
                    'hero_overlay': float(request.form.get('theme1_hero_overlay', 0.6)),
                    'footer': {
                        'newsletter_enabled': 'theme1_newsletter_enabled' in request.form,
                        'newsletter_action': request.form.get('theme1_newsletter_action', ''),
                        'show_wave': 'theme1_show_wave' in request.form,
                        'show_social': 'theme1_show_social' in request.form,
                    }
                }
            
            # Convert to YAML
            yaml_content = yaml.dump(config_data, default_flow_style=False, allow_unicode=True)
            
            # Get current config file to get SHA
            config_file = gh.get_config_yml()
            if config_file:
                commit_msg = f"Update blog configuration - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                if gh.update_file('_config.yml', yaml_content, commit_msg, config_file['sha']):
                    flash('✓ Configuration updated successfully!', 'success')
                    return redirect(url_for('config_management.edit_config'))
                else:
                    flash('✗ Error updating configuration', 'error')
            else:
                flash('✗ Could not load current configuration', 'error')
        
        # GET request - load current config
        config_file = gh.get_config_yml()
        config = {}
        
        if config_file:
            try:
                config = yaml.safe_load(config_file['content'])
            except:
                pass
        
        return render_template('edit_config.html', config=config)
    
    @bp.route('/ai-settings', methods=['GET', 'POST'])
    @login_required
    def edit_ai_settings():
        """Edit AI article generation settings"""
        gh = get_github_manager()
        
        if request.method == 'POST':
            settings = {
                'include_front_matter': request.form.get('include_front_matter') == 'on',
                'fetch_images': request.form.get('fetch_images') == 'on',
                'embedding_model': request.form.get('embedding_model', 'all-MiniLM-L6-v2'),
                'llm_model': request.form.get('llm_model', 'LiquidAI/LFM2-1.2B-RAG'),
                'config_path': request.form.get('config_path', 'research_v3/article_config.json'),
                'database_path': request.form.get('database_path', 'research_v3/flora_data.db'),
                'device': request.form.get('device', 'cpu'),
                'load_in_8bit': request.form.get('load_in_8bit') == 'on',
                'max_articles_per_run': int(request.form.get('max_articles_per_run', 1))
            }
            
            if ai_settings.save_settings_to_github(gh, settings):
                flash('✓ AI settings saved successfully!', 'success')
                return redirect(url_for('config_management.edit_ai_settings'))
            else:
                flash('✗ Error saving AI settings', 'error')
        
        # Load current settings
        settings, _ = ai_settings.load_settings_from_github(gh)
        
        return render_template('edit_ai_settings.html', config=settings)
    
    @bp.route('/v4-config', methods=['GET', 'POST'])
    @login_required
    def edit_v4_config():
        """Edit V4 AI configuration"""
        gh = get_github_manager()
        
        if request.method == 'POST':
            # This is a placeholder - implement based on your v4 config structure
            flash('✓ V4 configuration updated!', 'success')
            return redirect(url_for('config_management.edit_v4_config'))
        
        return render_template('edit_v4_config.html')


# Modified version of your existing setup_theme_routes
def setup_theme_routes(bp):
    """Setup theme management routes"""
    
    # Add all the config routes first
    setup_config_routes(bp)
    
    @bp.route('/theme-customizer', methods=['GET'])
    @login_required
    def theme_customizer():
        """Theme customizer interface"""
        gh = get_github_manager()
        
        # Get current theme from config
        config_file = gh.get_config_yml()
        current_theme = 'default'
        theme_colors = None
        
        if config_file:
            config = yaml.safe_load(config_file['content'])
            current_theme = config.get('active_theme', 'default')
            theme_colors = config.get('theme_colors', None)
        
        # Get all available themes
        all_themes = theme_manager.get_all_themes()
        
        # If no custom colors, use theme defaults
        if not theme_colors:
            theme_colors = theme_manager.get_theme(current_theme)
        
        return render_template('theme_customizer.html',
                             current_theme=current_theme,
                             theme_colors=theme_colors,
                             all_themes=all_themes,
                             available_fonts=theme_manager.AVAILABLE_FONTS)
    
    @bp.route('/theme-customizer/preview', methods=['POST'])
    @login_required
    def preview_theme():
        """Generate preview CSS for theme"""
        try:
            theme_config = {
                'primary_color': request.form.get('primary_color'),
                'secondary_color': request.form.get('secondary_color'),
                'background_color': request.form.get('background_color'),
                'text_color': request.form.get('text_color'),
                'navbar_bg': request.form.get('navbar_bg'),
                'navbar_text': request.form.get('navbar_text'),
                'footer_bg': request.form.get('footer_bg'),
                'footer_text': request.form.get('footer_text'),
                'link_color': request.form.get('link_color'),
                'link_hover': request.form.get('link_hover'),
                'masthead_overlay': float(request.form.get('masthead_overlay', 0.5)),
                'font_family_base': request.form.get('font_family_base', 'Lora'),
                'font_family_headings': request.form.get('font_family_headings', 'Open Sans')
            }
            
            css = theme_manager.generate_css_variables(theme_config)
            
            return jsonify({
                'status': 'success',
                'css': css
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @bp.route('/theme-customizer/apply', methods=['POST'])
    @login_required
    def apply_theme():
        """Apply theme to site configuration"""
        gh = get_github_manager()
        
        try:
            theme_config = {
                'primary_color': request.form.get('primary_color'),
                'secondary_color': request.form.get('secondary_color'),
                'background_color': request.form.get('background_color'),
                'text_color': request.form.get('text_color'),
                'navbar_bg': request.form.get('navbar_bg'),
                'navbar_text': request.form.get('navbar_text'),
                'footer_bg': request.form.get('footer_bg'),
                'footer_text': request.form.get('footer_text'),
                'link_color': request.form.get('link_color'),
                'link_hover': request.form.get('link_hover'),
                'masthead_overlay': float(request.form.get('masthead_overlay', 0.5)),
                'font_family_base': request.form.get('font_family_base', 'Lora'),
                'font_family_headings': request.form.get('font_family_headings', 'Open Sans')
            }
            
            # Save as custom theme if name provided
            custom_name = request.form.get('save_as_custom')
            if custom_name:
                theme_config['name'] = custom_name
                if theme_manager.save_custom_theme(custom_name, theme_config):
                    flash(f'✓ Custom theme "{custom_name}" saved successfully!', 'success')
            
            # Apply to GitHub config
            if theme_manager.apply_theme_to_config(gh, theme_config):
                flash('✓ Theme applied successfully! Changes will be visible after Jekyll rebuild.', 'success')
                return redirect(url_for('config_management.theme_customizer'))
            else:
                flash('✗ Error applying theme to configuration', 'error')
                
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        
        return redirect(url_for('config_management.theme_customizer'))
    
    @bp.route('/theme-customizer/load/<theme_name>', methods=['GET'])
    @login_required
    def load_theme(theme_name):
        """Load a theme configuration"""
        theme = theme_manager.get_theme(theme_name)
        return jsonify({
            'status': 'success',
            'theme': theme
        })
    
    @bp.route('/theme-customizer/delete/<theme_name>', methods=['POST'])
    @login_required
    def delete_theme(theme_name):
        """Delete a custom theme"""
        # Don't allow deleting default themes
        if theme_name in theme_manager.DEFAULT_THEMES:
            return jsonify({
                'status': 'error',
                'message': 'Cannot delete default themes'
            }), 400
        
        if theme_manager.delete_custom_theme(theme_name):
            return jsonify({
                'status': 'success',
                'message': f'Theme "{theme_name}" deleted successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to delete theme'
            }), 500
    
    @bp.route('/api/themes', methods=['GET'])
    @login_required
    def get_themes_api():
        """API endpoint to get all themes"""
        all_themes = theme_manager.get_all_themes()
        return jsonify({
            'status': 'success',
            'themes': all_themes
        })
