import re
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions
)
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError

BANNER_URL = "https://files.catbox.moe/k84w5u.png"

BANS_HELP_TEXT = (
    "**Bans**\n\n"
    "Some people need to be publicly banned; spammers, annoyances, or just trolls.\n\n"
    "This module allows you to do that easily by exposing some common actions, so everyone will see!\n\n"
    "**User commands:**\n"
    "• /kickme: Users that use this, kick themselves.\n\n"
    "**Admin commands:**\n"
    "• /ban: Ban a user.\n"
    "• /dban: Ban a user by reply, and delete their message.\n"
    "• /sban: Silently ban a user, and delete your message.\n"
    "• /tban: Temporarily ban a user. Example time values: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks.\n"
    "• /unban: Unban a user.\n"
    "• /mute: Mute a user.\n"
    "• /dmute: Mute a user by reply, and delete their message.\n"
    "• /smute: Silently mute a user, and delete your message.\n"
    "• /tmute: Temporarily mute a user. Example time values: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks.\n"
    "• /unmute: Unmute a user.\n"
    "• /kick: Kick a user.\n"
    "• /dkick: Kick a user by reply, and delete their message.\n"
    "• /skick: Silently kick a user, and delete your message.\n\n"
    "**Examples:**\n"
    "• Mute the user with username `@username` for two hours:\n"
    "  `/tmute @username 2h`\n\n"
    "• Silently ban the user with ID `1234` for two hours:\n"
    "  `/sban 1234 2h`"
)

BAN_COMMANDS = [
    "ban", "dban", "sban", "tban", "unban",
    "mute", "dmute", "smute", "tmute", "unmute",
    "kick", "dkick", "skick", "kickme"
]

def parse_time(time_str: str) -> datetime:
    time_str = time_str.lower().strip()
    match = re.match(r"^(\d+)([mhdw])?$", time_str)
    if not match:
        return None
    val, unit = match.groups()
    val = int(val)
    if unit == 'm':
        return datetime.now() + timedelta(minutes=val)
    elif unit == 'h':
        return datetime.now() + timedelta(hours=val)
    elif unit == 'd':
        return datetime.now() + timedelta(days=val)
    elif unit == 'w':
        return datetime.now() + timedelta(weeks=val)
    else:
        return datetime.now() + timedelta(hours=val)

async def is_user_admin(client: Client, message: Message) -> bool:
    if message.chat.type.name == "PRIVATE":
        return False
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

# Robust User Extraction (Reply, Username, or User ID)
async def extract_user(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        return user.id, user.first_name, user.mention
    
    args = message.text.split(maxsplit=2) if message.text else []
    if len(args) > 1:
        target = args[1]
        if target.isdigit():
            user_id = int(target)
            try:
                user = await client.get_users(user_id)
                return user.id, user.first_name, user.mention
            except Exception:
                return user_id, str(user_id), f"[User](tg://user?id={user_id})"
        elif target.startswith("@"):
            try:
                user = await client.get_users(target)
                return user.id, user.first_name, user.mention
            except Exception:
                return None, None, None
    return None, None, None

# Inline Callback Handler for Help Menu
@Client.on_callback_query(filters.regex("^help_bans$"))
async def help_bans_menu(client: Client, callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="help_back")]])
    full_text = f"{BANS_HELP_TEXT}\n[\u200b]({BANNER_URL})"
    
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass

# PM Restriction Handler
@Client.on_message(filters.command(BAN_COMMANDS) & filters.private)
async def bans_pm_handler(client: Client, message: Message):
    await message.reply_text("❌ This command can only be used in groups.")

# USER COMMAND: /kickme
@Client.on_message(filters.command("kickme") & filters.group)
async def kickme_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if await is_user_admin(client, message):
        return await message.reply_text("❌ You are an admin! You cannot kick yourself.")
    
    try:
        await client.ban_chat_member(message.chat.id, user_id)
        await client.unban_chat_member(message.chat.id, user_id)
        await message.reply_text(f"👢 {message.from_user.mention} has kicked themselves out!")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to kick you: {e}")

