#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.

First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from telegram import ChatAction, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler, CallbackQueryHandler, JobQueue)

## custom library
from lib.models import userDBexists,add_userDB,user_details_summary,session,users_data
from random import randint
import os
import re
import settings
import requests
from functools import wraps
from dataclasses import dataclass
from time import sleep
import threading
import time

TELEGRAM_CHECK, TWITTER_SUBMIT, TWITTER_PENDING, WALLET_SUBMIT, COMPLETED = range(5)


def start(update, context):
    print(f"Start function called for user: {update.message.from_user.id}")
    
    context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
    
    # Initialize user data
    context.user_data['user_id'] = update.message.from_user.id
    context.user_data['user_name'] = update.message.from_user.username
    context.user_data['first_name'] = update.message.from_user.first_name
    
    # Extract referrer ID from start parameter
    referrer_id = None
    if update.message.text and len(update.message.text.split()) > 1:
        try:
            start_param = update.message.text.split()[1]
            referrer_id = int(start_param)
        except (ValueError, IndexError):
            referrer_id = None
    
    # Check if user already exists in database
    try:
        existing_user = userDBexists(update.message.from_user.id)
        if existing_user:
            # User exists, check their current status
            registration_step = existing_user.get('registration_step', 1)
            
            if registration_step == 4:  # Completed registration
                ref_link = f"https://t.me/greendale1_bot?start={context.user_data['user_id']}"
                status_info = f"✅ Telegram: Verified\n✅ X (Twitter): Verified\n✅ Wallet: {existing_user.get('wallet', 'Not set')[:10]}..."
                message = settings.ALREADY_REGISTERED_MESSAGE.format(
                    status_info=status_info,
                    ref_link=ref_link
                )
                update.message.reply_text(message)
                return COMPLETED
            else:
                # Continue from where they left off
                return handle_existing_user_flow(context.bot, update, context.user_data, existing_user)
    except Exception as e:
        print(f"User not found in database: {e}")
        # Create new user in database with referral tracking
        try:
            new_user = users_data(
                telegram_id=update.message.from_user.id,
                username=update.message.from_user.username,
                registration_step=1,
                telegram_verified=False,
                twitter_verification_status='pending',
                wallet_submitted=False,
                balance=0,
                verified=False,
                referral_count=0,
                referral_by=referrer_id
            )
            session.add(new_user)
            session.commit()
            print(f"New user created in database: {update.message.from_user.id}")
            
            # Update referrer's referral count if valid referrer
            if referrer_id and userDBexists(referrer_id):
                referrer_data = userDBexists(referrer_id)
                if referrer_data:
                    current_count = referrer_data.get('referral_count', 0)
                    update_user_step(
                        referrer_id,
                        referrer_data.get('registration_step', 1),
                        referral_count=current_count + 1
                    )
                    print(f"Updated referrer {referrer_id} referral count to {current_count + 1}")
        except Exception as create_error:
            print(f"Error creating new user: {create_error}")
            session.rollback()
    
    # New user - start the registration flow
    welcome_text = settings.WELCOME_MESSAGE.format(Username=update.message.from_user.first_name or "Friend")
    
    # Create inline keyboard with Start Registration button
    keyboard = [[InlineKeyboardButton("🚀 Start Registration", callback_data="start_registration")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    return TELEGRAM_CHECK

def handle_existing_user_flow(update, context, existing_user):
    """Handle flow for existing users based on their registration step"""
    step = existing_user.get('registration_step', 1)
    
    if step == 1:  # Telegram verification
        return check_telegram_membership(update, context)
    elif step == 2:  # Twitter submission
        twitter_status = existing_user.get('twitter_verification_status', 'pending')
        if twitter_status == 'pending':
            update.message.reply_text(settings.TWITTER_PENDING_MESSAGE.format(
                username=existing_user.get('twitter_id', 'Unknown')
            ))
            return TWITTER_PENDING
        elif twitter_status == 'rejected':
            keyboard = [[InlineKeyboardButton("Proceed to X Follow", callback_data="proceed_twitter")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(settings.TWITTER_FOLLOW_MESSAGE.format(
                twitter_link=settings.TWITTER_PAGE_LINK
            ), reply_markup=reply_markup)
            return TWITTER_SUBMIT
        else:  # approved
            keyboard = [[InlineKeyboardButton("Proceed to Submit Wallet", callback_data="proceed_wallet")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(settings.TWITTER_APPROVED_MESSAGE, reply_markup=reply_markup)
            return WALLET_SUBMIT
    elif step == 3:  # Wallet submission
        keyboard = [[InlineKeyboardButton("Proceed to Submit Wallet", callback_data="proceed_wallet")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(settings.WALLET_PROMPT_MESSAGE, reply_markup=reply_markup)
        return WALLET_SUBMIT
    
    return TELEGRAM_CHECK

def check_telegram_membership(update, context):
    """Check if user is member of required Telegram groups"""
    # Handle both Message and CallbackQuery objects
    if hasattr(update, 'callback_query') and update.callback_query:
        user_id = update.callback_query.from_user.id
        reply_method = update.callback_query.message.reply_text
    else:
        user_id = update.message.from_user.id
        reply_method = update.message.reply_text
    
    if check_user_exist_groups(user_id):
        # User is in groups, proceed to Twitter step
        keyboard = [[InlineKeyboardButton("Proceed to X Follow", callback_data="proceed_twitter")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_method(settings.TELEGRAM_VERIFIED_MESSAGE, reply_markup=reply_markup)
        
        # Update user's telegram verification status
        update_user_step(context.user_data['user_id'], 2, telegram_verified=True)
        return TWITTER_SUBMIT
    else:
        # User not in groups, start automatic checking
        reply_method(settings.ASK_TO_JOIN_GROUPS + "\n\n⏳ I'll automatically check your membership every 30 seconds...")
        
        # Start automatic membership checking
        start_auto_membership_check(update, context)
        return TELEGRAM_CHECK


## custom function
def update_user_step(telegram_id, step, **kwargs):
    """Update user's registration step and other fields"""
    try:
        user = session.query(users_data).filter(users_data.telegram_id == telegram_id).first()
        if not user:
            # Create new user
            user = users_data(
                telegram_id=telegram_id,
                registration_step=step,
                **kwargs
            )
            session.add(user)
        else:
            # Update existing user
            user.registration_step = step
            for key, value in kwargs.items():
                setattr(user, key, value)
        
        session.commit()
        return True
    except Exception as e:
        print(f"Error updating user step: {e}")
        session.rollback()
        return False

def check_user_exist_groups(user_telegram_int_id):
    try:
        for group in settings.GROUPS_LIST:
            url = f'https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/getChatMember?chat_id=@{group}&user_id={user_telegram_int_id}'
            response = requests.get(url)
            data = response.json()
            
            # Check if the API response is valid
            if not data.get('ok', False):
                print(f'Telegram API error for group {group}: {data.get("description", "Unknown error")}')
                return False
                
            # Check if result exists in response
            if 'result' not in data:
                print(f'No result in API response for group {group}')
                return False
                
            if data['result']['status'] not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        print(f'Error checking group membership: {e}')
        return False

def handle_telegram_check(update, context):
    """Handle Telegram group membership checking"""
    query = update.callback_query
    if query and query.data == "check_telegram":
        query.answer()
        context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
        
        if check_user_exist_groups(context.user_data['user_id']):
            # User joined groups, proceed to Twitter
            keyboard = [[InlineKeyboardButton("Proceed to X Follow", callback_data="proceed_twitter")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(settings.TELEGRAM_VERIFIED_MESSAGE, reply_markup=reply_markup)
            
            # Update user step
            update_user_step(context.user_data['user_id'], 2, telegram_verified=True)
            return TWITTER_SUBMIT
        else:
            # Still not in groups
            query.edit_message_text(settings.NOT_IN_GROUP_MESSAGE + "\n\n⏳ I'll continue checking automatically every 30 seconds...")
            return TELEGRAM_CHECK
    
    # Handle any text message in this state
    if hasattr(update, 'message') and update.message:
        update.message.reply_text("⏳ I'm automatically checking your group membership. Please wait...")
    return TELEGRAM_CHECK

def start_auto_membership_check(update, context):
    """Start automatic membership checking in a separate thread"""
    def auto_check():
        # Handle both Message and CallbackQuery objects
        if hasattr(update, 'callback_query') and update.callback_query:
            chat_id = update.callback_query.message.chat_id
        else:
            chat_id = update.message.chat_id
        user_id = context.user_data['user_id']
        max_attempts = 20  # Check for 10 minutes (20 * 30 seconds)
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(30)  # Wait 30 seconds
            attempt += 1
            
            try:
                if check_user_exist_groups(user_id):
                    # User joined! Send success message
                    keyboard = [[InlineKeyboardButton("Proceed to X Follow", callback_data="proceed_twitter")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    context.bot.send_message(
                        chat_id=chat_id,
                        text="🎉 " + settings.TELEGRAM_VERIFIED_MESSAGE,
                        reply_markup=reply_markup
                    )
                    
                    # Update user step
                    update_user_step(user_id, 2, telegram_verified=True)
                    break
                    
            except Exception as e:
                print(f"Error in auto membership check: {e}")
                continue
        
        # If we've exhausted all attempts
        if attempt >= max_attempts:
            keyboard = [[InlineKeyboardButton("I've Joined - Check Again", callback_data="check_telegram")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(
                chat_id=chat_id,
                text="⏰ Automatic checking has timed out. Please use the button below to check manually:",
                reply_markup=reply_markup
            )
    
    # Start the checking thread
    thread = threading.Thread(target=auto_check)
    thread.daemon = True
    thread.start()

def handle_twitter_submit(update, context):
    """Handle Twitter follow and username submission"""
    query = update.callback_query
    
    if query and query.data == "proceed_twitter":
        query.answer()
        query.edit_message_text(settings.TWITTER_FOLLOW_MESSAGE.format(
            twitter_link=settings.TWITTER_PAGE_LINK
        ))
        return TWITTER_SUBMIT
    
    # Handle username submission
    if update.message and update.message.text:
        username = update.message.text.strip().replace('@', '')
        
        # Save username and set status to pending
        update_user_step(
            context.user_data['user_id'], 
            2, 
            twitter_id=username,
            twitter_verification_status='pending'
        )
        
        update.message.reply_text(settings.TWITTER_PENDING_MESSAGE.format(username=username))
        return TWITTER_PENDING
    
    # Handle any other callback queries that shouldn't be processed here
    if query:
        query.answer()
        return TWITTER_SUBMIT
    
    if update.message:
        update.message.reply_text("Please submit your X (Twitter) username.")
    return TWITTER_SUBMIT

def handle_twitter_pending(update, context):
    """Handle users waiting for Twitter verification"""
    # Check if admin has approved/rejected
    try:
        user = session.query(users_data).filter(users_data.telegram_id == context.user_data['user_id']).first()
        if user:
            if user.twitter_verification_status == 'approved':
                keyboard = [[InlineKeyboardButton("Proceed to Submit Wallet", callback_data="proceed_wallet")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(settings.TWITTER_APPROVED_MESSAGE, reply_markup=reply_markup)
                update_user_step(context.user_data['user_id'], 3)
                return WALLET_SUBMIT
            elif user.twitter_verification_status == 'rejected':
                keyboard = [[InlineKeyboardButton("Proceed to X Follow", callback_data="proceed_twitter")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(settings.TWITTER_REJECTED_MESSAGE.format(
                    reason="Please ensure you've followed our X account"
                ))
                return TWITTER_SUBMIT
    except Exception as e:
        print(f"Error checking Twitter status: {e}")
    
    update.message.reply_text("⏳ Your X verification is still pending. Please wait for admin approval.")
    return TWITTER_PENDING

def handle_wallet_submit(update, context):
    """Handle wallet address submission"""
    query = update.callback_query
    
    if query and query.data == "proceed_wallet":
        query.answer()
        query.edit_message_text(settings.WALLET_PROMPT_MESSAGE)
        return WALLET_SUBMIT
    
    # Handle wallet address submission
    if update.message and update.message.text:
        wallet_address = update.message.text.strip()
        
        # Basic Solana address validation (44 characters, base58)
        if len(wallet_address) >= 32 and len(wallet_address) <= 44:
            try:
                # Save wallet and mark as completed
                update_user_step(
                    context.user_data['user_id'],
                    4,
                    wallet=wallet_address,
                    wallet_submitted=True,
                    verified=True
                )
                
                # Generate referral link
                ref_link = f"https://t.me/greendale1_bot?start={context.user_data['user_id']}"
                
                # Format and send completion message with referral link
                completion_message = settings.FINAL_SUCCESS_MESSAGE.format(ref_link=ref_link)
                update.message.reply_text(completion_message)
                return COMPLETED
                
            except Exception as e:
                print(f"Error saving wallet: {e}")
                update.message.reply_text(settings.ERROR_MESSAGE)
                return WALLET_SUBMIT
        else:
            update.message.reply_text("❌ Invalid Solana wallet address. Please enter a valid address.")
            return WALLET_SUBMIT
    
    update.message.reply_text("Please submit your Solana wallet address.")
    return WALLET_SUBMIT

def handle_completed(update, context):
    """Handle users who have completed registration"""
    # Check if user is submitting task proof
    if 'awaiting_submission' in context.user_data:
        # Handle task submission
        return handle_task_submission_text(update, context)
    
    # Default completed message for other interactions
    update.message.reply_text("✅ You have already completed the airdrop registration!\n\nThank you for participating in the Greendale Airdrop.")
    return COMPLETED

def userInfo(update, context):
    """Handle /info command"""
    context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
    user_info = user_details_summary(int(update.message.from_user.id))
    if user_info:
        update.message.reply_text(user_info)
    else:
        update.message.reply_text('User does not exist. Please use /start to signup')

def call_back(update, context):
    """Handle callback queries not handled by conversation handler"""
    query = update.callback_query
    callback_data = query.data
    
    # Filter out conversation-related callbacks to prevent conflicts
    conversation_callbacks = ["proceed_twitter", "proceed_wallet", "check_telegram"]
    if callback_data in conversation_callbacks:
        # Let the conversation handler deal with these
        return
    
    query.answer()
    print(f"callback called {callback_data}")
    
    if callback_data == "view_tasks":
        show_available_tasks(query, context.user_data)
    elif callback_data.startswith("task_"):
        task_id = callback_data.split("_")[1]
        show_task_details(query, context.user_data, task_id)
    elif callback_data.startswith("proceed_task_"):
        task_id = callback_data.split("_")[2]
        handle_task_proceed(query, context.user_data, task_id)
    elif callback_data.startswith("submit_task_"):
        task_id = callback_data.split("_")[2]
        handle_task_submit(query, context.user_data, task_id)
    elif callback_data == "start_registration":
        # Handle Start Registration button press
        # Get user_id from callback query and add to user_data
        user_id = query.from_user.id
        context.user_data['user_id'] = user_id
        
        # Create a mock update object that mimics message structure for compatibility
        class MockUpdate:
            def __init__(self, callback_query):
                self.message = callback_query
                self.callback_query = callback_query
        
        mock_update = MockUpdate(query)
        return check_telegram_membership(mock_update, context)

def show_available_tasks(update, user_data):
    """Show list of available tasks with completion status"""
    try:
        print("[DEBUG] show_available_tasks called")
        user_id = update.callback_query.from_user.id if hasattr(update, 'callback_query') else update.from_user.id
        
        # Fetch all tasks
        tasks_response = requests.get('http://localhost:5000/api/tasks')
        print(f"[DEBUG] API response status: {tasks_response.status_code}")
        
        if tasks_response.status_code != 200:
            print(f"[DEBUG] API error in show_available_tasks: {tasks_response.status_code}")
            update.edit_message_text("❌ Error fetching tasks. Please try again later.")
            return
            
        tasks_data = tasks_response.json()
        all_tasks = tasks_data.get('tasks', [])
        print(f"[DEBUG] Found {len(all_tasks)} tasks in show_available_tasks")
        
        if not all_tasks:
            update.edit_message_text("❌ No active tasks available at the moment.")
            return
        
        # Fetch user submissions
        submissions_response = requests.get(f'http://localhost:5000/api/user_submissions/{user_id}')
        user_submissions = []
        if submissions_response.status_code == 200:
            submissions_data = submissions_response.json()
            if submissions_data.get('success'):
                user_submissions = submissions_data.get('submissions', [])
        
        # Categorize tasks
        completed_tasks = []
        new_tasks = []
        
        submitted_task_ids = {sub['task_id'] for sub in user_submissions}
        
        for task in all_tasks:
            if task['id'] in submitted_task_ids:
                # Find the submission status
                submission = next((sub for sub in user_submissions if sub['task_id'] == task['id']), None)
                task['submission_status'] = submission['status'] if submission else 'pending'
                completed_tasks.append(task)
            else:
                new_tasks.append(task)
        
        # Build message
        message = ""
        
        keyboard = []
        
        # Add new tasks section
        if new_tasks:
            for task in new_tasks:
                button_text = f"🆕 {task['title']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"task_{task['id']}")])
                print(f"[DEBUG] Added new task: {task['title']} (ID: {task['id']})")
            message += "\n"
        
        # Add completed tasks section
        if completed_tasks:
            message += "✅ <b>Your Submissions</b>\n"
            for task in completed_tasks:
                status_emoji = {
                    'pending': '⏳',
                    'approved': '✅', 
                    'rejected': '❌'
                }.get(task['submission_status'], '⏳')
                button_text = f"{status_emoji} {task['title']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"task_{task['id']}")])
                print(f"[DEBUG] Added completed task: {task['title']} (ID: {task['id']}, Status: {task['submission_status']})")
        
        if not keyboard:
            update.edit_message_text("❌ No tasks available at the moment.")
            return
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
        print("[DEBUG] Tasks message sent successfully from show_available_tasks")
        
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        update.edit_message_text("❌ Error fetching tasks. Please try again later.")

def show_task_details(update, user_data, task_id):
    """Show detailed information about a specific task"""
    try:
        response = requests.get('http://localhost:5000/api/tasks')
        if response.status_code == 200:
            data = response.json()
            tasks = data.get('tasks', [])
            
            task = next((t for t in tasks if str(t['id']) == str(task_id)), None)
            if not task:
                update.edit_message_text("❌ Task not found.")
                return
            
            message = f"🎯 <b>{task['title']}</b>\n\n"
            message += f"📝 <b>Description:</b>\n{task['description']}\n\n"
            message += f"🔗 <b>Type:</b> {task['task_type'].title()}\n\n"
            
            if task.get('requirements'):
                message += f"📋 <b>Requirements:</b>\n{task['requirements']}\n\n"
            
            keyboard = [
                [InlineKeyboardButton("🚀 Proceed", callback_data=f"proceed_task_{task_id}")],
                [InlineKeyboardButton("⬅️ Back to Tasks", callback_data="view_tasks")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
        else:
            update.edit_message_text("❌ Error fetching task details. Please try again later.")
    except Exception as e:
        print(f"Error fetching task details: {e}")
        update.edit_message_text("❌ Error fetching task details. Please try again later.")

def handle_task_proceed(update, user_data, task_id):
    """Handle when user clicks Proceed on a task"""
    try:
        response = requests.get('http://localhost:5000/api/tasks')
        if response.status_code == 200:
            data = response.json()
            tasks = data.get('tasks', [])
            
            task = next((t for t in tasks if str(t['id']) == str(task_id)), None)
            if not task:
                update.edit_message_text("❌ Task not found.")
                return
            
            message = f"🎯 <b>{task['title']}</b>\n\n"
            message += f"📝 Platform: {task.get('task_type', 'General').title()}\n"
            message += f"Task: {task['description']}\n\n"
            
            message += "✨ <b>Complete this task to receive more airdrop allocation!</b>\n\n"
            
            if task.get('requirements'):
                message += f"📋 <b>Requirements:</b>\n{task['requirements']}\n\n"
            
            message += "✅ <b>After completing, please submit the proof as a reply to this message.</b>\n\n"
            message += "📎 Please provide the link or proof of completion:"
            
            keyboard = [
                [InlineKeyboardButton("📤 Submit Proof", callback_data=f"submit_task_{task_id}")],
                [InlineKeyboardButton("⬅️ Back", callback_data=f"task_{task_id}")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
            
            # Store task_id in user context for submission
            user_data['current_task_id'] = task_id
        else:
            update.edit_message_text("❌ Error fetching task details. Please try again later.")
    except Exception as e:
        print(f"Error handling task proceed: {e}")
        update.edit_message_text("❌ Error processing request. Please try again later.")

def handle_task_submit(update, user_data, task_id):
    """Handle task submission request"""
    try:
        message = "📤 <b>Submit Your Proof</b>\n\n"
        message += "Please reply to this message with your proof of completion:\n\n"
        message += "• For Twitter tasks: Share the tweet link\n"
        message += "• For Telegram tasks: Share your username\n"
        message += "• For other tasks: Share the relevant link or proof\n\n"
        message += "⏳ <i>Waiting for your submission...</i>"
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Back", callback_data=f"proceed_task_{task_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
        
        # Store task_id for text submission handler
        user_data['awaiting_submission'] = task_id
        
    except Exception as e:
        print(f"Error handling task submit: {e}")
        update.edit_message_text("❌ Error processing request. Please try again later.")

def handle_task_submission_text(update, context):
    """Handle text submissions for tasks"""
    if 'awaiting_submission' not in context.user_data:
        return
    
    task_id = context.user_data['awaiting_submission']
    submission_text = update.message.text
    user_id = update.message.from_user.id
    
    try:
        # Submit to backend API
        payload = {
            'user_id': user_id,
            'task_id': task_id,
            'submission_link': submission_text
        }
        
        response = requests.post('http://localhost:5000/api/submit_task', json=payload)
        
        if response.status_code == 200:
            update.message.reply_text(
                "✅ <b>Submission Received!</b>\n\n"
                "Thank you! Your submission is under review.\n\n"
                "📋 <b>What you submitted:</b>\n"
                f"{submission_text}\n\n"
                "⏳ You will be notified once the admin reviews your submission.",
                parse_mode='HTML'
            )
            # Clear the awaiting submission flag
            del context.user_data['awaiting_submission']
        else:
            error_data = response.json()
            error_message = error_data.get('error', 'Unknown error occurred')
            update.message.reply_text(f"❌ Error: {error_message}")
            
    except Exception as e:
        print(f"Error submitting task: {e}")
        update.message.reply_text("❌ Error submitting task. Please try again later.")

def tasks_command(update, context):
    """Handle /tasks command"""
    try:
        user_id = update.message.from_user.id
        
        # Fetch all tasks
        tasks_response = requests.get('http://localhost:5000/api/tasks')
        
        if tasks_response.status_code != 200:
            update.message.reply_text("❌ Error fetching tasks. Please try again later.")
            return
            
        tasks_data = tasks_response.json()
        all_tasks = tasks_data.get('tasks', [])
        
        if not all_tasks:
            update.message.reply_text("❌ No active tasks available at the moment.")
            return
        
        # Fetch user submissions
        submissions_response = requests.get(f'http://localhost:5000/api/user_submissions/{user_id}')
        user_submissions = []
        
        if submissions_response.status_code == 200:
            submissions_data = submissions_response.json()
            user_submissions = submissions_data.get('submissions', [])
        
        # Create a set of task IDs that user has submitted
        submitted_task_ids = {sub['task_id'] for sub in user_submissions}
        
        # Categorize tasks
        new_tasks = [task for task in all_tasks if task['id'] not in submitted_task_ids]
        completed_tasks = [task for task in all_tasks if task['id'] in submitted_task_ids]
        
        # Build message
        message = ""
        
        keyboard = []
        
        # Add new tasks section
        if new_tasks:
            for task in new_tasks:
                button_text = f"🆕 {task['title']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"task_{task['id']}")])
            message += "\n"
        
        # Add completed tasks section
        if completed_tasks:
            message += "📋 <b>Your Submissions</b>\n"
            for task in completed_tasks:
                # Find the submission for this task
                submission = next((sub for sub in user_submissions if sub['task_id'] == task['id']), None)
                if submission:
                    status_emoji = "✅" if submission['status'] == 'approved' else "⏳" if submission['status'] == 'pending' else "❌"
                    message += f"• {status_emoji} {task['title']} - {submission['status'].title()}\n"
                    button_text = f"{status_emoji} {task['title']}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f"task_{task['id']}")])
            message += "\n"
        
        if not new_tasks and not completed_tasks:
            message += "❌ No tasks available at the moment."
        else:
            message += "Tap on any task to view details!"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        update.message.reply_text("❌ Error fetching tasks. Please try again later.")

def error(update, context):
    """Log Errors caused by Updates."""
    print(f'Update "{update}" caused error "{context.error}"')


def setup_handlers(dp):
    """Setup all handlers for the dispatcher - used by both polling and webhook modes"""
    # Add conversation handler with the enhanced workflow states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TELEGRAM_CHECK: [
                CallbackQueryHandler(handle_telegram_check),
                MessageHandler(Filters.text, handle_telegram_check)
            ],
            TWITTER_SUBMIT: [
                CallbackQueryHandler(handle_twitter_submit),
                MessageHandler(Filters.text, handle_twitter_submit)
            ],
            TWITTER_PENDING: [
                MessageHandler(Filters.text, handle_twitter_pending)
            ],
            WALLET_SUBMIT: [
                CallbackQueryHandler(handle_wallet_submit),
                MessageHandler(Filters.text, handle_wallet_submit)
            ],
            COMPLETED: [
                MessageHandler(Filters.text, handle_completed)
            ],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    
    dp.add_handler(CommandHandler('info', userInfo))
    dp.add_handler(CommandHandler('tasks', tasks_command))
    dp.add_handler(conv_handler)
    dp.add_handler(CallbackQueryHandler(call_back))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_task_submission_text))
    dp.add_error_handler(error)

def main():
    # Create the Updater and pass it your bot's token with improved timeout settings.
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
    
    # Start the Bot with enhanced polling
    updater.start_polling(
        poll_interval=1.0,
        timeout=30,
        drop_pending_updates=True,
        bootstrap_retries=-1
    )
    
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

