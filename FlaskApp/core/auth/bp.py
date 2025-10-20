"""
Authentication blueprint
"""
from flask import Blueprint
from FlaskApp.core.auth.routes import setup_auth_routes

auth_bp = Blueprint('auth', __name__, url_prefix='')
setup_auth_routes(auth_bp)