# ADMIN COMMANDS: /ban, /dban, /sban, /tban
@Client.on_message(filters.command(["ban", "dban", "sban", "tban"]) & filters.group)
async def ban_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    user_id, first_name, mention = await extract_user(client, message)
    if not user_id:
        return await message.reply_text("You need to specify a user to ban - by reply or username/ID.")

    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await message.reply_text("❌ You cannot ban another admin!")
        if member.status == ChatMemberStatus.BANNED:
            return await message.reply_text(f"❌ {mention} is already banned!")
    except Exception:
        pass

    cmd = message.command[0].lower()
    until_date = None

    if cmd == "tban":
        args = message.text.split(maxsplit=2)
        time_arg = None
        if message.reply_to_message and len(args) > 1:
            time_arg = args[1]
        elif len(args) > 2:
            time_arg = args[2]

        if not time_arg:
            return await message.reply_text("Usage: `/tban @username 2h` or reply with `/tban 2h`")
            
        until_date = parse_time(time_arg)
        if not until_date:
            return await message.reply_text("❌ Invalid time format! Use values like `4m`, `3h`, `6d`, or `5w`.")

    try:
        if until_date:
            await client.ban_chat_member(message.chat.id, user_id, until_date=until_date)
        else:
            await client.ban_chat_member(message.chat.id, user_id)
        
        if cmd == "dban" and message.reply_to_message:
            await message.reply_to_message.delete()
        if cmd == "sban":
            await message.delete()
            return
            
        if cmd == "tban":
            await message.reply_text(f"⏳ Banned {mention} temporarily until `{until_date.strftime('%Y-%m-%d %H:%M:%S')}`.")
        else:
            await message.reply_text(f"🚫 Banned {mention}!")
    except RPCError as e:
        await message.reply_text(f"❌ Action failed: {e}")

# ADMIN COMMAND: /unban
@Client.on_message(filters.command("unban") & filters.group)
async def unban_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    user_id, first_name, mention = await extract_user(client, message)
    if not user_id:
        return await message.reply_text("You need to specify a user to unban - by reply or username/ID.")

    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status not in [ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
            return await message.reply_text(f"❌ {mention} is not banned or restricted!")
    except Exception:
        pass

    try:
        await client.unban_chat_member(message.chat.id, user_id)
        await message.reply_text(f"✅ Unbanned {mention}!")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to unban: {e}")

# ADMIN COMMANDS: /mute, /dmute, /smute, /tmute
@Client.on_message(filters.command(["mute", "dmute", "smute", "tmute"]) & filters.group)
async def mute_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    user_id, first_name, mention = await extract_user(client, message)
    if not user_id:
        return await message.reply_text("You need to specify a user to mute - by reply or username/ID.")

    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await message.reply_text("❌ You cannot mute another admin!")
        if member.status == ChatMemberStatus.RESTRICTED and not member.permissions.can_send_messages:
            return await message.reply_text(f"❌ {mention} is already muted!")
    except Exception:
        pass

    cmd = message.command[0].lower()
    until_date = None

    if cmd == "tmute":
        args = message.text.split(maxsplit=2)
        time_arg = None
        if message.reply_to_message and len(args) > 1:
            time_arg = args[1]
        elif len(args) > 2:
            time_arg = args[2]

        if not time_arg:
            return await message.reply_text("Usage: `/tmute @username 2h` or reply with `/tmute 2h`")

        until_date = parse_time(time_arg)
        if not until_date:
            return await message.reply_text("❌ Invalid time format! Use values like `4m`, `3h`, `6d`, or `5w`.")

    try:
        if until_date:
            await client.restrict_chat_member(
                message.chat.id,
                user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
        else:
            await client.restrict_chat_member(
                message.chat.id,
                user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )

        if cmd == "dmute" and message.reply_to_message:
            await message.reply_to_message.delete()
        if cmd == "smute":
            await message.delete()
            return

        if cmd == "tmute":
            await message.reply_text(f"⏳ Muted {mention} temporarily until `{until_date.strftime('%Y-%m-%d %H:%M:%S')}`.")
        else:
            await message.reply_text(f"🔇 Muted {mention}!")
    except RPCError as e:
        await message.reply_text(f"❌ Action failed: {e}")

# ADMIN COMMAND: /unmute
@Client.on_message(filters.command("unmute") & filters.group)
async def unmute_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    user_id, first_name, mention = await extract_user(client, message)
    if not user_id:
        return await message.reply_text("You need to specify a user to unmute - by reply or username/ID.")

    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status == ChatMemberStatus.RESTRICTED and member.permissions.can_send_messages:
            return await message.reply_text(f"❌ {mention} is already unmuted!")
    except Exception:
        pass

    try:
        await client.restrict_chat_member(
            message.chat.id,
            user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await message.reply_text(f"🔊 Unmuted {mention}!")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to unmute: {e}")

# ADMIN COMMANDS: /kick, /dkick, /skick
@Client.on_message(filters.command(["kick", "dkick", "skick"]) & filters.group)
async def kick_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    user_id, first_name, mention = await extract_user(client, message)
    if not user_id:
        return await message.reply_text("You need to specify a user to kick - by reply or username/ID.")

    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await message.reply_text("❌ You cannot kick another admin!")
    except Exception:
        pass

    cmd = message.command[0].lower()

    try:
        await client.ban_chat_member(message.chat.id, user_id)
        await client.unban_chat_member(message.chat.id, user_id)

        if cmd == "dkick" and message.reply_to_message:
            await message.reply_to_message.delete()
        if cmd == "skick":
            await message.delete()
            return

        await message.reply_text(f"👢 Kicked {mention}!")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to kick: {e}")
