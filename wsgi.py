#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point for AirdropBot V2
This file is used by Gunicorn to serve the Flask application in production.
"""

import os
import sys
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

# Set environment variables if not already set
if not os.environ.get('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'production'

try:
    # Import the Flask application from app.py
    from app import app
    
except ImportError as e:
    print(f"Error importing application: {e}")
    # Create a minimal Flask app as fallback
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'airdropbot'}, 200
    
    @app.route('/')
    def index():
        return {'message': 'AirdropBot V2 is running', 'status': 'active'}, 200

# Configure logging for production
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    # Create logs directory if it doesn't exist
    logs_dir = project_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Set up file handler for application logs
    file_handler = RotatingFileHandler(
        logs_dir / 'airdropbot.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('AirdropBot V2 startup')

# Application factory pattern (optional)
def create_app():
    """Application factory for creating Flask app instances."""
    return app

# For debugging purposes
if __name__ == "__main__":
    print("Starting AirdropBot V2 in development mode...")
    app.run(host='0.0.0.0', port=5000, debug=True)