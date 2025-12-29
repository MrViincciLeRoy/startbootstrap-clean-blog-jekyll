"""
Configuration management blueprint
"""
from flask import Blueprint
from FlaskApp.core.config_management.routes import setup_theme_routes

config_management_bp = Blueprint('config_management', __name__, url_prefix='')
setup_theme_routes(config_management_bp)
