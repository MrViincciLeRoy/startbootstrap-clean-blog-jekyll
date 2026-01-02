"""
AI Chat blueprint
"""
from flask import Blueprint
from FlaskApp.core.ai_chat.routes import setup_ai_chat_routes

ai_chat_bp = Blueprint('ai_chat', __name__, url_prefix='')
setup_ai_chat_routes(ai_chat_bp)

