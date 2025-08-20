#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Import the original bot code and modify the main function
from bot import *
import time
import requests

def force_clear_updates():
    """Aggressively clear any pending updates"""
    try:
        # Get current updates to find the highest offset
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/getUpdates"
        response = requests.get(url, params={'limit': 100, 'timeout': 1})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok') and data.get('result'):
                updates = data['result']
                if updates:
                    # Get the highest update_id and confirm it
                    highest_id = max(update['update_id'] for update in updates)
                    confirm_url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/getUpdates"
                    requests.get(confirm_url, params={'offset': highest_id + 1, 'limit': 1, 'timeout': 1})
                    print(f"Cleared {len(updates)} pending updates, highest ID: {highest_id}")
                else:
                    print("No pending updates found")
            else:
                print(f"API Error: {data}")
        else:
            print(f"HTTP Error: {response.status_code}")
    except Exception as e:
        print(f"Error clearing updates: {e}")

def main_fixed():
    """Enhanced main function with conflict resolution"""
    print("Starting bot with conflict resolution...")
    
    # Force clear any pending updates
    force_clear_updates()
    
    # Wait a moment
    time.sleep(3)
    
    # Create the Updater with enhanced settings
    updater = Updater(
        settings.TELEGRAM_TOKEN,
        request_kwargs={
            'connect_timeout': 60.0,
            'read_timeout': 60.0,
        },
        use_context=True
    )
    
    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    setup_handlers(dp)
    
    # Start polling with custom parameters
    print("Starting polling...")
    updater.start_polling(
        poll_interval=1.0,
        timeout=30,
        clean=True,
        bootstrap_retries=-1
    )
    
    print("Bot is running! Press Ctrl+C to stop.")
    updater.idle()

if __name__ == '__main__':
    main_fixed()