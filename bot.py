import pymongo
import logging
import datetime
import pytz
from telegram import Update, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters, ChatMemberHandler

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MongoDB client
def initialize_db():
    client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    db = client["training_bot"]
    trainings_collection = db["trainings"]
    trainings_collection.create_index([("datetime", pymongo.ASCENDING)])
    return db

# Command to start the bot
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Welcome to the training sign-up bot! Use /signup to register for a training.")

# Command to add a new training
async def new_training(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Please provide details for the new training in the following format:\n"
                                    "Type, Date and Time (YYYY-MM-DD HH:MM), Address, Holding (In person/Remote), Holder")

    # Listen for the user's response
    context.user_data['waiting_for_new_training'] = True

# Command to sign up for training
async def signup(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Please specify which training you'd like to sign up for: De-escalator, Shooting harassment, General, Trainer training.")
    context.user_data['waiting_for_signup'] = True


async def training_details(update: Update, context: CallbackContext) -> None:
    if 'waiting_for_signup' in context.user_data and context.user_data['waiting_for_signup']:
        # context.user_data['waiting_for_signup']
        
        message_text = update.message.text
        # Process the message text to determine criteria for filtering trainings
        # You can use if-else statements or a more sophisticated approach here

        db = initialize_db()
        trainings_collection = db["trainings"]

        criteria = {"type": message_text}  # Filter by training type
        selected_trainings = trainings_collection.find(criteria)

        if trainings_collection.count_documents(criteria) > 0:
            response = "Here are the trainings that match your criteria:\n\n"
            for training in selected_trainings:
                response += f"Training: {training['type']}\n"
                response += f"Date and Time: {training['datetime']}\n"
                response += f"Address: {training['address']}\n"
                response += f"Holding: {training['holding']}\n"
                response += f"Holder: {training['holder']}\n\n"
            await update.message.reply_text(response)
            
        else:
            await update.message.reply_text("No trainings found that match your criteria.")
    elif 'waiting_for_new_training' in context.user_data and context.user_data['waiting_for_new_training']:
        context.user_data['waiting_for_new_training'] = False

        message_text = update.message.text
        details = message_text.split(', ')

        if len(details) == 5:
            training_type, date_time, address, holding, holder = details
            db = initialize_db()
            trainings_collection = db["trainings"]

            # Convert date and time to a datetime object
            datetime_obj = datetime.datetime.strptime(
                date_time, '%Y-%m-%d %H:%M')

            # Insert the new training into the collection
            new_training = {
                "type": training_type,
                "datetime": datetime_obj,
                "address": address,
                "holding": holding,
                "holder": holder
            }

            trainings_collection.insert_one(new_training)

            response = f"New training added:\n"
            response += f"Training: {training_type}\n"
            response += f"Date and Time: {datetime_obj}\n"
            response += f"Address: {address}\n"
            response += f"Holding: {holding}\n"
            response += f"Holder: {holder}\n"

            await update.message.reply_text(response)
        else:
            await update.message.reply_text("Please provide the details in the correct format.")
    else:
        await update.message.reply_text("Please use /signup to register for a training.")

# Command to complete the sign-up process


async def complete_signup(update: Update, context: CallbackContext) -> None:
    if 'selected_training' in context.user_data:
        selected_training = context.user_data['selected_training']

        # Store the registration information in the database
        db = initialize_db()
        registrations_collection = db["registrations"]

        new_registration = {
            "user_id": update.message.from_user.id,
            "training_type": selected_training['type'],
            "datetime": selected_training['datetime'],
            "address": selected_training['address'],
            "holding": selected_training['holding'],
            "holder": selected_training['holder']
        }

        registrations_collection.insert_one(new_registration)

        response = f"Registration completed:\n"
        response += f"Training: {selected_training['type']}\n"
        response += f"Date and Time: {selected_training['datetime']}\n"
        response += f"Address: {selected_training['address']}\n"
        response += f"Holding: {selected_training['holding']}\n"
        response += f"Holder: {selected_training['holder']}\n"

        await update.message.reply_text(response)
        del context.user_data['selected_training']
    else:
        await update.message.reply_text("Please use /signup to select a training first.")

# Handler for processing the selected training


async def selected_training(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    if chat.type != Chat.PRIVATE:
        return
    
    if 'waiting_for_signup' in context.user_data and context.user_data['waiting_for_signup']:
        context.user_data['waiting_for_signup'] = False

        selected_training_type = update.message.text
        db = initialize_db()
        trainings_collection = db["trainings"]

        selected_training = trainings_collection.find_one(
            {"type": selected_training_type})

        if selected_training:
            context.user_data['selected_training'] = selected_training
            await update.message.reply_text(f"You've selected the following training:\n"
                                            f"Training: {selected_training['type']}\n"
                                            f"Date and Time: {selected_training['datetime']}\n"
                                            f"Address: {selected_training['address']}\n"
                                            f"Holding: {selected_training['holding']}\n"
                                            f"Holder: {selected_training['holder']}\n\n"
                                            f"Please use /complete_signup to finish the registration.")
        else:
            await update.message.reply_text("Selected training not found.")
    else:
        await update.message.reply_text("Please use /signup to register for a training.")

# Function to announce upcoming trainings
async def announce_trainings(update: Update, context: CallbackContext) -> None:
    db = initialize_db()
    trainings_collection = db["trainings"]

    current_time = datetime.datetime.now(pytz.utc)
    upcoming_trainings = trainings_collection.find(
        {"datetime": {"$gte": current_time}}).sort("datetime")

    if trainings_collection.count_documents({"datetime": {"$gte": current_time}}) > 0:

        response = "Upcoming trainings:\n\n"
        for training in upcoming_trainings:
            response += f"Training: {training['type']}\n"
            response += f"Date and Time: {training['datetime']}\n"
            response += f"Address: {training['address']}\n"
            response += f"Holding: {training['holding']}\n"
            #response += f"Holder: {training['holder']}\n\n"
            response += "\n"
            
        response += "\nSignup for those trainings by sending me /signup in private chat, and then following instructions"
        await context.bot.send_message(chat_id='-1001988401379', text=response)
    else:
        await context.bot.send_message(
            chat_id='-1001988401379', text="No upcoming trainings.")

# Command to send a message to registered participants
async def send_message_to_participants(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Please specify the training type for which you want to send a message to participants:")
    context.user_data['waiting_for_message_type'] = True

# Handler for processing the selected training type for sending messages


async def selected_message_type(update: Update, context: CallbackContext) -> None:
    if 'waiting_for_message_type' in context.user_data and context.user_data['waiting_for_message_type']:
        context.user_data['waiting_for_message_type'] = False

        selected_training_type = update.message.text
        db = initialize_db()
        trainings_collection = db["trainings"]

        selected_training = trainings_collection.find_one(
            {"type": selected_training_type})

        if selected_training:
            context.user_data['selected_training_for_message'] = selected_training
            await update.message.reply_text("Please enter the message you want to send to participants:")
        else:
            await update.message.reply_text("Selected training not found.")
    else:
        await update.message.reply_text("Please use /send_message_to_participants to send a message.")

# Handler for sending a message to registered participants


async def send_message(update: Update, context: CallbackContext) -> None:
    if 'selected_training_for_message' in context.user_data:
        selected_training = context.user_data['selected_training_for_message']
        message_to_send = update.message.text

        message_to_send += f"\n\n\nSent by human"

        db = initialize_db()
        registrations_collection = db["registrations"]

        participants = registrations_collection.find(
            {"training_type": selected_training['type']})
        for participant in participants:
            user_id = participant['user_id']
            await context.bot.send_message(chat_id=user_id, text=message_to_send)

        await update.message.reply_text("Message sent to participants.")
        del context.user_data['selected_training_for_message']
    else:
        await update.message.reply_text("Please select a training type using /send_message_to_participants first.")

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
