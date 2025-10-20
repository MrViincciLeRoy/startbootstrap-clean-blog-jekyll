"""
Main Flask application entry point
"""
import os
from flask_app import create_app

if __name__ == '__main__':
    config_name = os.getenv('FLASK_ENV', 'development')
    app = create_app(config_name)
    
    # Validate required environment variables
    if not os.getenv('GITHUB_TOKEN') or not os.getenv('REPO_NAME'):
        print("ERROR: Set GITHUB_TOKEN and REPO_NAME in .env file")
        exit(1)
    
    print(f"Starting Flask Dashboard")
    print(f"Environment: {config_name}")
    print(f"Repository: {os.getenv('REPO_NAME')}")
    print(f"Branch: {os.getenv('BRANCH', 'master')}")
    
    debug = config_name == 'development'
    app.run(debug=debug, host='0.0.0.0', port=5001)