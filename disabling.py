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

BANNER_URL = "https://files.catbox.moe/1cfasf.png"

# In-memory storage for Disabling system per chat
# Format: DISABLE_DATA[chat_id] = {"disabled_cmds": set(), "del_disabled": False, "disable_admin": False}
DISABLE_DATA = {}

# List of all commands that can be disabled
DISABLEABLE_COMMANDS = [
    "info", "id", "ping", "staff", "rules", "notes", "filters", 
    "locks", "warnings", "approval", "captcha", "cleancommand"
]

DISABLING_HELP_TEXT = (
    "**⚡ Disabling System (Advanced Module)**\n\n"
    "Control your chat's ecosystem! Disable specific commands to prevent spam, blue-texting, and unauthorized usage within your supergroup.\n\n"
    "**👑 Admin Commands:**\n"
    "• /disable [cmd]: Stop users from using specified command in this group.\n"
    "• /enable [cmd]: Re-allow users to use specified command.\n"
    "• /disableable: List all available commands that can be disabled.\n"
    "• /disabled: View all currently disabled commands in this chat.\n"
    "• /disabledel [yes/no/on/off]: Auto-delete disabled command messages sent by non-admins.\n"
    "• /disableadmin [yes/no/on/off]: Enforce command restrictions on group admins as well.\n\n"
    "**💡 Pro Examples:**\n"
    "• Disable user info command:\n"
    "  /disable info\n\n"
    "• Re-enable user info command:\n"
    "  /enable info\n\n"
    "• Disable ALL supported commands:\n"
    "  /disable all\n\n"
    "• Auto-delete disabled commands:\n"
    "  /disabledel on\n\n"
    "• Apply command blocks on Admins too:\n"
    "  /disableadmin on\n\n"
    "**Note:** By default, command disabling applies only to non-admins unless /disableadmin is toggled ON."
)

DISABLE_CMDS = ["disable", "enable", "disableable", "disabled", "disabledel", "disableadmin"]

def get_chat_disable_config(chat_id: int):
    if chat_id not in DISABLE_DATA:
        DISABLE_DATA[chat_id] = {
            "disabled_cmds": set(),
            "del_disabled": False,
            "disable_admin": False
        }
    return DISABLE_DATA[chat_id]

async def is_user_admin(client: Client, message: Message) -> bool:
    if message.chat.type.name == "PRIVATE":
        return False
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

# --- PM RESTRICTION HANDLER ---
@Client.on_message(filters.command(DISABLE_CMDS) & filters.private)
async def disable_pm_restriction(client: Client, message: Message):
    await message.reply_text("❌ This command can only be used in groups.")

