import os
import json
import io
from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- DEDICATED BANNER IMAGE URL ---
BANNER_IMPORT_EXPORT = "https://files.catbox.moe/vmecgj.png"

# --- IMPORT/EXPORT HELP TEXT ---
IMPORT_EXPORT_HELP_TEXT = (
    "**Import / Export**\n\n"
    "Allows you to import/export settings for a chat, so you can quickly set up "
    "other chats using a pre-existing template. Instead of setting the same settings "
    "over and over again in different chats, you can use this feature to copy the general "
    "configuration across groups.\n\n"
    "The generated file is in standard JSON format, so if there are any settings you don't "
    "want to import to your other chats, just open the file and edit it before importing.\n\n"
    "Exporting settings can be done by any administrator, but for security reasons, "
    "importing can only be done by the group creator.\n\n"
    "**Chat Owner / Admin Commands:**\n"
    "• `/export`: Generate a JSON file containing all chat settings and filters.\n"
    "• `/import`: Import settings by replying to a previously exported JSON file.\n"
    "• `/reset`: Reset all settings and filters in the current chat."
)

# --- INLINE CALLBACK HANDLER (ONLY BACK BUTTON) ---

@Client.on_callback_query(filters.regex(r"^(help_import_export|help_import)$"))
async def help_import_export_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{IMPORT_EXPORT_HELP_TEXT}\n[\u200b]({BANNER_IMPORT_EXPORT})"
    
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False,
            parse_mode=enums.ParseMode.MARKDOWN
        )
    except RPCError:
        pass
    await callback.answer()

# --- ADMIN & OWNER CHECKERS ---

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

async def is_owner(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status == ChatMemberStatus.OWNER
    except Exception:
        return False

# --- EXPORT COMMAND HANDLER ---

@Client.on_message(filters.command("export"))
async def export_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to export chat settings.")

    chat_id = message.chat.id
    
    try:
        from modules.filters import CHAT_FILTERS
        filters_data = CHAT_FILTERS.get(chat_id, {})
    except ImportError:
        filters_data = {}

    try:
        from modules.greetings import GREETINGS_DB
        greetings_data = GREETINGS_DB.get(chat_id, {})
    except ImportError:
        greetings_data = {}

    export_payload = {
        "chat_id": chat_id,
        "chat_title": message.chat.title,
        "filters": filters_data,
        "greetings": greetings_data
    }

    json_data = json.dumps(export_payload, indent=4)
    file_bytes = io.BytesIO(json_data.encode("utf-8"))
    file_bytes.name = f"config_{chat_id}.json"

    await client.send_document(
        chat_id=chat_id,
        document=file_bytes,
        caption=f"✅ **Exported configuration for** `{message.chat.title}`",
        parse_mode=enums.ParseMode.MARKDOWN
    )

# --- IMPORT COMMAND HANDLER ---

@Client.on_message(filters.command("import"))
async def import_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_owner(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ For security reasons, importing settings can only be performed by the Group Owner.")

    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("❌ Please reply to an exported JSON configuration file with `/import`.")

    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".json"):
        return await message.reply_text("❌ Invalid file format! Please provide a valid `.json` settings file.")

    downloaded_path = await client.download_media(message.reply_to_message)
    
    try:
        with open(downloaded_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chat_id = message.chat.id

        if "filters" in data:
            try:
                from modules.filters import CHAT_FILTERS
                CHAT_FILTERS[chat_id] = data["filters"]
            except ImportError:
                pass

        if "greetings" in data:
            try:
                from modules.greetings import GREETINGS_DB
                GREETINGS_DB[chat_id] = data["greetings"]
            except ImportError:
                pass

        await message.reply_text("✅ Chat settings and configuration imported successfully!")
    except Exception as e:
        await message.reply_text(f"❌ Failed to import configuration: `{str(e)}`")
    finally:
        if os.path.exists(downloaded_path):
            os.remove(downloaded_path)

# --- RESET COMMAND HANDLER ---

@Client.on_message(filters.command("reset"))
async def reset_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_owner(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Only the Group Owner can reset chat settings.")

    chat_id = message.chat.id

    try:
        from modules.filters import CHAT_FILTERS
        if chat_id in CHAT_FILTERS:
            CHAT_FILTERS[chat_id].clear()
    except ImportError:
        pass

    try:
        from modules.greetings import GREETINGS_DB
        if chat_id in GREETINGS_DB:
            GREETINGS_DB[chat_id] = {
                "welcome_enabled": True,
                "welcome_text": "Hey {mention}, welcome to **{chatname}**!",
                "goodbye_enabled": True,
                "goodbye_text": "Goodbye {first}!"
            }
    except ImportError:
        pass

    await message.reply_text("✅ All chat settings and active filters have been reset to default.")
