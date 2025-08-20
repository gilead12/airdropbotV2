#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask application wrapper for AirdropBot V2
This creates a Flask web application that can handle Telegram webhooks
and be served by Gunicorn in production.
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Dispatcher
import settings
from bot import setup_handlers
from bot_fixed import force_clear_updates
from telegram.ext import Updater
import threading
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Global variables for bot components
bot = None
dispatcher = None
updater = None

def initialize_bot():
    """Initialize the Telegram bot and dispatcher."""
    global bot, dispatcher, updater
    
    try:
        logger.info("Initializing Telegram bot...")
        
        # Force clear any pending updates
        force_clear_updates()
        time.sleep(2)
        
        # Create updater and get bot and dispatcher
        updater = Updater(
            settings.TELEGRAM_TOKEN,
            request_kwargs={
                'connect_timeout': 60.0,
                'read_timeout': 60.0,
            },
            use_context=True
        )
        
        bot = updater.bot
        dispatcher = updater.dispatcher
        
        # Setup handlers
        setup_handlers(dispatcher)
        
        logger.info("Bot initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        return False

def set_webhook():
    """Set the webhook URL for the bot."""
    try:
        webhook_url = os.environ.get('WEBHOOK_URL')
        if webhook_url:
            result = bot.set_webhook(url=f"{webhook_url}/webhook")
            if result:
                logger.info(f"Webhook set successfully to {webhook_url}/webhook")
            else:
                logger.error("Failed to set webhook")
        else:
            logger.warning("WEBHOOK_URL not set in environment variables")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

@app.route('/')
def index():
    """Health check endpoint."""
    return jsonify({
        'status': 'running',
        'service': 'AirdropBot V2',
        'version': '2.0.0'
    })

@app.route('/health')
def health_check():
    """Detailed health check endpoint."""
    bot_status = 'initialized' if bot else 'not_initialized'
    
    return jsonify({
        'status': 'healthy',
        'service': 'AirdropBot V2',
        'bot_status': bot_status,
        'timestamp': time.time()
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram webhooks."""
    try:
        if not bot or not dispatcher:
            logger.error("Bot not initialized")
            return jsonify({'error': 'Bot not initialized'}), 500
        
        # Get the JSON data from the request
        json_data = request.get_json()
        
        if not json_data:
            logger.warning("Received empty webhook data")
            return jsonify({'error': 'No data received'}), 400
        
        # Create Update object from JSON
        update = Update.de_json(json_data, bot)
        
        if update:
            # Process the update
            dispatcher.process_update(update)
            logger.info(f"Processed update: {update.update_id}")
            return jsonify({'status': 'ok'})
        else:
            logger.warning("Failed to create Update object from JSON")
            return jsonify({'error': 'Invalid update data'}), 400
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/set_webhook', methods=['POST'])
def set_webhook_endpoint():
    """Endpoint to set the webhook URL."""
    try:
        data = request.get_json()
        webhook_url = data.get('url') if data else None
        
        if not webhook_url:
            return jsonify({'error': 'URL is required'}), 400
        
        if bot:
            result = bot.set_webhook(url=webhook_url)
            if result:
                return jsonify({'status': 'success', 'message': 'Webhook set successfully'})
            else:
                return jsonify({'error': 'Failed to set webhook'}), 500
        else:
            return jsonify({'error': 'Bot not initialized'}), 500
            
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook_info')
def webhook_info():
    """Get current webhook information."""
    try:
        if bot:
            webhook_info = bot.get_webhook_info()
            return jsonify({
                'url': webhook_info.url,
                'has_custom_certificate': webhook_info.has_custom_certificate,
                'pending_update_count': webhook_info.pending_update_count,
                'last_error_date': webhook_info.last_error_date,
                'last_error_message': webhook_info.last_error_message,
                'max_connections': webhook_info.max_connections,
                'allowed_updates': webhook_info.allowed_updates
            })
        else:
            return jsonify({'error': 'Bot not initialized'}), 500
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Initialize bot when the module is imported
if __name__ != '__main__':
    # This runs when imported by Gunicorn
    initialize_bot()
    
    # Set webhook if URL is provided
    webhook_url = os.environ.get('WEBHOOK_URL')
    if webhook_url and bot:
        threading.Thread(target=set_webhook, daemon=True).start()

if __name__ == '__main__':
    # Development mode - run with Flask dev server
    print("Starting AirdropBot V2 in development mode...")
    
    if initialize_bot():
        print("Bot initialized successfully")
        
        # In development, we can use polling instead of webhooks
        use_polling = os.environ.get('USE_POLLING', 'true').lower() == 'true'
        
        if use_polling:
            print("Starting polling mode for development...")
            # Start polling in a separate thread
            def start_polling():
                updater.start_polling(
                    poll_interval=1.0,
                    timeout=30,
                    clean=True,
                    bootstrap_retries=-1
                )
                updater.idle()
            
            polling_thread = threading.Thread(target=start_polling, daemon=True)
            polling_thread.start()
        
        # Start Flask app
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("Failed to initialize bot")
        exit(1)