"""
Pages blueprint
"""
from flask import Blueprint
from FlaskApp.core.pages.routes import setup_pages_routes

pages_bp = Blueprint('pages', __name__, url_prefix='')
setup_pages_routes(pages_bp)
