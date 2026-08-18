import re
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- DEDICATED BANNER IMAGE URLS ---
BANNER_FILTERS_MAIN = "https://files.catbox.moe/mdppa6.png"
BANNER_FILTERS_USAGE = "https://files.catbox.moe/i2wwwx.png"

# --- IN-MEMORY DATABASE ---
CHAT_FILTERS = {}

# --- HELP TEXT STRINGS ---

FILTERS_MAIN_HELP = (
    "**⚡ Filters**\n\n"
    "Make your chat more lively with filters; The bot will reply to certain words!\n\n"
    "Filters are case insensitive; every time someone says your trigger words, "
    "the bot will reply with something else! Can be used to create your own commands, if desired.\n\n"
    "**Commands:**\n"
    "• /filter [trigger] [reply]: Every time someone says \"trigger\", the bot will reply with \"reply\". "
    "For multiple word triggers, quote the trigger.\n"
    "• /filters: List all chat filters.\n"
    "• /stop [trigger]: Stop the bot from replying to \"trigger\".\n"
    "• /stopall: Stop ALL filters in the current chat. This cannot be undone."
)

FILTERS_USAGE_HELP = (
    "**⚡ Example Usage**\n\n"
    "Filters can serve quite complicated, so here are some examples, so you can get some inspiration.\n\n"
    "**Examples:**\n"
    "• To set a filter for a single word:\n"
    "`/filter hello Hello there! How are you?`\n\n"
    "• To set a filter with multiple words in the trigger:\n"
    "`/filter \"hello there\" General Kenobi!`\n\n"
    "• To set a filter replying to a saved message or sticker:\n"
    "Reply to the message or sticker with `/filter [trigger]`\n\n"
    "• To stop a specific filter:\n"
    "`/stop hello`\n\n"
    "• To view all active filters in the current group:\n"
    "`/filters`"
)

# --- INLINE CALLBACK HANDLERS ---

@Client.on_callback_query(filters.regex(r"^help_filters$"))
async def help_filters_main(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Example usage", callback_data="filter_cmd_usage")],
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{FILTERS_MAIN_HELP}\n[\u200b]({BANNER_FILTERS_MAIN})"
    try:
        await callback.message.edit_text(text=full_text, reply_markup=keyboard, disable_web_page_preview=False)
    except RPCError:
        pass
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^filter_cmd_usage$"))
async def filter_cmd_usage_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="help_filters")]])
    full_text = f"{FILTERS_USAGE_HELP}\n[\u200b]({BANNER_FILTERS_USAGE})"
    try:
        await callback.message.edit_text(text=full_text, reply_markup=keyboard, disable_web_page_preview=False)
    except RPCError:
        pass
    await callback.answer()

# --- STRICT REAL LOGIC COMMAND HANDLERS ---

@Client.on_message(filters.command("filter"))
async def add_filter_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please run it inside a Telegram group.")

    user_id = message.from_user.id
    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return await message.reply_text("❌ You need to be an Admin to add filters.")
    except Exception:
        return

    args = message.command[1:]
    if not args and not message.reply_to_message:
        return await message.reply_text("Usage: /filter [trigger] [reply] or reply to media/text/links with /filter [trigger]")

    chat_id = message.chat.id
    if chat_id not in CHAT_FILTERS:
        CHAT_FILTERS[chat_id] = {}

    filter_data = {}

    if message.reply_to_message:
        if not args:
            return await message.reply_text("Please provide a trigger keyword.")
        trigger = args[0].lower()
        replied = message.reply_to_message

        if replied.sticker:
            filter_data = {"type": "sticker", "content": replied.sticker.file_id}
        elif replied.photo:
            filter_data = {"type": "photo", "content": replied.photo.file_id, "caption": replied.caption}
        elif replied.video:
            filter_data = {"type": "video", "content": replied.video.file_id, "caption": replied.caption}
        elif replied.animation:
            filter_data = {"type": "animation", "content": replied.animation.file_id, "caption": replied.caption}
        elif replied.voice:
            filter_data = {"type": "voice", "content": replied.voice.file_id, "caption": replied.caption}
        elif replied.document:
            filter_data = {"type": "document", "content": replied.document.file_id, "caption": replied.caption}
        elif replied.text:
            filter_data = {"type": "text", "content": replied.text}
        else:
            return await message.reply_text("❌ Unsupported message type.")
    else:
        full_raw = message.text.split(None, 1)[1] if len(message.text.split(None, 1)) > 1 else ""
        quoted_match = re.match(r'^"([^"]+)"\s+(.+)', full_raw)
        if quoted_match:
            trigger = quoted_match.group(1).lower()
            reply_text = quoted_match.group(2)
        else:
            parts = full_raw.split(None, 1)
            if len(parts) < 2:
                return await message.reply_text("Usage: /filter [trigger] [reply]")
            trigger = parts[0].lower()
            reply_text = parts[1]

        filter_data = {"type": "text", "content": reply_text}

    CHAT_FILTERS[chat_id][trigger] = filter_data
    await message.reply_text(f"✅ Filter saved for **{trigger}**!")