# --- INLINE HELP CALLBACK HANDLER ---
@Client.on_callback_query(filters.regex(r"^help_disabling$"))
async def help_disabling_menu(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{DISABLING_HELP_TEXT}\n[\u200b]({BANNER_URL})"
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass
    await callback.answer()

# --- ADMIN SETUP COMMANDS ---

@Client.on_message(filters.command("disable") & filters.group)
async def disable_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: /disable [command_name / all]")

    target = args[0].lower().lstrip("/")
    cfg = get_chat_disable_config(message.chat.id)

    if target == "all":
        cfg["disabled_cmds"] = set(DISABLEABLE_COMMANDS)
        return await message.reply_text("✅ **All** disableable commands have been disabled in this chat.")

    if target not in DISABLEABLE_COMMANDS:
        return await message.reply_text(f"❌ `{target}` is not a valid disableable command!\nUse /disableable to see the list.")

    cfg["disabled_cmds"].add(target)
    await message.reply_text(f"✅ Disabled command `/{target}` in this chat.")

@Client.on_message(filters.command("enable") & filters.group)
async def enable_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: /enable [command_name / all]")

    target = args[0].lower().lstrip("/")
    cfg = get_chat_disable_config(message.chat.id)

    if target == "all":
        cfg["disabled_cmds"].clear()
        return await message.reply_text("✅ All commands have been re-enabled in this chat.")

    if target in cfg["disabled_cmds"]:
        cfg["disabled_cmds"].remove(target)
        await message.reply_text(f"✅ Re-enabled command `/{target}`.")
    else:
        await message.reply_text(f"ℹ️ Command `/{target}` is not currently disabled.")

@Client.on_message(filters.command("disableable") & filters.group)
async def disableable_cmd(client: Client, message: Message):
    cmds_formatted = ", ".join([f"`/{cmd}`" for cmd in DISABLEABLE_COMMANDS])
    text = (
        "**Available Disableable Commands:**\n\n"
        f"{cmds_formatted}\n\n"
        "You can disable any of these commands using `/disable [command]`."
    )
    await message.reply_text(text)

@Client.on_message(filters.command("disabled") & filters.group)
async def disabled_list_cmd(client: Client, message: Message):
    cfg = get_chat_disable_config(message.chat.id)
    disabled = cfg["disabled_cmds"]

    if not disabled:
        return await message.reply_text("ℹ️ No commands are currently disabled in this chat.")

    cmds_formatted = "\n".join([f"• `/{cmd}`" for cmd in sorted(disabled)])
    text = (
        f"**Disabled Commands in {message.chat.title}:**\n\n"
        f"{cmds_formatted}\n\n"
        f"• **Auto-Delete Enabled:** `{cfg['del_disabled']}`\n"
        f"• **Disabled For Admins:** `{cfg['disable_admin']}`"
    )
    await message.reply_text(text)

@Client.on_message(filters.command("disabledel") & filters.group)
async def disabledel_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.command[1:]
    cfg = get_chat_disable_config(message.chat.id)

    if not args:
        status = "ON" if cfg["del_disabled"] else "OFF"
        return await message.reply_text(f"ℹ️ Auto-deletion of disabled commands is currently **{status}**.")

    val = args[0].lower()
    if val in ["yes", "on", "true"]:
        cfg["del_disabled"] = True
        await message.reply_text("✅ Disabled command auto-deletion is now **ENABLED**.")
    elif val in ["no", "off", "false"]:
        cfg["del_disabled"] = False
        await message.reply_text("✅ Disabled command auto-deletion is now **DISABLED**.")
    else:
        await message.reply_text("Usage: /disabledel [yes/no/on/off]")

@Client.on_message(filters.command("disableadmin") & filters.group)
async def disableadmin_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.command[1:]
    cfg = get_chat_disable_config(message.chat.id)

    if not args:
        status = "ON" if cfg["disable_admin"] else "OFF"
        return await message.reply_text(f"ℹ️ Enforcing disabled commands on Admins is currently **{status}**.")

    val = args[0].lower()
    if val in ["yes", "on", "true"]:
        cfg["disable_admin"] = True
        await message.reply_text("✅ Disabled commands are now enforced on **Admins as well**.")
    elif val in ["no", "off", "false"]:
        cfg["disable_admin"] = False
        await message.reply_text("✅ Disabled commands will now **only apply to Non-Admins**.")
    else:
        await message.reply_text("Usage: /disableadmin [yes/no/on/off]")

# --- AUTO-ENFORCEMENT INTERCEPTOR LISTENER ---
@Client.on_message(filters.group & ~filters.service, group=9)
async def check_disabled_commands_enforcer(client: Client, message: Message):
    if not message.text or not message.text.startswith(("/", "!", ".")):
        return

    cfg = get_chat_disable_config(message.chat.id)
    if not cfg["disabled_cmds"]:
        return

    # Extract command name
    cmd_sent = message.text.split()[0][1:].split("@")[0].lower()

    if cmd_sent in cfg["disabled_cmds"]:
        is_admin = await is_user_admin(client, message)

        # Skip if user is admin and admin restriction is OFF
        if is_admin and not cfg["disable_admin"]:
            return

        # Handle Action: Delete message if toggle ON
        if cfg["del_disabled"]:
            try:
                await message.delete()
            except RPCError:
                pass
        else:
            try:
                await message.reply_text(f"🚫 The `/{cmd_sent}` command has been disabled by admins in this chat.")
            except RPCError:
                pass
