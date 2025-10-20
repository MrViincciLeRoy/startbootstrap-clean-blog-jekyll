"""
Pages blueprint
"""
from flask import Blueprint
from flask_app.core.pages.routes import setup_pages_routes

pages_bp = Blueprint('pages', __name__, url_prefix='')
setup_pages_routes(pages_bp)