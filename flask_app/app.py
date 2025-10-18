"""
Flask Dashboard for GitHub-Synced Jekyll Blog
Edits files directly in GitHub repo, allows article generation to run via GH Actions
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import yaml
import base64
import json
import re
from pathlib import Path
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-secret-key')

# GitHub Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = os.getenv('REPO_NAME')  # e.g., "username/blog-repo"
BRANCH = os.getenv('BRANCH', 'master')

# AI Settings Configuration

AI_CONFIG_FILE = os.getenv('AI_CONFIG_FILE', 'research_v3/.ai_settings.json')

# Simple user storage (use database in production)
USERS = {
    'admin': generate_password_hash(os.getenv('ADMIN_PASSWORD', 'changeme'))
}

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============================================================================
# USER MODEL
# ============================================================================

class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username

@login_manager.user_loader
def load_user(username):
    if username in USERS:
        return User(username)
    return None



# ============================================================================
# GITHUB INTEGRATION
# ============================================================================

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
                # Update existing file
                self.repo.update_file(
                    file_path,
                    commit_message,
                    content,
                    sha,
                    branch=self.branch
                )
            else:
                # Create new file
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
        """Extract a specific content section by ID (e.g., 'about', 'intro')"""
        # Pattern to match <!-- Section Name --> content <!-- /Section Name -->
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

# Initialize GitHub manager
def get_github_manager():
    return GitHubRepoManager(GITHUB_TOKEN, REPO_NAME, BRANCH)

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and check_password_hash(USERS[username], password):
            user = User(username)
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ============================================================================
# DASHBOARD ROUTES
# ============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    gh = get_github_manager()
    posts = gh.list_posts()
    pages = gh.list_pages()
    
    return render_template('dashboard.html', 
                         posts=posts[:10],  # Show last 10 posts
                         pages=pages,
                         total_posts=len(posts))

# ============================================================================
# ============================================================================
# AI SETTINGS MANAGEMENT
# ============================================================================

class AISettingsManager:
    """Manages AI article generation settings"""
    
    def __init__(self, config_file=AI_CONFIG_FILE):
        self.config_file = config_file
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
    
    def load_settings(self):
        """Load AI settings from file or return defaults"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return {**self.defaults, **settings}
            except Exception as e:
                print(f"Error loading AI settings: {e}")
                return self.defaults.copy()
        return self.defaults.copy()
    
    def save_settings(self, settings):
        """Save AI settings to file with proper validation and error handling"""
        try:
            # Ensure config directory exists
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
                print(f"Created directory: {config_dir}")
            
            # Validate all settings are present
            validated_settings = {}
            for key in self.defaults:
                if key in settings:
                    validated_settings[key] = settings[key]
                else:
                    # Use existing value or default if missing
                    existing = self.load_settings()
                    validated_settings[key] = existing.get(key, self.defaults[key])
            
            # Write to file
            with open(self.config_file, 'w') as f:
                json.dump(validated_settings, f, indent=2)
            
            print(f"✓ Settings saved successfully to {self.config_file}")
            print(f"  Content: {validated_settings}")
            
            # Verify the file was written
            if os.path.exists(self.config_file):
                file_size = os.path.getsize(self.config_file)
                print(f"  File size: {file_size} bytes")
                return True
            else:
                print(f"✗ File not found after save: {self.config_file}")
                return False
                
        except PermissionError as e:
            print(f"✗ Permission denied writing to {self.config_file}: {e}")
            return False
        except IOError as e:
            print(f"✗ IO Error saving AI settings: {e}")
            return False
        except Exception as e:
            print(f"✗ Unexpected error saving AI settings: {e}")
            return False
    
    def get_setting(self, key, default=None):
        """Get a specific setting"""
        settings = self.load_settings()
        return settings.get(key, default or self.defaults.get(key))
    
    def update_setting(self, key, value):
        """Update a single setting"""
        settings = self.load_settings()
        settings[key] = value
        return self.save_settings(settings)


# Initialize settings manager
ai_settings = AISettingsManager()


# ============================================================================
# AI SETTINGS ROUTES (UPDATED)
# ============================================================================

