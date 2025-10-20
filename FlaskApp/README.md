# Flask Dashboard Refactoring Guide

Complete guide to restructure your monolithic Flask app into a modular, scalable architecture.

## Project Structure

```
flask_app/
├── __init__.py                 # App factory
├── config.py                   # Configuration
├── core/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── routes.py          # Login, logout routes
│   │   └── models.py          # User model
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── routes.py          # Dashboard routes
│   │   └── bp.py              # Blueprint definition
│   ├── posts/
│   │   ├── __init__.py
│   │   ├── routes.py          # Post management routes
│   │   └── bp.py
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── routes.py          # Page management routes
│   │   └── bp.py
│   ├── config_management/
│   │   ├── __init__.py
│   │   ├── routes.py          # Config/V4 config routes
│   │   └── bp.py
│   └── api/
│       ├── __init__.py
│       ├── routes.py          # API endpoints
│       └── bp.py
├── services/
│   ├── __init__.py
│   ├── github_manager.py       # GitHub operations
│   ├── ai_settings_manager.py  # AI settings logic
│   └── v4_config_manager.py    # V4 config logic
├── utils/
│   ├── __init__.py
│   └── decorators.py           # Custom decorators
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   └── ...
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── app.py                      # Main entry point
└── requirements.txt
```

---

## File Implementations

### 1. requirements.txt

```txt
Flask==3.0.0
Flask-Login==0.6.3
Werkzeug==3.0.1
PyGithub==2.1.1
python-dotenv==1.0.0
PyYAML==6.0.1
```

---

### 2. flask_app/config.py

```python
"""
Flask configuration settings
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-secret-key')
    
    # GitHub Configuration
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    REPO_NAME = os.getenv('REPO_NAME')
    BRANCH = os.getenv('BRANCH', 'master')
    
    # AI Settings Configuration
    AI_CONFIG_FILE = os.getenv('AI_CONFIG_FILE', 'research_v3/.ai_settings.json')
    
    # Flask Settings
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 86400

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
```

---

### 3. flask_app/__init__.py

```python
"""
Application factory
"""
from flask import Flask
from flask_login import LoginManager
import os

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_name=None):
    """Create and configure Flask application"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    from flask_app.config import config_by_name
    
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions
    login_manager.init_app(app)
    
    # Register blueprints
    from flask_app.core.auth.bp import auth_bp
    from flask_app.core.dashboard.bp import dashboard_bp
    from flask_app.core.posts.bp import posts_bp
    from flask_app.core.pages.bp import pages_bp
    from flask_app.core.config_management.bp import config_management_bp
    from flask_app.core.api.bp import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(config_management_bp)
    app.register_blueprint(api_bp)
    
    # Load user loader
    from flask_app.core.auth.models import load_user
    
    return app
```

---

### 4. flask_app/core/auth/models.py

```python
"""
User model and authentication
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_app import login_manager
import os

# Simple user storage (use database in production)
USERS = {
    'admin': generate_password_hash(os.getenv('ADMIN_PASSWORD', 'changeme'))
}

class User(UserMixin):
    """User model"""
    def __init__(self, username):
        self.id = username
        self.username = username

@login_manager.user_loader
def load_user(username):
    """Load user from database"""
    if username in USERS:
        return User(username)
    return None

def verify_credentials(username, password):
    """Verify user credentials"""
    if username in USERS and check_password_hash(USERS[username], password):
        return True
    return False
```

---

### 5. flask_app/core/auth/routes.py

```python
"""
Authentication routes
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_app.core.auth.models import User, verify_credentials

def setup_auth_routes(bp):
    """Setup authentication routes"""
    
    @bp.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.dashboard'))
        return redirect(url_for('auth.login'))
    
    @bp.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if verify_credentials(username, password):
                user = User(username)
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('dashboard.dashboard'))
            
            flash('Invalid credentials', 'error')
        
        return render_template('login.html')
    
    @bp.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('auth.login'))
```

---

### 6. flask_app/core/auth/bp.py

```python
"""
Authentication blueprint
"""
from flask import Blueprint
from flask_app.core.auth.routes import setup_auth_routes

auth_bp = Blueprint('auth', __name__, url_prefix='')
setup_auth_routes(auth_bp)
```

---

### 7. flask_app/core/dashboard/routes.py

