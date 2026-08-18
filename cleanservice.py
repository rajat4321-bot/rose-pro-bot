import re
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError

BANNER_URL = "https://files.catbox.moe/vuaytm.png"

# In-memory storage for clean service settings per group
# Categories: all, join, leave, other, photo, pin, title, videochat
CLEAN_SERVICE_DATA = {}

CLEAN_SERVICE_HELP_TEXT = (
    "**Clean Service**\n\n"
    "Clean up automated Telegram service messages! The available categories are:\n"
    "• `all`: All service messages.\n"
    "• `join`: When a new user joins, or is added. eg: 'X joined the chat'.\n"
    "• `leave`: When a user leaves, or is removed. eg: 'X left the chat'.\n"
    "• `other`: Miscellaneous items; such as chat boosts, successful telegram payments, proximity alerts, webapp messages, message auto deletion changes, or checklist updates.\n"
    "• `photo`: When chat photos or chat backgrounds are changed.\n"
    "• `pin`: When a new message is pinned. eg: 'X pinned a message'.\n"
    "• `title`: When chat or topic titles are changed.\n"
    "• `videochat`: When a video chat action occurs - eg starting, ending, scheduling, or adding members to the call.\n\n"
    "**Admin commands:**\n"
    "• `/cleanservice <type> [yes/no/on/off]`: Select which service messages to delete.\n"
    "• `/keepservice <type>`: Select which service messages to stop deleting.\n"
    "• `/nocleanservice <type>`: (same as keepservice)\n"
    "• `/cleanservicetypes`: List all the available service messages, with a brief explanation.\n\n"
    "**Examples:**\n"
    "• Stop all Telegram service messages:\n"
    "  `/cleanservice all`\n\n"
    "• Stop Telegram's 'X joined the chat' messages:\n"
    "  `/cleanservice join`\n\n"
    "• Keep Telegram's 'X pinned a message' messages:\n"
    "  `/keepservice pin`"
)

SERVICE_CMDS = ["cleanservice", "keepservice", "nocleanservice", "cleanservicetypes"]
VALID_TYPES = ["all", "join", "leave", "other", "photo", "pin", "title", "videochat"]

def get_chat_service_config(chat_id: int):
    if chat_id not in CLEAN_SERVICE_DATA:
        CLEAN_SERVICE_DATA[chat_id] = {t: False for t in VALID_TYPES}
    return CLEAN_SERVICE_DATA[chat_id]

async def is_user_admin(client: Client, message: Message) -> bool:
    if message.chat.type.name == "PRIVATE":
        return False
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

# --- PM RESTRICTION HANDLER ---
@Client.on_message(filters.command(SERVICE_CMDS) & filters.private)
async def clean_service_pm_handler(client: Client, message: Message):
    await message.reply_text("❌ This command can only be used in groups.")

# --- INLINE HELP CALLBACK HANDLER (MATCHES BOTH PATTERNS) ---
@Client.on_callback_query(filters.regex(r"^help_clean(Service|service)$"))
async def help_cleanservice_menu(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{CLEAN_SERVICE_HELP_TEXT}\n[\u200b]({BANNER_URL})"
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass
    await callback.answer()

# --- COMMAND HANDLERS ---

@Client.on_message(filters.command("cleanservice") & filters.group)
async def cleanservice_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/cleanservice <type> [yes/no/on/off]`\nAvailable types: `all`, `join`, `leave`, `other`, `photo`, `pin`, `title`, `videochat`")

    stype = args[0].lower()
    turn_on = True

    if len(args) >= 2:
        val = args[1].lower()
        if val in ["no", "off", "false"]:
            turn_on = False

    cfg = get_chat_service_config(message.chat.id)

    if stype == "all":
        for k in cfg:
            cfg[k] = turn_on
        status_str = "enabled" if turn_on else "disabled"
        await message.reply_text(f"✅ Clean service for **ALL** service messages is now `{status_str}`.")
    elif stype in VALID_TYPES:
        cfg[stype] = turn_on
        status_str = "enabled" if turn_on else "disabled"
        await message.reply_text(f"✅ Clean service for `{stype}` is now `{status_str}`.")
    else:
        await message.reply_text(f"❌ Invalid type specified! Valid types are:\n`{', '.join(VALID_TYPES)}`")

@Client.on_message(filters.command(["keepservice", "nocleanservice"]) & filters.group)
async def keepservice_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/keepservice <type>` or `/nocleanservice <type>`")

    stype = args[0].lower()
    cfg = get_chat_service_config(message.chat.id)

    if stype == "all":
        for k in cfg:
            cfg[k] = False
        await message.reply_text("✅ Disabled clean service for **ALL** service messages.")
    elif stype in VALID_TYPES:
        cfg[stype] = False
        await message.reply_text(f"✅ Stopped cleaning service messages for `{stype}`.")
    else:
        await message.reply_text(f"❌ Invalid type specified! Valid types are:\n`{', '.join(VALID_TYPES)}`")

@Client.on_message(filters.command("cleanservicetypes") & filters.group)
async def cleanservicetypes_cmd(client: Client, message: Message):
    cfg = get_chat_service_config(message.chat.id)
    
    res = f"**Clean Service Types Status in {message.chat.title}:**\n\n"
    for stype in VALID_TYPES:
        status = "ON" if cfg[stype] else "OFF"
        res += f"• `{stype}`: `{status}`\n"
    
    await message.reply_text(res)

# --- AUTO-CLEANUP SERVICE ENFORCEMENT LISTENER ---
@Client.on_message(filters.group & filters.service, group=12)
async def cleanservice_autoclean(client: Client, message: Message):
    cfg = get_chat_service_config(message.chat.id)
    
    # Skip if no clean service settings are enabled
    if not any(cfg.values()):
        return

    should_delete = False

    if cfg["all"]:
        should_delete = True
    else:
        # Check specific service types
        if cfg["join"] and (message.new_chat_members or message.group_chat_created or message.supergroup_chat_created):
            should_delete = True
        elif cfg["leave"] and message.left_chat_member:
            should_delete = True
        elif cfg["photo"] and (message.new_chat_photo or message.delete_chat_photo):
            should_delete = True
        elif cfg["pin"] and message.pinned_message:
            should_delete = True
        elif cfg["title"] and message.new_chat_title:
            should_delete = True
        elif cfg["videochat"] and (message.video_chat_started or message.video_chat_ended or message.video_chat_participants_invited or message.video_chat_scheduled):
            should_delete = True
        elif cfg["other"]:
            # Miscellaneous service triggers
            if not any([
                message.new_chat_members, message.left_chat_member,
                message.new_chat_photo, message.delete_chat_photo,
                message.pinned_message, message.new_chat_title,
                message.video_chat_started, message.video_chat_ended,
                message.video_chat_participants_invited, message.video_chat_scheduled
            ]):
                should_delete = True

    if should_delete:
        try:
            await message.delete()
        except RPCError:
            pass
