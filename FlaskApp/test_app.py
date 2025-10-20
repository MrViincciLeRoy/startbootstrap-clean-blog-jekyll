"""
Simple tests for the refactored application
"""
import pytest
from FlaskApp import create_app

@pytest.fixture
def app():
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200

def test_index_redirect(client):
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302

def test_protected_dashboard(client):
    response = client.get('/dashboard')
    assert response.status_code == 302  # Should redirect to login