```python
"""
Dashboard routes
"""
from flask import render_template
from flask_login import login_required
from flask_app.services.github_manager import get_github_manager

def setup_dashboard_routes(bp):
    """Setup dashboard routes"""
    
    @bp.route('/dashboard')
    @login_required
    def dashboard():
        gh = get_github_manager()
        posts = gh.list_posts()
        pages = gh.list_pages()
        
        return render_template('dashboard.html', 
                             posts=posts[:10],
                             pages=pages,
                             total_posts=len(posts))
```

---

### 8. flask_app/core/dashboard/bp.py

```python
"""
Dashboard blueprint
"""
from flask import Blueprint
from flask_app.core.dashboard.routes import setup_dashboard_routes

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='')
setup_dashboard_routes(dashboard_bp)
```

---

### 9. flask_app/core/posts/routes.py

```python
"""
Post management routes
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime
from flask_app.services.github_manager import get_github_manager

def setup_posts_routes(bp):
    """Setup post routes"""
    
    @bp.route('/posts')
    @login_required
    def list_posts():
        gh = get_github_manager()
        posts = gh.list_posts()
        return render_template('list_posts.html', posts=posts)
    
    @bp.route('/post/<path:post_path>')
    @login_required
    def view_post(post_path):
        gh = get_github_manager()
        post_file = gh.get_file_content(post_path)
        
        if not post_file:
            flash('Post not found', 'error')
            return redirect(url_for('posts.list_posts'))
        
        front_matter, body = gh.parse_front_matter(post_file['content'])
        
        return render_template('view_post.html', 
                             post_path=post_path,
                             front_matter=front_matter,
                             body=body,
                             sha=post_file['sha'])
    
    @bp.route('/post/<path:post_path>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_post(post_path):
        gh = get_github_manager()
        post_file = gh.get_file_content(post_path)
        
        if not post_file:
            flash('Post not found', 'error')
            return redirect(url_for('posts.list_posts'))
        
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            content = request.form.get('content')
            sha = request.form.get('sha')
            
            if not title or not content or not sha:
                flash('Missing required fields', 'error')
                return redirect(url_for('posts.edit_post', post_path=post_path))
            
            front_matter = {
                'layout': 'post',
                'title': title,
                'date': request.form.get('date', datetime.now().strftime('%Y-%m-%d')),
            }
            
            if description:
                front_matter['description'] = description
            
            if request.form.get('categories'):
                front_matter['categories'] = request.form.get('categories')
            
            full_content = gh.create_front_matter(front_matter, content)
            
            commit_msg = f"Update post: {title} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            if gh.update_file(post_path, full_content, commit_msg, sha):
                flash('Post updated successfully!', 'success')
                return redirect(url_for('posts.list_posts'))
            else:
                flash('Error updating post', 'error')
                return redirect(url_for('posts.edit_post', post_path=post_path))
        
        front_matter, body = gh.parse_front_matter(post_file['content'])
        
        if front_matter is None:
            front_matter = {}
        
        return render_template('edit_post.html',
                             post_path=post_path,
                             front_matter=front_matter,
                             body=body,
                             sha=post_file['sha'])
    
    @bp.route('/post/<path:post_path>/delete', methods=['POST'])
    @login_required
    def delete_post(post_path):
        gh = get_github_manager()
        
        commit_msg = f"Delete post: {post_path} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if gh.delete_file(post_path, commit_msg):
            flash('Post deleted successfully!', 'success')
        else:
            flash('Error deleting post', 'error')
        
        return redirect(url_for('posts.list_posts'))
```

---

### 10. flask_app/core/posts/bp.py

```python
"""
Posts blueprint
"""
from flask import Blueprint
from flask_app.core.posts.routes import setup_posts_routes

posts_bp = Blueprint('posts', __name__, url_prefix='')
setup_posts_routes(posts_bp)
```

---

### 11. flask_app/core/pages/routes.py

