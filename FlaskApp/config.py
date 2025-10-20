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