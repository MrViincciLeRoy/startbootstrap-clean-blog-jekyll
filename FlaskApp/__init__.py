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
    
    from FlaskApp.config import config_by_name
    
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions
    login_manager.init_app(app)
    
    # Register blueprints
    from FlaskApp.core.auth.bp import auth_bp
    from FlaskApp.core.dashboard.bp import dashboard_bp
    from FlaskApp.core.posts.bp import posts_bp
    from FlaskApp.core.pages.bp import pages_bp
    from FlaskApp.core.config_management.bp import config_management_bp
    from FlaskApp.core.api.bp import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(config_management_bp)
    app.register_blueprint(api_bp)
    
    # Load user loader
    from FlaskApp.core.auth.models import load_user
    
    return app