```python
"""
Page management routes
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime
from flask_app.services.github_manager import get_github_manager

def setup_pages_routes(bp):
    """Setup page routes"""
    
    @bp.route('/pages')
    @login_required
    def list_pages():
        gh = get_github_manager()
        pages = gh.list_pages()
        return render_template('list_pages.html', pages=pages)
    
    @bp.route('/edit-home-about', methods=['GET', 'POST'])
    @login_required
    def edit_home_about():
        gh = get_github_manager()
        
        if request.method == 'POST':
            new_content = request.form.get('about_content', '')
            
            file_data = gh.get_file_content('_layouts/home.html')
            if not file_data:
                flash('Could not load home layout', 'error')
                return redirect(url_for('dashboard.dashboard'))
            
            updated_content = gh.update_content_section(
                file_data['content'],
                'about-section',
                new_content
            )
            
            commit_msg = f"Update home about section - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            if gh.update_file('_layouts/home.html', updated_content, commit_msg, file_data['sha']):
                flash('Homepage about section updated successfully!', 'success')
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('Error updating homepage', 'error')
        
        file_data = gh.get_file_content('_layouts/home.html')
        if not file_data:
            flash('Could not load home layout', 'error')
            return redirect(url_for('dashboard.dashboard'))
        
        about_content = gh.extract_content_section(file_data['content'], 'about-section')
        if not about_content:
            import re
            about_match = re.search(r'<h1><u>About</u></h1>\s*<p>(.*?)</p>', file_data['content'], re.DOTALL)
            about_content = about_match.group(1) if about_match else ""
        
        return render_template('edit_content.html',
                             content_type='Home About Section',
                             content=about_content,
                             file_type='home')
    
    @bp.route('/edit-about-page', methods=['GET', 'POST'])
    @login_required
    def edit_about_page():
        gh = get_github_manager()
        
        if request.method == 'POST':
            title = request.form.get('title', 'About Our Blog')
            description = request.form.get('description', '')
            new_content = request.form.get('page_content', '')
            sha = request.form.get('sha', '')
            
            if not sha:
                flash('Missing file information', 'error')
                return redirect(url_for('pages.edit_about_page'))
            
            front_matter = {
                'layout': 'page',
                'title': title,
                'description': description,
                'background': request.form.get('background', '/img/bg-about.jpg')
            }
            
            full_content = gh.create_front_matter(front_matter, new_content)
            
            commit_msg = f"Update about page - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            if gh.update_file('about.html', full_content, commit_msg, sha):
                flash('About page updated successfully!', 'success')
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('Error updating about page', 'error')
        
        page_file = gh.get_file_content('about.html')
        
        if not page_file:
            flash('About page not found', 'error')
            return redirect(url_for('dashboard.dashboard'))
        
        front_matter, body = gh.parse_front_matter(page_file['content'])
        
        return render_template('edit_about_page.html',
                             front_matter=front_matter,
                             body=body,
                             sha=page_file['sha'])
    
    @bp.route('/page/<path:page_path>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_page(page_path):
        gh = get_github_manager()
        
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            content = request.form.get('content')
            sha = request.form.get('sha')
            
            front_matter = {
                'layout': 'page',
                'title': title,
                'description': description,
                'background': request.form.get('background', '/img/bg-about.jpg')
            }
            
            full_content = gh.create_front_matter(front_matter, content)
            
            commit_msg = f"Update page: {title} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            if gh.update_file(page_path, full_content, commit_msg, sha):
                flash('Page updated successfully!', 'success')
                return redirect(url_for('pages.list_pages'))
            else:
                flash('Error updating page', 'error')
        
        page_file = gh.get_file_content(page_path)
        
        if not page_file:
            flash('Page not found', 'error')
            return redirect(url_for('pages.list_pages'))
        
        front_matter, body = gh.parse_front_matter(page_file['content'])
        
        return render_template('edit_page.html',
                             page_path=page_path,
                             front_matter=front_matter,
                             body=body,
                             sha=page_file['sha'])
```

---

### 12. flask_app/core/pages/bp.py

```python
"""
Pages blueprint
"""
from flask import Blueprint
from flask_app.core.pages.routes import setup_pages_routes

pages_bp = Blueprint('pages', __name__, url_prefix='')
setup_pages_routes(pages_bp)
```

---

### 13. flask_app/core/config_management/routes.py

```python
"""
Configuration management routes
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import yaml
import json
from flask_app.services.github_manager import get_github_manager
from flask_app.services.ai_settings_manager import AISettingsManager
from flask_app.services.v4_config_manager import V4ConfigManager

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
```

---

### 14. flask_app/core/config_management/bp.py

```python
"""
Configuration management blueprint
"""
from flask import Blueprint
from flask_app.core.config_management.routes import setup_config_routes

config_management_bp = Blueprint('config_management', __name__, url_prefix='')
setup_config_routes(config_management_bp)
```

---

### 15. flask_app/core/api/routes.py

```python
"""
API endpoints
"""
from flask import jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json
from flask_app.services.github_manager import get_github_manager
from flask_app.services.ai_settings_manager import AISettingsManager

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

```

---

### 16. flask_app/core/api/bp.py

```python
"""
API blueprint
"""
from flask import Blueprint
from flask_app.core.api.routes import setup_api_routes

api_bp = Blueprint('api', __name__, url_prefix='')
setup_api_routes(api_bp)
```