@app.route('/ai-settings', methods=['GET', 'POST'])
@login_required
def edit_ai_settings():
    """Edit AI article generation settings"""
    
    if request.method == 'POST':
        try:
            # Collect settings from form - checkboxes use 'in' operator
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
            
            print(f"Form data received: {settings}")
            
            # Validate settings
            valid_devices = ['cpu', 'cuda', 'mps']
            if settings['device'] not in valid_devices:
                flash('Invalid device selected', 'error')
                return redirect(url_for('edit_ai_settings'))
            
            if not 1 <= settings['max_articles_per_run'] <= 10:
                flash('Max articles per run must be between 1 and 10', 'error')
                return redirect(url_for('edit_ai_settings'))
            
            # Save settings
            if ai_settings.save_settings(settings):
                flash('✓ AI settings updated successfully!', 'success')
                return redirect(url_for('edit_ai_settings'))
            else:
                flash('✗ Error saving AI settings to file', 'error')
                return redirect(url_for('edit_ai_settings'))
                
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
            return redirect(url_for('edit_ai_settings'))
        except Exception as e:
            print(f"Unexpected error in edit_ai_settings: {e}")
            flash(f'Unexpected error: {str(e)}', 'error')
            return redirect(url_for('edit_ai_settings'))
    
    # GET request - load current settings
    current_settings = ai_settings.load_settings()
    print(f"Loading settings for display: {current_settings}")
    
    return render_template('edit_ai_settings.html', config=current_settings)


@app.route('/api/ai-settings')
@login_required
def get_ai_settings_api():
    """API endpoint to get current AI settings"""
    settings = ai_settings.load_settings()
    return jsonify({
        'status': 'success',
        'settings': settings
    })


@app.route('/api/ai-settings/<key>')
@login_required
def get_ai_setting_api(key):
    """API endpoint to get a specific AI setting"""
    valid_keys = [
        'include_front_matter', 'fetch_images', 'embedding_model',
        'llm_model', 'config_path', 'database_path', 'device',
        'load_in_8bit', 'max_articles_per_run'
    ]
    
    if key not in valid_keys:
        return jsonify({'status': 'error', 'message': 'Invalid setting key'}), 400
    
    value = ai_settings.get_setting(key)
    return jsonify({
        'status': 'success',
        'key': key,
        'value': value
    })

# ============================================================================
# CONFIGURATION ROUTES
# ============================================================================

