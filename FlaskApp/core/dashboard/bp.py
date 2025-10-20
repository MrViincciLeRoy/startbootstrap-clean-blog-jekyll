"""
Dashboard blueprint
"""
from flask import Blueprint
from FlaskApp.core.dashboard.routes import setup_dashboard_routes

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='')
setup_dashboard_routes(dashboard_bp)