---

### 17. flask_app/core/__init__.py

```python
"""
Core module initialization
"""
```

---

### 18. flask_app/services/github_manager.py

```python
"""
GitHub repository operations management
"""
import os
import base64
import re
import yaml
from github import Github, GithubException
from flask_app.config import Config

def get_github_manager():
    """Factory function to get GitHub manager instance"""
    return GitHubRepoManager(Config.GITHUB_TOKEN, Config.REPO_NAME, Config.BRANCH)

class GitHubRepoManager:
    """Manages file operations on GitHub repository"""
    
    def __init__(self, token, repo_name, branch='main'):
        self.g = Github(token)
        self.repo = self.g.get_repo(repo_name)
        self.branch = branch
    
    def get_file_content(self, file_path):
        """Get file content from GitHub"""
        try:
            file_content = self.repo.get_contents(file_path, ref=self.branch)
            content = base64.b64decode(file_content.content).decode('utf-8')
            return {
                'content': content,
                'sha': file_content.sha,
                'path': file_path
            }
        except GithubException as e:
            print(f"Error getting file {file_path}: {e}")
            return None
    
    def update_file(self, file_path, content, commit_message, sha=None):
        """Update file in GitHub repo"""
        try:
            if sha:
                self.repo.update_file(
                    file_path,
                    commit_message,
                    content,
                    sha,
                    branch=self.branch
                )
            else:
                self.repo.create_file(
                    file_path,
                    commit_message,
                    content,
                    branch=self.branch
                )
            return True
        except GithubException as e:
            print(f"Error updating file {file_path}: {e}")
            return False
    
    def delete_file(self, file_path, commit_message):
        """Delete file from GitHub repo"""
        try:
            file_content = self.repo.get_contents(file_path, ref=self.branch)
            self.repo.delete_file(
                file_path,
                commit_message,
                file_content.sha,
                branch=self.branch
            )
            return True
        except GithubException as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    
    def list_posts(self):
        """List all blog posts"""
        try:
            contents = self.repo.get_contents("_posts", ref=self.branch)
            posts = []
            for content in contents:
                if content.name.endswith(('.html', '.md', '.markdown')):
                    posts.append({
                        'name': content.name,
                        'path': content.path,
                        'sha': content.sha,
                        'size': content.size
                    })
            return sorted(posts, key=lambda x: x['name'], reverse=True)
        except GithubException as e:
            print(f"Error listing posts: {e}")
            return []
    
    def list_pages(self):
        """List all pages (non-post HTML files in root)"""
        try:
            contents = self.repo.get_contents("", ref=self.branch)
            pages = []
            for content in contents:
                if content.name.endswith('.html') and content.name not in ['index.html']:
                    pages.append({
                        'name': content.name,
                        'path': content.path,
                        'sha': content.sha
                    })
            return pages
        except GithubException as e:
            print(f"Error listing pages: {e}")
            return []
    
    def get_config_yml(self):
        """Get _config.yml content"""
        return self.get_file_content('_config.yml')
    
    def update_config_yml(self, config_dict, commit_message="Update blog configuration"):
        """Update _config.yml"""
        config_file = self.get_config_yml()
        if not config_file:
            return False
        
        yaml_content = yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
        return self.update_file('_config.yml', yaml_content, commit_message, config_file['sha'])
    
    def parse_front_matter(self, content):
        """Parse Jekyll front matter from content"""
        if not content.startswith('---'):
            return None, content
        
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None, content
        
        try:
            front_matter = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return front_matter, body
        except yaml.YAMLError:
            return None, content
    
    def create_front_matter(self, front_matter_dict, body):
        """Create Jekyll file with front matter"""
        fm = '---\n'
        fm += yaml.dump(front_matter_dict, default_flow_style=False, allow_unicode=True)
        fm += '---\n\n'
        return fm + body
    
    def extract_content_section(self, content, section_id):
        """Extract a specific content section by ID"""
        pattern = rf'<!-- {section_id} -->(.*?)<!-- /{section_id} -->'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    def update_content_section(self, content, section_id, new_section_content):
        """Update a specific content section"""
        pattern = rf'(<!-- {section_id} -->)(.*?)(<!-- /{section_id} -->)'
        replacement = rf'\1\n{new_section_content}\n\3'
        updated = re.sub(pattern, replacement, content, flags=re.DOTALL)
        return updated
    
    def trigger_workflow(self, workflow_name='mainBlog.yml'):
        """Trigger GitHub Actions workflow"""
        try:
            workflow = self.repo.get_workflow(workflow_name)
            workflow.create_dispatch(ref=self.branch)
            return True
        except GithubException as e:
            print(f"Error triggering workflow: {e}")
            return False
```

