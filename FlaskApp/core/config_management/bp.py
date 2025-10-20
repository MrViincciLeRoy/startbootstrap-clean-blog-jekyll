"""
Configuration management blueprint
"""
from flask import Blueprint
from flask_app.core.config_management.routes import setup_config_routes

config_management_bp = Blueprint('config_management', __name__, url_prefix='')
setup_config_routes(config_management_bp)