@Client.on_message(filters.command("stop"))
async def stop_filter_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please run it inside a Telegram group.")

    user_id = message.from_user.id
    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return await message.reply_text("❌ You need to be an Admin to remove filters.")
    except Exception:
        return

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: /stop [trigger]")

    trigger = args[0].lower()
    chat_id = message.chat.id

    if chat_id in CHAT_FILTERS and trigger in CHAT_FILTERS[chat_id]:
        del CHAT_FILTERS[chat_id][trigger]
        await message.reply_text(f"✅ Stopped filter **{trigger}**.")
    else:
        await message.reply_text("ℹ️ No filter found for that trigger.")

@Client.on_message(filters.command("stopall"))
async def stopall_filters_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please run it inside a Telegram group.")

    user_id = message.from_user.id
    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status != ChatMemberStatus.OWNER:
            return await message.reply_text("❌ Only the group creator can clear all filters.")
    except Exception:
        return

    chat_id = message.chat.id
    if chat_id in CHAT_FILTERS:
        CHAT_FILTERS[chat_id].clear()
        await message.reply_text("✅ Cleared all filters in this chat.")
    else:
        await message.reply_text("ℹ️ No filters active in this chat.")

@Client.on_message(filters.command("filters"))
async def list_filters_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please run it inside a Telegram group.")

    chat_id = message.chat.id
    if chat_id not in CHAT_FILTERS or not CHAT_FILTERS[chat_id]:
        return await message.reply_text("ℹ️ No filters currently active in this chat.")

    text = "**Active Filters in this Chat:**\n\n"
    for trg in CHAT_FILTERS[chat_id].keys():
        text += f"• `{trg}`\n"
    await message.reply_text(text)

# --- AUTO FILTER MATCH RESPONDER (DIRECT SEND / NO REPLY TAG) ---

@Client.on_message(filters.group & filters.text & ~filters.bot, group=1)
async def auto_filter_responder(client: Client, message: Message):
    if not message.text or message.text.startswith("/"):
        return

    chat_id = message.chat.id
    if chat_id not in CHAT_FILTERS or not CHAT_FILTERS[chat_id]:
        return

    msg_text = message.text.lower()
    for trigger, data in CHAT_FILTERS[chat_id].items():
        if re.search(r'\b' + re.escape(trigger) + r'\b', msg_text):
            m_type = data.get("type", "text")
            content = data.get("content")
            caption = data.get("caption")

            if m_type == "sticker":
                await client.send_sticker(chat_id=chat_id, sticker=content)
            elif m_type == "photo":
                await client.send_photo(chat_id=chat_id, photo=content, caption=caption)
            elif m_type == "video":
                await client.send_video(chat_id=chat_id, video=content, caption=caption)
            elif m_type == "animation":
                await client.send_animation(chat_id=chat_id, animation=content, caption=caption)
            elif m_type == "voice":
                await client.send_voice(chat_id=chat_id, voice=content, caption=caption)
            elif m_type == "document":
                await client.send_document(chat_id=chat_id, document=content, caption=caption)
            else:
                await client.send_message(chat_id=chat_id, text=content, disable_web_page_preview=False)
            break
