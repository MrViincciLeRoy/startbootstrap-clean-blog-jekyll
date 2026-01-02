"""
AI Chat routes for blog post Q&A
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from FlaskApp.services.github_manager import get_github_manager
from FlaskApp.services.ai_chat_service import AIChatService
import os

ai_chat_bp = Blueprint('ai_chat', __name__, url_prefix='')

# Initialize AI chat service (will be done on first use)
_chat_service = None

def get_chat_service():
    """Get or create AI chat service instance"""
    global _chat_service
    if _chat_service is None:
        # Get posts directory from GitHub manager
        gh = get_github_manager()
        posts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '_posts')
        
        # Initialize service
        groq_api_key = os.getenv('GROQ_API_KEY')
        _chat_service = AIChatService(posts_dir=posts_dir, groq_api_key=groq_api_key)
    
    return _chat_service

@ai_chat_bp.route('/ai-chat')
@login_required
def ai_chat_page():
    """AI chat interface page"""
    chat_service = get_chat_service()
    has_groq = chat_service.has_groq
    
    return render_template('ai_chat.html', has_groq=has_groq)

@ai_chat_bp.route('/api/ai-chat/index', methods=['POST'])
@login_required
def index_posts():
    """Index all blog posts for RAG"""
    try:
        chat_service = get_chat_service()
        result = chat_service.index_posts()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@ai_chat_bp.route('/api/ai-chat/search', methods=['POST'])
@login_required
def search_posts():
    """Search blog posts using vector similarity"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        n_results = data.get('n_results', 3)
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Query is required'
            }), 400
        
        chat_service = get_chat_service()
        result = chat_service.search_posts(query, n_results)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@ai_chat_bp.route('/api/ai-chat/ask', methods=['POST'])
@login_required
def ask_question():
    """Ask a question about blog posts"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        n_context = data.get('n_context', 3)
        model = data.get('model', 'llama-3.3-70b-versatile')
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Query is required'
            }), 400
        
        chat_service = get_chat_service()
        result = chat_service.ask_question(query, n_context, model)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@ai_chat_bp.route('/api/ai-chat/status', methods=['GET'])
@login_required
def get_status():
    """Get AI chat service status"""
    try:
        chat_service = get_chat_service()
        
        has_collection = chat_service.load_collection()
        
        status = {
            'has_groq': chat_service.has_groq,
            'has_collection': has_collection,
            'embedding_model': 'BAAI/bge-small-en-v1.5'
        }
        
        if has_collection:
            try:
                count = chat_service.collection.count()
                status['indexed_chunks'] = count
            except:
                status['indexed_chunks'] = 0
        
        return jsonify({
            'status': 'success',
            'data': status
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