@app.route('/config', methods=['GET', 'POST'])
@login_required
def edit_config():
    gh = get_github_manager()
    
    if request.method == 'POST':
        # Get author field - if empty, use spaces for auto-generated
        author_input = request.form.get('author', '').strip()
        author_value = author_input if author_input else ' ' * 13 + 'HAA[B]'
        
        # Build config dictionary from form
        config_dict = {
            'title': request.form.get('title'),
            'email': request.form.get('email'),
            'description': request.form.get('description'),
            'baseurl': request.form.get('baseurl'),
            'url': request.form.get('url'),
            'author': author_value,
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
        
        # Remove empty values
        config_dict = {k: v for k, v in config_dict.items() if v}
        
        if gh.update_config_yml(config_dict, f"Update config - {datetime.now().strftime('%Y-%m-%d %H:%M')}"):
            flash('Configuration updated successfully!', 'success')
            return redirect(url_for('edit_config'))
        else:
            flash('Error updating configuration', 'error')
    
    # Get current config
    config_file = gh.get_config_yml()
    if config_file:
        config = yaml.safe_load(config_file['content'])
    else:
        config = {}
    
    return render_template('edit_config.html', config=config)

# ============================================================================
# CONTENT EDITING ROUTES
# ============================================================================

@app.route('/edit-home-about', methods=['GET', 'POST'])
@login_required
def edit_home_about():
    """Edit the About section on the homepage"""
    gh = get_github_manager()
    
    if request.method == 'POST':
        new_content = request.form.get('about_content', '')
        
        file_data = gh.get_file_content('_layouts/home.html')
        if not file_data:
            flash('Could not load home layout', 'error')
            return redirect(url_for('dashboard'))
        
        # Update the about section
        updated_content = gh.update_content_section(
            file_data['content'],
            'about-section',
            new_content
        )
        
        commit_msg = f"Update home about section - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if gh.update_file('_layouts/home.html', updated_content, commit_msg, file_data['sha']):
            flash('Homepage about section updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Error updating homepage', 'error')
    
    # GET request - load current content
    file_data = gh.get_file_content('_layouts/home.html')
    if not file_data:
        flash('Could not load home layout', 'error')
        return redirect(url_for('dashboard'))
    
    about_content = gh.extract_content_section(file_data['content'], 'about-section')
    if not about_content:
        # If section doesn't exist with markers, extract the About section manually
        about_match = re.search(r'<h1><u>About</u></h1>\s*<p>(.*?)</p>', file_data['content'], re.DOTALL)
        about_content = about_match.group(1) if about_match else ""
    
    return render_template('edit_content.html',
                         content_type='Home About Section',
                         content=about_content,
                         file_type='home')


@app.route('/edit-about-page', methods=['GET', 'POST'])
@login_required
def edit_about_page():
    """Edit the About page content"""
    gh = get_github_manager()
    
    if request.method == 'POST':
        title = request.form.get('title', 'About Our Blog')
        description = request.form.get('description', '')
        new_content = request.form.get('page_content', '')
        sha = request.form.get('sha', '')
        
        if not sha:
            flash('Missing file information', 'error')
            return redirect(url_for('edit_about_page'))
        
        # Build front matter
        front_matter = {
            'layout': 'page',
            'title': title,
            'description': description,
            'background': request.form.get('background', '/img/bg-about.jpg')
        }
        
        # Create full content
        full_content = gh.create_front_matter(front_matter, new_content)
        
        # Update file
        commit_msg = f"Update about page - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if gh.update_file('about.html', full_content, commit_msg, sha):
            flash('About page updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Error updating about page', 'error')
    
    # GET request - load page for editing
    page_file = gh.get_file_content('about.html')
    
    if not page_file:
        flash('About page not found', 'error')
        return redirect(url_for('dashboard'))
    
    front_matter, body = gh.parse_front_matter(page_file['content'])
    
    return render_template('edit_about_page.html',
                         front_matter=front_matter,
                         body=body,
                         sha=page_file['sha'])

# ============================================================================
# POST ROUTES
# ============================================================================

@app.route('/posts')
@login_required
def list_posts():
    gh = get_github_manager()
    posts = gh.list_posts()
    return render_template('list_posts.html', posts=posts)

@app.route('/post/<path:post_path>')
@login_required
def view_post(post_path):
    gh = get_github_manager()
    post_file = gh.get_file_content(post_path)
    
    if not post_file:
        flash('Post not found', 'error')
        return redirect(url_for('list_posts'))
    
    front_matter, body = gh.parse_front_matter(post_file['content'])
    
    return render_template('view_post.html', 
                         post_path=post_path,
                         front_matter=front_matter,
                         body=body,
                         sha=post_file['sha'])


@app.route('/post/<path:post_path>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_path):
    """Edit a blog post"""
    gh = get_github_manager()
    post_file = gh.get_file_content(post_path)
    
    if not post_file:
        flash('Post not found', 'error')
        return redirect(url_for('list_posts'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        content = request.form.get('content')
        sha = request.form.get('sha')
        
        # VALIDATION - Check if we have required fields
        if not title or not content or not sha:
            flash('Missing required fields (title, content, or sha)', 'error')
            return redirect(url_for('edit_post', post_path=post_path))
        
        # Build front matter
        front_matter = {
            'layout': 'post',
            'title': title,
            'date': request.form.get('date', datetime.now().strftime('%Y-%m-%d')),
        }
        
        # Add optional fields if provided
        if description:
            front_matter['description'] = description
        
        if request.form.get('categories'):
            front_matter['categories'] = request.form.get('categories')
        
        # Create full content
        full_content = gh.create_front_matter(front_matter, content)
        
        # Update file
        commit_msg = f"Update post: {title} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if gh.update_file(post_path, full_content, commit_msg, sha):
            flash('Post updated successfully!', 'success')
            return redirect(url_for('list_posts'))
        else:
            flash('Error updating post', 'error')
            return redirect(url_for('edit_post', post_path=post_path))
    
    # GET request - load post for editing
    front_matter, body = gh.parse_front_matter(post_file['content'])
    
    # IMPORTANT: Make sure front_matter is a dict, not None
    if front_matter is None:
        front_matter = {}
    
    return render_template('edit_post.html',
                         post_path=post_path,
                         front_matter=front_matter,
                         body=body,
                         sha=post_file['sha'])


@app.route('/post/<path:post_path>/delete', methods=['POST'])
@login_required
def delete_post(post_path):
    gh = get_github_manager()
    
    commit_msg = f"Delete post: {post_path} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    if gh.delete_file(post_path, commit_msg):
        flash('Post deleted successfully!', 'success')
    else:
        flash('Error deleting post', 'error')
    
    return redirect(url_for('list_posts'))

# ============================================================================
# PAGE ROUTES
# ============================================================================

@app.route('/pages')
@login_required
def list_pages():
    gh = get_github_manager()
    pages = gh.list_pages()
    return render_template('list_pages.html', pages=pages)

@app.route('/page/<path:page_path>/edit', methods=['GET', 'POST'])
@login_required
def edit_page(page_path):
    gh = get_github_manager()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        content = request.form.get('content')
        sha = request.form.get('sha')
        
        # Build front matter
        front_matter = {
            'layout': 'page',
            'title': title,
            'description': description,
            'background': request.form.get('background', '/img/bg-about.jpg')
        }
        
        # Create full content
        full_content = gh.create_front_matter(front_matter, content)
        
        # Update file
        commit_msg = f"Update page: {title} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if gh.update_file(page_path, full_content, commit_msg, sha):
            flash('Page updated successfully!', 'success')
            return redirect(url_for('list_pages'))
        else:
            flash('Error updating page', 'error')
    
    # GET request - load page for editing
    page_file = gh.get_file_content(page_path)
    
    if not page_file:
        flash('Page not found', 'error')
        return redirect(url_for('list_pages'))
    
    front_matter, body = gh.parse_front_matter(page_file['content'])
    
    return render_template('edit_page.html',
                         page_path=page_path,
                         front_matter=front_matter,
                         body=body,
                         sha=page_file['sha'])

# ============================================================================
# WORKFLOW TRIGGER ROUTES
# ============================================================================

@app.route('/trigger-generation', methods=['POST'])
@login_required
def trigger_generation():
    """Trigger GitHub Actions workflow with AI settings"""
    gh = get_github_manager()
    
    # Get current AI settings
    settings = ai_settings.load_settings()
    
    # Create a workflow config file that GitHub Actions can read
    try:
        workflow_config = {
            'timestamp': datetime.now().isoformat(),
            'triggered_by': current_user.username,
            'ai_settings': settings
        }
        
        # Save config locally for GH Actions to read
        config_path = 'workflow_config.json'
        with open(config_path, 'w') as f:
            json.dump(workflow_config, f, indent=2)
        
        if gh.trigger_workflow('mainBlog.yml'):
            device_info = settings.get('device', 'cpu')
            model_info = settings.get('llm_model', 'LiquidAI/LFM2-1.2B-RAG')
            flash(
                f'Article generation workflow triggered! '
                f'(Device: {device_info}, Model: {model_info})',
                'success'
            )
        else:
            flash('Error triggering workflow. Check GitHub Actions settings.', 'error')
    except Exception as e:
        print(f"Error in trigger_generation: {e}")
        flash(f'Error triggering workflow: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/sync-check')
@login_required
def sync_check():
    """Check if repo is in sync"""
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

@app.route('/api/workflow-status')
@login_required
def workflow_status():
    """Get status of latest workflow run"""
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
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# INITIALIZATION
# ============================================================================

if __name__ == '__main__':
    if not GITHUB_TOKEN or not REPO_NAME:
        print("ERROR: Set GITHUB_TOKEN and REPO_NAME in .env file")
        exit(1)
    
    print(f"Dashboard connected to: {REPO_NAME}")
    print(f"Branch: {BRANCH}")
    print(f"AI Settings file: {AI_CONFIG_FILE}")
    app.run(debug=True, host='0.0.0.0', port=5001)
