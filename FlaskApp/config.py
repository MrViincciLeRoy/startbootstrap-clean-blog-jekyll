"""
Configuration settings for Flask application
"""
import os
from pathlib import Path

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    REPO_NAME = os.getenv('REPO_NAME')
    BRANCH = os.getenv('BRANCH', 'master')
    
    # AI Configuration
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    AI_CONFIG_FILE = os.path.join('FlaskApp', 'services', 'v4', 'config', 'ai_settings.json')
    
    # Posts directory
    BASE_DIR = Path(__file__).parent.parent
    POSTS_DIR = BASE_DIR / '_posts'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
