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