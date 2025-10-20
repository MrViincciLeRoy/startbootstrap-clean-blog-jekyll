"""
Page management routes
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime
from FlaskApp.services.github_manager import get_github_manager

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