import asyncio
import json
import io
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from database import get_user_full_privacy_data, delete_user_data, register_user

PRIVACY_PHOTO = "https://files.catbox.moe/y0szup.png"

PRIVACY_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Retrieve data", callback_data="privacy_retrieve"),
        InlineKeyboardButton("Delete data", callback_data="privacy_delete")
    ],
    [
        InlineKeyboardButton("Cancel", callback_data="privacy_cancel")
    ]
])

DELETE_CONFIRM_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Yes, delete all my data", callback_data="privacy_confirm_delete")
    ],
    [
        InlineKeyboardButton("No, I changed my mind!", callback_data="privacy_cancel_delete")
    ]
])

@Client.on_message(filters.command("privacy") & filters.private)
async def privacy_command(client: Client, message: Message):
    text = (
        "Select one of the options below for more information about how "
        "**ATHER X MANAGEMENT** handles your privacy and data security.\n\n"
        "You can inspect or erase all personal records associated with your account at any time."
        f"[\u200b]({PRIVACY_PHOTO})"
    )
    
    await message.reply_text(
        text=text,
        reply_markup=PRIVACY_KEYBOARD,
        disable_web_page_preview=False
    )

@Client.on_callback_query(filters.regex("^privacy_"))
async def privacy_callback(client: Client, callback: CallbackQuery):
    data = callback.data
    user = callback.from_user

    if data == "privacy_retrieve":
        await callback.answer("Initializing data export...", show_alert=False)
        
        status_msg = await callback.message.reply_text("Generating data log... This may take a while.")
        
        # Real Live MongoDB Fetch across all collections
        live_privacy_data = await get_user_full_privacy_data(user.id)
        
        if not live_privacy_data:
            await status_msg.edit_text("❌ No active record found in database. Please send /start first.")
            return

        json_data = json.dumps(live_privacy_data, indent=4)
        bio = io.BytesIO(json_data.encode("utf-8"))
        bio.name = f"{user.id}.json"

        caption_text = f"privacy data report for **{user.first_name}** (`{user.id}`) in JSON format."

        await callback.message.reply_document(
            document=bio,
            file_name=f"{user.id}.json",
            caption=caption_text
        )
        await status_msg.delete()

    elif data == "privacy_delete":
        await callback.answer()
        delete_text = (
            "**Are you sure you want to delete your data?**\n\n"
            "**Note that this will:**\n"
            "• Delete all notes/filters saved in your private chat.\n"
            "• Remove your federation settings and admin status linked with bot.\n"
            "• Remove all approvals across managed chats.\n\n"
            "__This action CANNOT be undone.__"
        )
        await callback.message.edit_text(
            text=delete_text,
            reply_markup=DELETE_CONFIRM_KEYBOARD
        )

    elif data == "privacy_confirm_delete":
        await callback.answer("Processing deletion...", show_alert=False)
        await callback.message.edit_text("⏳ Deleting your data from bot database...")
        
        # Wipe user data from All DB Collections
        await delete_user_data(user.id)
        await asyncio.sleep(1.5)
        
        await callback.message.edit_text(
            "✅ **All your personal data has been successfully wiped from our database.**"
        )

    elif data == "privacy_cancel_delete":
        await callback.answer("Operation cancelled.")
        
        await register_user(user.id, user.first_name, user.username, user.language_code)
        
        start_text = (
            f"Hey {user.mention}! 👋\n\n"
            "I am **ATHER X MANAGEMENT**, your all-in-one powerful group management bot built to keep your communities safe, active, and organized.\n\n"
            "• Click /help to explore all available commands and features.\n"
            "• Check /privacy to view how your data is safely managed."
        )
        start_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "➕ Add me to your chat!", 
                    url=f"https://t.me/{client.me.username}?startgroup=true"
                )
            ]
        ])
        
        await callback.message.delete()
        await client.send_animation(
            chat_id=callback.message.chat.id,
            animation="https://telegra.ph/file/36b85623b00684061877a.mp4",
            caption=start_text,
            reply_markup=start_keyboard
        )

    elif data == "privacy_cancel":
        await callback.answer("Cancelled")
        await callback.message.delete()
