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
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-secret-key')

# GitHub Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = os.getenv('REPO_NAME')  # e.g., "username/blog-repo"
BRANCH = os.getenv('BRANCH', 'master')

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
# CONFIGURATION ROUTES
# ============================================================================

@app.route('/config', methods=['GET', 'POST'])
@login_required
def edit_config():
    gh = get_github_manager()
    
    if request.method == 'POST':
        # Build config dictionary from form
        config_dict = {
            'title': request.form.get('title'),
            'email': request.form.get('email'),
            'description': request.form.get('description'),
            'baseurl': request.form.get('baseurl'),
            'url': request.form.get('url'),
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
# FIXED VERSION OF THE PROBLEMATIC ROUTE

@app.route('/post/<path:page_path>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_path):
    gh = get_github_manager()
    page_path = gh.get_file_content(post_path)
    
    if not post_path:
        flash('Post not found', 'error')
        return redirect(url_for('list_posts'))
    
    #front_matter, body = gh.parse_front_matter(post_file['content'])
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        content = request.form.get('content')
        sha = request.form.get('sha')
        
        # VALIDATION - Check if we have required fields
        if not title or not content or not sha:
            flash('Missing required fields (title, content, or sha)', 'error')
            return redirect(url_for('edit_page', page_path=page_path))
        
        # Build front matter
        front_matter = {
            'layout': 'page',
            'title': title,
            'description': description,
            'background': request.form.get('background', '/img/bg-about.jpg')
        }
        
        # Remove empty description to keep front matter clean
        if not description:
            del front_matter['description']
        
        # Create full content
        full_content = gh.create_front_matter(front_matter, content)
        
        # Update file
        commit_msg = f"Update page: {title} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if gh.update_file(page_path, full_content, commit_msg, sha):
            flash('Page updated successfully!', 'success')
            return redirect(url_for('list_pages'))
        else:
            flash('Error updating page', 'error')
            return redirect(url_for('edit_page', page_path=page_path))
    
    # GET request - load page for editing
    #page_file = gh.get_file_content(page_path)
    
    if not page_file:
        flash('Page not found', 'error')
        return redirect(url_for('list_pages'))
    
    front_matter, body = gh.parse_front_matter(page_file['content'])
    
    # IMPORTANT: Make sure front_matter is a dict, not None
    if front_matter is None:
        front_matter = {}
    
    return render_template('edit_page.html',
                         page_path=page_path,
                         front_matter=front_matter,
                         body=body,
                         sha=page_file['sha'])


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
    """Trigger GitHub Actions workflow to generate new articles"""
    gh = get_github_manager()
    
    if gh.trigger_workflow('mainBlog.yml'):
        flash('Article generation workflow triggered! Check GitHub Actions for progress.', 'success')
    else:
        flash('Error triggering workflow. Check GitHub Actions settings.', 'error')
    
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
    app.run(debug=True, host='0.0.0.0', port=5001)
