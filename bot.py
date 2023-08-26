import pymongo
import logging
import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters, ChatMemberHandler

from trainings import (
    new_training, 
    training_details, 
    signup, 
    complete_signup, 
    selected_training, 
    announce_trainings, 
    send_message, 
    send_message_to_participants, 
    selected_message_type)

from .db import initialize_db

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Command to start the bot
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Welcome to the SMHV bot! Use /help to get started.")


# Handler for saving received messages
async def save_message(update: Update, context: CallbackContext) -> None:
    if update.message.text:
        db = initialize_db()
        messages_collection = db["messages"]

        new_message = {
            "user_id": update.message.from_user.id,
            "chat_id": update.message.chat.id,
            "message_text": update.message.text,
            "timestamp": update.message.date
        }

        messages_collection.insert_one(new_message)
    
    if "waiting_for_signup" in context.user_data and context.user_data["waiting_for_signup"]: #or "waiting_for_new_training" in context.user_data and context.user_data['waiting_for_new_training']:
        await selected_training(update, context)
        
    if 'waiting_for_message_type' in context.user_data and context.user_data['waiting_for_message_type']:
        await selected_message_type(update, context)
        
    if 'selected_training_for_message' in context.user_data and context.user_data['selected_training_for_message']:
        await send_message(update, context)
        
    if 'waiting_for_new_training' in context.user_data and context.user_data['waiting_for_new_training']:
        await training_details(update, context)    

# Handler for saving member changes in rooms
async def save_member_change(update: Update, context: CallbackContext) -> None:
    if update.chat_member:
        db = initialize_db()
        member_changes_collection = db["member_changes"]

        new_member_change = {
            "chat_id": update.chat_member.chat.id,
            "user_id": update.chat_member.from_user.id,
            "status": update.chat_member.new_chat_member.status,
            "timestamp": update.chat_member.date
        }

        member_changes_collection.insert_one(new_member_change)

def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    application = Application.builder().token(
        "TOKEN").build()

    # Command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('new_training', new_training))
    application.add_handler(CommandHandler('signup', signup))
    application.add_handler(CommandHandler(
        'complete_signup', complete_signup))  # New command
    application.add_handler(CommandHandler(
        'send_message_to_participants', send_message_to_participants))
    application.add_handler(CommandHandler(
        'send_message', send_message))  # New command
    application.add_handler(CommandHandler('announce', announce_trainings))
    application.add_handler(CommandHandler('help', help))

       # Handle members joining/leaving chats.
    application.add_handler(ChatMemberHandler(save_member_change, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(save_member_change, ChatMemberHandler.MY_CHAT_MEMBER))


    # Message handler for training details
    application.add_handler(MessageHandler(filters.TEXT, save_message))  # New handler for saving messages

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, selected_training))  # New handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, training_details))

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, send_message))  # New handler
    

    


    # Schedule the weekly training announcement
    job_queue = application.job_queue
    # 604800 seconds = 1 week
    
    weeks = 7
    days = 0 + weeks*7
    hours = 0 + days*24    
    minutes = 0 + hours*60
    seconds = 0 + minutes*60

    job_queue.run_repeating(announce_trainings, interval=seconds, first=0)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
