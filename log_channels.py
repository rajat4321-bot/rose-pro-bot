from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- DEDICATED BANNER IMAGE URL ---
BANNER_LOG_CHANNELS = "https://files.catbox.moe/m5g5bi.png"

# --- IN-MEMORY DATABASE FOR LOG CHANNELS ---
LOGS_DB = {}

SUPPORTED_LOG_CATEGORIES = ["bans", "mutes", "warns", "notes", "all"]

# --- HELP TEXT ---
LOG_CHANNELS_HELP_TEXT = (
    "**Log Channels**\n\n"
    "Recent actions are nice, but they don't help you log every action taken by the bot. "
    "This is why you need log channels!\n\n"
    "Log channels can help you keep track of exactly what the other admins are doing. "
    "Bans, Mutes, warns, notes - everything can be moderated.\n\n"
    "**Setting a log channel is done by the following steps:**\n"
    "• Add Rose to your channel, as an admin. This is done via the \"add administrators\" tab.\n"
    "• Send `/setlog` to your channel.\n"
    "• Forward the `/setlog` command to the group you wish to be logged.\n"
    "• Congrats! all done :-)\n\n"
    "**Admin commands:**\n"
    "• `/logchannel`: Get the name of the current log channel.\n"
    "• `/setlog`: Set the log channel for the current chat.\n"
    "• `/unsetlog`: Unset the log channel for the current chat.\n"
    "• `/log <category>`: Enable a log category - actions of that type will now be logged.\n"
    "• `/nolog <category>`: Disable a log category - actions of that type will no longer be logged.\n"
    "• `/logcategories`: List all support categories, with information on what they refer to."
)

# --- HELPER FUNCTION TO SEND LOGS TO CHANNEL ---

async def log_action(client: Client, chat_id: int, category: str, text: str):
    """Call this function from other modules (like ban/mute) to send logs."""
    log_data = LOGS_DB.get(chat_id)
    if not log_data or not log_data.get("channel_id"):
        return

    categories = log_data.get("categories", set())
    if "all" in categories or category in categories:
        try:
            await client.send_message(
                chat_id=log_data["channel_id"],
                text=text,
                parse_mode=enums.ParseMode.MARKDOWN
            )
        except Exception:
            pass

# --- ADMIN CHECKER ---

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

# --- INLINE CALLBACK HANDLER (MATCHES help.py DATA) ---

@Client.on_callback_query(filters.regex(r"^(help_log|help_log_channels)$"))
async def help_log_channels_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{LOG_CHANNELS_HELP_TEXT}\n[\u200b]({BANNER_LOG_CHANNELS})"
    
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

# --- COMMAND HANDLERS ---

@Client.on_message(filters.command("setlog"))
async def setlog_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.CHANNEL:
        return await message.reply_text(
            "Now forward this message to the group you want to set this log channel for!"
        )

    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an Admin to configure log channels.")

        if not message.forward_from_chat or message.forward_from_chat.type != ChatType.CHANNEL:
            return await message.reply_text("❌ Please forward the `/setlog` command from your target channel.")

        channel_id = message.forward_from_chat.id
        LOGS_DB[message.chat.id] = {
            "channel_id": channel_id,
            "categories": set(SUPPORTED_LOG_CATEGORIES)
        }
        return await message.reply_text(
            f"✅ Successfully set log channel to **{message.forward_from_chat.title}**!",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    return await message.reply_text("❌ This command must be used in a channel/group setup flow.")

@Client.on_message(filters.command("unsetlog"))
async def unsetlog_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to unset the log channel.")

    if message.chat.id in LOGS_DB:
        del LOGS_DB[message.chat.id]
        await message.reply_text("✅ Successfully unset the log channel for this group.")
    else:
        await message.reply_text("No log channel is currently set for this group.")

@Client.on_message(filters.command("logchannel"))
async def logchannel_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    log_data = LOGS_DB.get(message.chat.id)
    if not log_data or not log_data.get("channel_id"):
        return await message.reply_text("No log channel is set for this chat.")

    try:
        chat = await client.get_chat(log_data["channel_id"])
        await message.reply_text(f"The current log channel is: **{chat.title}** (`{chat.id}`)", parse_mode=enums.ParseMode.MARKDOWN)
    except Exception:
        await message.reply_text("Log channel is configured, but I can no longer access it.")

@Client.on_message(filters.command("log"))
async def enable_log_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to edit log settings.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/log <category>` (e.g., `/log bans`)", parse_mode=enums.ParseMode.MARKDOWN)

    category = args[0].lower()
    if category not in SUPPORTED_LOG_CATEGORIES:
        return await message.reply_text(f"Invalid category. Supported categories: `{', '.join(SUPPORTED_LOG_CATEGORIES)}`")

    log_data = LOGS_DB.setdefault(message.chat.id, {"channel_id": None, "categories": set()})
    log_data["categories"].add(category)
    await message.reply_text(f"✅ Enabled logging for `{category}` actions.", parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("nolog"))
async def disable_log_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to edit log settings.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/nolog <category>` (e.g., `/nolog bans`)", parse_mode=enums.ParseMode.MARKDOWN)

    category = args[0].lower()
    log_data = LOGS_DB.get(message.chat.id)

    if log_data and category in log_data["categories"]:
        log_data["categories"].remove(category)
        await message.reply_text(f"✅ Disabled logging for `{category}` actions.", parse_mode=enums.ParseMode.MARKDOWN)
    else:
        await message.reply_text(f"Category `{category}` was not being logged.", parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("logcategories"))
async def logcategories_cmd(client: Client, message: Message):
    cats_text = (
        "**Available log categories:**\n\n"
        "• `bans`: Ban and unban actions.\n"
        "• `mutes`: Mute and unmute actions.\n"
        "• `warns`: Warning and warn resetting actions.\n"
        "• `notes`: Note saving and deletion actions.\n"
        "• `all`: Enables all logging categories."
    )
    await message.reply_text(cats_text, parse_mode=enums.ParseMode.MARKDOWN)
