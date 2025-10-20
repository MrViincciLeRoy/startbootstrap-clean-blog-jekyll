"""
Posts blueprint
"""
from flask import Blueprint
from FlaskApp.core.posts.routes import setup_posts_routes

posts_bp = Blueprint('posts', __name__, url_prefix='')
setup_posts_routes(posts_bp)