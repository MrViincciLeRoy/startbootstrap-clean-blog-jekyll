"""
User model and authentication
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from FlaskApp import login_manager
import os

# Simple user storage (use database in production)
USERS = {
    'admin': generate_password_hash(os.getenv('ADMIN_PASSWORD', 'changeme'))
}

class User(UserMixin):
    """User model"""
    def __init__(self, username):
        self.id = username
        self.username = username

@login_manager.user_loader
def load_user(username):
    """Load user from database"""
    if username in USERS:
        return User(username)
    return None

def verify_credentials(username, password):
    """Verify user credentials"""
    if username in USERS and check_password_hash(USERS[username], password):
        return True
    return False