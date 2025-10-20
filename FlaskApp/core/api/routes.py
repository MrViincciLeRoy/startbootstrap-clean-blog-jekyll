"""
API endpoints
"""
from flask import jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json
from FlaskApp.services.github_manager import get_github_manager
from FlaskApp.services.ai_settings_manager import AISettingsManager

ai_settings = AISettingsManager()

def setup_api_routes(bp):
    """Setup API routes"""
    
    @bp.route('/api/sync-check')
    @login_required
    def sync_check():
        gh = get_github_manager()
        try:
            latest_commit = gh.repo.get_commits()[0]
            return jsonify({
                'status': 'success',
                'latest_commit': {
                    'sha': latest_commit.sha[:7],
                    'message': latest_commit.commit.message,
                    'date': latest_commit.commit.author.date.isoformat(),
                    'author': latest_commit.commit.author.name
                }
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @bp.route('/api/ai-settings')
    @login_required
    def get_ai_settings_api():
        gh = get_github_manager()
        settings, _ = ai_settings.load_settings_from_github(gh)
        return jsonify({
            'status': 'success',
            'settings': settings
        })
    
    @bp.route('/api/ai-settings/<key>')
    @login_required
    def get_ai_setting_api(key):
        valid_keys = [
            'include_front_matter', 'fetch_images', 'embedding_model',
            'llm_model', 'config_path', 'database_path', 'device',
            'load_in_8bit', 'max_articles_per_run'
        ]
        
        if key not in valid_keys:
            return jsonify({'status': 'error', 'message': 'Invalid setting key'}), 400
        
        gh = get_github_manager()
        settings, _ = ai_settings.load_settings_from_github(gh)
        value = settings.get(key, ai_settings.defaults.get(key))
        return jsonify({
            'status': 'success',
            'key': key,
            'value': value
        })
    
    @bp.route('/trigger-generation', methods=['POST'])
    @login_required
    def trigger_generation():
        gh = get_github_manager()
        settings = ai_settings.load_settings()
        
        try:
            workflow_config = {
                'timestamp': datetime.now().isoformat(),
                'triggered_by': current_user.username,
                'ai_settings': settings
            }
            
            config_path = 'workflow_config.json'
            with open(config_path, 'w') as f:
                json.dump(workflow_config, f, indent=2)
            
            if gh.trigger_workflow('mainBlog.yml'):
                device_info = settings.get('device', 'cpu')
                model_info = settings.get('llm_model', 'LiquidAI/LFM2-1.2B-RAG')
                return jsonify({
                    'status': 'success',
                    'message': f'Article generation workflow triggered! (Device: {device_info}, Model: {model_info})'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Error triggering workflow. Check GitHub Actions settings.'
                }), 500
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500