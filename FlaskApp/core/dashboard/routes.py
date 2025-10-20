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