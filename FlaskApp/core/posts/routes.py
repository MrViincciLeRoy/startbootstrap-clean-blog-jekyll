"""
Post management routes
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime
from FlaskApp.services.github_manager import get_github_manager

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