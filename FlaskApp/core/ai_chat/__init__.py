"""
Flask application factory
"""
from flask import Flask
from flask_login import LoginManager
import os

# Initialize Flask-Login
login_manager = LoginManager()

def create_app(config_name='development'):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    from FlaskApp.config import config_by_name
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    from FlaskApp.core.auth.bp import auth_bp
    from FlaskApp.core.dashboard.bp import dashboard_bp
    from FlaskApp.core.posts.bp import posts_bp
    from FlaskApp.core.pages.bp import pages_bp
    from FlaskApp.core.config_management.bp import config_management_bp
    from FlaskApp.core.api.bp import api_bp
    from FlaskApp.core.ai_chat.bp import ai_chat_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(config_management_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(ai_chat_bp)
    
    return app
