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

BANNER_URL = "https://files.catbox.moe/e6qgut.png"

# In-memory storage for clean command settings
CLEAN_DATA = {}

CLEAN_HELP_TEXT = (
    "**Clean Commands**\n\n"
    "Keep your chat clean by cleaning up commands from both users and admins!\n\n"
    "This module allows you to delete certain command categories, for both users and admins, to ensure your chat is kept clean. "
    "For example, you might choose to delete all user commands, this will stop users from accidentally pressing on blue text commands in other people's messages.\n\n"
    "**Available options are:**\n"
    "• `all`: Delete ALL commands sent to the group.\n"
    "• `admin`: Delete any admin-only commands sent to the group (e.g. `/ban`, `/mute` or settings changes).\n"
    "• `user`: Delete any user commands sent to the group (e.g. `/id`, `/info`, `/ping`). These commands will also be cleaned when sent by admins.\n"
    "• `other`: Delete any commands which aren't recognized as being valid Rose commands.\n\n"
    "**Admin commands:**\n"
    "• `/cleancommand <type>`: Select which command types to delete.\n"
    "• `/keepcommand <type>`: Select which command types to stop deleting.\n"
    "• `/cleancommandtypes`: List the different command types which can be cleaned.\n\n"
    "**Examples:**\n"
    "• Delete all commands, but still respond to them:\n"
    "  `/cleancommand all`\n\n"
    "• Delete all users commands (but still respond), as well as unknown commands:\n"
    "  `/cleancommand user other`\n\n"
    "• Stop deleting all commands:\n"
    "  `/keepcommand all`"
)

CLEAN_CMDS = ["cleancommand", "keepcommand", "cleancommandtypes"]

def get_chat_clean_config(chat_id: int):
    if chat_id not in CLEAN_DATA:
        CLEAN_DATA[chat_id] = {
            "all": False,
            "admin": False,
            "user": False,
            "other": False
        }
    return CLEAN_DATA[chat_id]

async def is_user_admin(client: Client, message: Message) -> bool:
    if message.chat.type.name == "PRIVATE":
        return False
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

# Custom Filter for command messages
async def is_any_command(_, __, message: Message) -> bool:
    text = message.text or message.caption
    if text and text.startswith(("/", "!", ".")):
        return True
    return False

# --- PM RESTRICTION HANDLER ---
@Client.on_message(filters.command(CLEAN_CMDS) & filters.private)
async def clean_pm_handler(client: Client, message: Message):
    await message.reply_text("❌ This command can only be used in groups.")

# --- INLINE HELP CALLBACK HANDLER (MATCHES BOTH PATTERNS) ---
@Client.on_callback_query(filters.regex(r"^help_clean(Cmds|commands)$"))
async def help_cleancommands_menu(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{CLEAN_HELP_TEXT}\n[\u200b]({BANNER_URL})"
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

@Client.on_message(filters.command("cleancommand") & filters.group)
async def cleancommand_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/cleancommand <type>`\nAvailable types: `all`, `admin`, `user`, `other`")

    cfg = get_chat_clean_config(message.chat.id)
    updated = []
    
    for opt in args:
        opt = opt.lower()
        if opt == "all":
            cfg["all"] = True
            cfg["admin"] = True
            cfg["user"] = True
            cfg["other"] = True
            updated.append("all")
        elif opt in ["admin", "user", "other"]:
            cfg[opt] = True
            updated.append(opt)

    if updated:
        await message.reply_text(f"✅ Enabled clean command for types: `{', '.join(updated)}`")
    else:
        await message.reply_text("❌ Invalid type specified! Use `all`, `admin`, `user`, or `other`.")

@Client.on_message(filters.command("keepcommand") & filters.group)
async def keepcommand_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/keepcommand <type>`\nAvailable types: `all`, `admin`, `user`, `other`")

    cfg = get_chat_clean_config(message.chat.id)
    updated = []

    for opt in args:
        opt = opt.lower()
        if opt == "all":
            cfg["all"] = False
            cfg["admin"] = False
            cfg["user"] = False
            cfg["other"] = False
            updated.append("all")
        elif opt in ["admin", "user", "other"]:
            cfg[opt] = False
            cfg["all"] = False
            updated.append(opt)

    if updated:
        await message.reply_text(f"✅ Disabled clean command for types: `{', '.join(updated)}`")
    else:
        await message.reply_text("❌ Invalid type specified! Use `all`, `admin`, `user`, or `other`.")

@Client.on_message(filters.command("cleancommandtypes") & filters.group)
async def cleancommandtypes_cmd(client: Client, message: Message):
    cfg = get_chat_clean_config(message.chat.id)
    
    res = (
        f"**Clean Command Status in {message.chat.title}:**\n\n"
        f"• **All Commands (`all`):** `{cfg['all']}`\n"
        f"• **Admin Commands (`admin`):** `{cfg['admin']}`\n"
        f"• **User Commands (`user`):** `{cfg['user']}`\n"
        f"• **Other Commands (`other`):** `{cfg['other']}`"
    )
    await message.reply_text(res)

# --- AUTO-CLEANUP ENFORCEMENT LISTENER ---
@Client.on_message(filters.group & filters.create(is_any_command), group=11)
async def cleancommand_autoclean(client: Client, message: Message):
    cfg = get_chat_clean_config(message.chat.id)
    
    if not any(cfg.values()):
        return

    is_admin = await is_user_admin(client, message)
    should_delete = False

    if cfg["all"]:
        should_delete = True
    elif is_admin and cfg["admin"]:
        should_delete = True
    elif not is_admin and cfg["user"]:
        should_delete = True

    if should_delete:
        try:
            await message.delete()
        except RPCError:
            pass
