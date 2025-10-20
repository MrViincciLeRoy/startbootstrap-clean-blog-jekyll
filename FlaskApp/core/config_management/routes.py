"""
Configuration management routes
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import yaml
import json
from FlaskApp.services.github_manager import get_github_manager
from FlaskApp.services.ai_settings_manager import AISettingsManager
from FlaskApp.services.v4_config_manager import V4ConfigManager

ai_settings = AISettingsManager()

def setup_config_routes(bp):
    """Setup configuration routes"""
    
    @bp.route('/config', methods=['GET', 'POST'])
    @login_required
    def edit_config():
        gh = get_github_manager()
        
        if request.method == 'POST':
            author_input = request.form.get('author', '').strip()
            author_value = author_input if author_input else ' ' * 13 + 'HAA[B]'
            
            config_dict = {
                'title': request.form.get('title'),
                'email': request.form.get('email'),
                'description': request.form.get('description'),
                'baseurl': request.form.get('baseurl'),
                'url': request.form.get('url'),
                'author': author_value,
                'phone': request.form.get('phone'),
                'address': request.form.get('address'),
                'active_theme': request.form.get('active_theme', 'default'),
                'twitter_username': request.form.get('twitter_username'),
                'github_username': request.form.get('github_username'),
                'facebook_username': request.form.get('facebook_username'),
                'instagram_username': request.form.get('instagram_username'),
                'linkedin_username': request.form.get('linkedin_username'),
                'google_analytics': request.form.get('google_analytics'),
                'markdown': 'kramdown',
                'paginate': 10,
                'paginate_path': '/posts/page:num/'
            }
            
            if request.form.get('active_theme') == 'theme1':
                config_dict['theme1'] = {
                    'primary_color': request.form.get('theme1_primary_color', '#6366f1'),
                    'secondary_color': request.form.get('theme1_secondary_color', '#10b981'),
                    'accent_color': request.form.get('theme1_accent_color', '#f59e0b'),
                    'hero_overlay': float(request.form.get('theme1_hero_overlay', '0.6')),
                    'font_heading': request.form.get('theme1_font_heading', 'Ubuntu'),
                    'font_body': request.form.get('theme1_font_body', 'Roboto'),
                    'footer': {
                        'newsletter_enabled': 'theme1_newsletter_enabled' in request.form,
                        'newsletter_action': request.form.get('theme1_newsletter_action', ''),
                        'show_wave': 'theme1_show_wave' in request.form,
                        'show_social': 'theme1_show_social' in request.form
                    }
                }
            
            config_dict = {k: v for k, v in config_dict.items() if v or k in ['active_theme', 'theme1']}
            
            if gh.update_config_yml(config_dict, f"Update config - {datetime.now().strftime('%Y-%m-%d %H:%M')}"):
                flash('Configuration updated successfully!', 'success')
                return redirect(url_for('config_management.edit_config'))
            else:
                flash('Error updating configuration', 'error')
        
        config_file = gh.get_config_yml()
        if config_file:
            config = yaml.safe_load(config_file['content'])
        else:
            config = {}
        
        return render_template('edit_config.html', config=config)
    
    @bp.route('/ai-settings', methods=['GET', 'POST'])
    @login_required
    def edit_ai_settings():
        gh = get_github_manager()
        
        if request.method == 'POST':
            try:
                settings = {
                    'include_front_matter': 'include_front_matter' in request.form,
                    'fetch_images': 'fetch_images' in request.form,
                    'embedding_model': request.form.get('embedding_model', 'all-MiniLM-L6-v2'),
                    'llm_model': request.form.get('llm_model', 'LiquidAI/LFM2-1.2B-RAG'),
                    'config_path': request.form.get('config_path', 'research_v3/article_config.json'),
                    'database_path': request.form.get('database_path', 'research_v3/flora_data.db'),
                    'device': request.form.get('device', 'cpu'),
                    'load_in_8bit': 'load_in_8bit' in request.form,
                    'max_articles_per_run': int(request.form.get('max_articles_per_run', 1))
                }
                
                valid_devices = ['cpu', 'cuda', 'mps']
                if settings['device'] not in valid_devices:
                    flash('Invalid device selected', 'error')
                    return redirect(url_for('config_management.edit_ai_settings'))
                
                if not 1 <= settings['max_articles_per_run'] <= 10:
                    flash('Max articles per run must be between 1 and 10', 'error')
                    return redirect(url_for('config_management.edit_ai_settings'))
                
                current_settings, file_data = ai_settings.load_settings_from_github(gh)
                
                if ai_settings.save_settings_to_github(settings, gh, file_data):
                    flash('✓ AI settings updated and committed to repository!', 'success')
                    return redirect(url_for('config_management.edit_ai_settings'))
                else:
                    flash('✗ Error saving AI settings to repository', 'error')
                    return redirect(url_for('config_management.edit_ai_settings'))
                    
            except ValueError as e:
                flash(f'Invalid input: {str(e)}', 'error')
                return redirect(url_for('config_management.edit_ai_settings'))
            except Exception as e:
                flash(f'Unexpected error: {str(e)}', 'error')
                return redirect(url_for('config_management.edit_ai_settings'))
        
        current_settings, file_data = ai_settings.load_settings_from_github(gh)
        return render_template('edit_ai_settings.html', config=current_settings)
    
    @bp.route('/v4-config', methods=['GET'])
    @login_required
    def v4_config_list():
        gh = get_github_manager()
        configs = []
        
        for key, config_info in V4ConfigManager.CONFIG_FILES.items():
            config_data, file_data = V4ConfigManager.load_config(gh, key)
            configs.append({
                'key': key,
                'label': config_info['label'],
                'icon': config_info['icon'],
                'description': config_info['description'],
                'status': 'loaded' if config_data else 'error'
            })
        
        return render_template('v4_config_list.html', configs=configs)
    
    @bp.route('/v4-config/<config_key>', methods=['GET', 'POST'])
    @login_required
    def edit_v4_config(config_key):
        gh = get_github_manager()
        
        schema = V4ConfigManager.get_config_schema(config_key)
        if not schema:
            flash('Configuration not found', 'error')
            return redirect(url_for('config_management.v4_config_list'))
        
        if request.method == 'POST':
            try:
                config_data, file_data = V4ConfigManager.load_config(gh, config_key)
                
                if not config_data:
                    flash('Error loading configuration', 'error')
                    return redirect(url_for('config_management.edit_v4_config', config_key=config_key))
                
                raw_data = request.form.get('json_data', '{}')
                updated_data = json.loads(raw_data)
                
                if V4ConfigManager.save_config(gh, config_key, updated_data, file_data):
                    flash(f'✓ {schema["label"]} updated and committed to repository!', 'success')
                    return redirect(url_for('config_management.edit_v4_config', config_key=config_key))
                else:
                    flash('✗ Error saving configuration to repository', 'error')
            
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON format: {str(e)}', 'error')
            except Exception as e:
                flash(f'Unexpected error: {str(e)}', 'error')
        
        config_data, file_data = V4ConfigManager.load_config(gh, config_key)
        
        if not config_data:
            flash('Could not load configuration file', 'error')
            return redirect(url_for('config_management.v4_config_list'))
        
        return render_template('edit_v4_config.html',
                             config_key=config_key,
                             config=config_data,
                             schema=schema,
                             json_str=json.dumps(config_data, indent=2))
