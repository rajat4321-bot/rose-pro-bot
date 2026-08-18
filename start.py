from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from database import register_user

START_GIF = "https://files.catbox.moe/25v6ip.gif"

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    
    # Real MongoDB registration
    await register_user(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username,
        lang=user.language_code
    )

    text = (
        f"Hey {user.mention}! 👋\n\n"
        "I am **ATHER X MANAGEMENT**, your all-in-one powerful group management bot built to keep your communities safe, active, and organized.\n\n"
        "• Click /help to explore all available commands and features.\n"
        "• Check /privacy to view how your data is safely managed."
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Add me to your chat!", 
                url=f"https://t.me/{client.me.username}?startgroup=true"
            )
        ]
    ])
    
    await message.reply_animation(
        animation=START_GIF,
        caption=text,
        reply_markup=keyboard
    )
