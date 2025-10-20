"""
API blueprint
"""
from flask import Blueprint
from FlaskApp.core.api.routes import setup_api_routes

api_bp = Blueprint('api', __name__, url_prefix='')
setup_api_routes(api_bp)