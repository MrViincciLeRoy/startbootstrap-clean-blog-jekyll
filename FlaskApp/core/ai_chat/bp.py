"""
AI Chat blueprint
"""
from flask import Blueprint
from FlaskApp.core.ai_chat.routes import ai_chat_bp

# Export the blueprint
__all__ = ['ai_chat_bp']
