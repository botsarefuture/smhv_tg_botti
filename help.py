from telegram import Update
from telegram.ext import CallbackContext



help_subjects = ["trainings"]

# Command to start the bot
async def help(update: Update, context: CallbackContext) -> None:
    help_text = ""

    help_text += "Trainings:\n"
    help_text += "/signup to start signing up for the training"
    help_text += "then answer to the bot the training you want to (de-escalator or general or )"

    await update.message.reply_text(help_text)