---

### 19. flask_app/services/ai_settings_manager.py

```python
"""
AI settings management for article generation
"""
import os
import json
from datetime import datetime
from flask_app.config import Config

class AISettingsManager:
    """Manages AI article generation settings stored in GitHub repo"""
    
    def __init__(self, config_file=None):
        self.config_file = config_file or Config.AI_CONFIG_FILE
        self.github_path = os.path.join('flask_app', 'research_v3', '.ai_settings.json')
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
```

---

### 20. flask_app/services/v4_config_manager.py

```python
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
```

---

### 21. flask_app/services/__init__.py

```python
"""
Services module initialization
"""
```

---

### 22. flask_app/utils/__init__.py

```python
"""
Utilities module initialization
"""
```

---

### 23. flask_app/utils/decorators.py

```python
"""
Custom decorators for Flask application
"""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.username != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
```

---

### 24. flask_app/app.py (Main Entry Point)

```python
"""
Main Flask application entry point
"""
import os
from flask_app import create_app

if __name__ == '__main__':
    config_name = os.getenv('FLASK_ENV', 'development')
    app = create_app(config_name)
    
    # Validate required environment variables
    if not os.getenv('GITHUB_TOKEN') or not os.getenv('REPO_NAME'):
        print("ERROR: Set GITHUB_TOKEN and REPO_NAME in .env file")
        exit(1)
    
    print(f"Starting Flask Dashboard")
    print(f"Environment: {config_name}")
    print(f"Repository: {os.getenv('REPO_NAME')}")
    print(f"Branch: {os.getenv('BRANCH', 'master')}")
    
    debug = config_name == 'development'
    app.run(debug=debug, host='0.0.0.0', port=5001)
```

---

### 25. .env.example

```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here-change-in-production

# GitHub Configuration
GITHUB_TOKEN=ghp_your_github_token_here
REPO_NAME=username/blog-repo
BRANCH=master

# Admin Configuration
ADMIN_PASSWORD=changeme

# AI Settings
AI_CONFIG_FILE=research_v3/.ai_settings.json
```

---

## Migration Steps

1. **Create new directory structure**
   ```bash
   mkdir -p flask_app/core/{auth,dashboard,posts,pages,config_management,api}
   mkdir -p flask_app/services
   mkdir -p flask_app/utils
   ```

2. **Create all `__init__.py` files** (empty initialization files)

3. **Copy template files** from old `templates/` directory

4. **Move config to new location**
   - Create `flask_app/config.py` with configuration classes

5. **Split services** into their respective modules

6. **Create blueprints** for each feature module

7. **Update imports** in all route files to use new service locations

8. **Create `.env` file** from `.env.example`

9. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

10. **Run application**
    ```bash
    python flask_app/app.py
    ```

---

## Key Benefits of This Structure

✅ **Modular Design** - Each feature is self-contained in its own module
✅ **Scalability** - Easy to add new modules without affecting existing code
✅ **Testability** - Each service can be unit tested independently
✅ **Maintainability** - Clear separation of concerns
✅ **Reusability** - Services can be imported and used in multiple places
✅ **Configuration Management** - Centralized config with environment support
✅ **Blueprint Organization** - Clean routing structure using Flask blueprints

---

## Testing the Refactored App

Create `test_app.py`:

```python
"""
Simple tests for the refactored application
"""
import pytest
from flask_app import create_app

@pytest.fixture
def app():
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200

def test_index_redirect(client):
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302

def test_protected_dashboard(client):
    response = client.get('/dashboard')
    assert response.status_code == 302  # Should redirect to login
```

Run tests:
```bash
pip install pytest
pytest test_app.py
```
```

 jsonify({'status': 'error', 'message': str(e)}), 500
    
    @bp.route('/api/workflow-status')
    @login_required
    def workflow_status():
        gh = get_github_manager()
        try:
            workflows = gh.repo.get_workflow_runs()
            if workflows.totalCount > 0:
                latest = workflows[0]
                return jsonify({
                    'status': latest.status,
                    'conclusion': latest.conclusion,
                    'created_at': latest.created_at.isoformat(),
                    'html_url': latest.html_url
                })
            return jsonify({'status': 'no_runs'})
        except Exception as e:
            return