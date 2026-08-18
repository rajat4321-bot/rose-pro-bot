import re
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from database import db

# Database Collections
antiraid_db = db["antiraid"]

# In-Memory Cache
join_tracker = {}  # {chat_id: [timestamp1, timestamp2, ...]}
active_raids = {}  # {chat_id: end_timestamp}

BANNER_URL = "https://files.catbox.moe/bsvbj2.png"

ANTIRAID_HELP_TEXT = (
    "**AntiRaid**\n\n"
    "Some people on telegram find it entertaining to \"raid\" chats. "
    "During a raid, hundreds of users join a chat to spam.\n\n"
    "The antiraid module allows you to quickly stop anyone from joining when such a raid is happening. "
    "All new joins will be temporarily banned for the next few hours, allowing you to wait out the spam attack until the trolls stop.\n\n"
    "**Admin commands:**\n"
    "• /antiraid <optional time/off/no>: Toggle antiraid. All new joins will be temporarily banned for the next few hours.\n"
    "• /raidtime <time>: View or set the desired antiraid duration. Default 6h.\n"
    "• /lockdowntime <time>: View or set the time for antiraid to tempban users for. Default 1h.\n"
    "• /autoantiraid <number/off/no>: Set the number of joins per minute after which to enable automatic antiraid. Set to '0', 'off', or 'no' to disable.\n\n"
    "**Examples:**\n"
    "• Enable antiraid for 3 hours:\n"
    "`/antiraid 3h`\n\n"
    "• Disable antiraid:\n"
    "`/antiraid off`\n\n"
    "• Automatically enable antiraid if over 15 users join in under a minute:\n"
    "`/autoantiraid 15`\n\n"
    "• Disable automatic antiraid:\n"
    "`/autoantiraid off`"
)

def parse_time(time_str: str) -> int:
    """Parses time strings like 30m, 3h, 1d into seconds."""
    time_str = time_str.lower().strip()
    match = re.match(r"^(\d+)([smhd])?$", time_str)
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    if unit == 's': return value
    if unit == 'm': return value * 60
    if unit == 'h': return value * 3600
    if unit == 'd': return value * 86400
    return value * 3600

async def is_user_admin(client: Client, message: Message) -> bool:
    if message.chat.type.name == "PRIVATE":
        return False
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

# --- Inline Callback Handler ---
@Client.on_callback_query(filters.regex("^help_antiraid$"))
async def help_antiraid_menu(client: Client, callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="help_back")]])
    full_text = f"{ANTIRAID_HELP_TEXT}\n[\u200b]({BANNER_URL})"
    
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass

# --- PM Restrictions ---
@Client.on_message(filters.command(["antiraid", "raidtime", "lockdowntime", "autoantiraid"]) & filters.private)
async def antiraid_pm_handler(client: Client, message: Message):
    await message.reply_text("❌ This command can only be used in groups.")

# --- Real-Time Join Enforcer ---
@Client.on_message(filters.group & filters.new_chat_members, group=11)
async def antiraid_join_enforcer(client: Client, message: Message):
    chat_id = message.chat.id
    now = time.time()
    
    settings = await antiraid_db.find_one({"chat_id": chat_id}) or {}
    raid_duration = settings.get("raidtime", 21600)      # Default 6h
    lockdown_duration = settings.get("lockdowntime", 3600) # Default 1h
    auto_limit = settings.get("autoantiraid", 0)

    # Auto-AntiRaid Rate Tracker
    if auto_limit > 0:
        if chat_id not in join_tracker:
            join_tracker[chat_id] = []
        
        # Keep track of joins within 60 seconds
        join_tracker[chat_id] = [t for t in join_tracker[chat_id] if now - t <= 60]
        join_tracker[chat_id].append(now)

        if len(join_tracker[chat_id]) >= auto_limit and active_raids.get(chat_id, 0) < now:
            active_raids[chat_id] = now + raid_duration
            await message.reply_text(
                f"🚨 **Auto-AntiRaid Activated!** More than `{auto_limit}` users joined in under a minute.\n"
                f"New joins will be temporarily banned for `{lockdown_duration // 3600}h`."
            )

    # Temporary Ban logic during active raid
    if active_raids.get(chat_id, 0) > now:
        for user in message.new_chat_members:
            if user.is_self:
                continue
            try:
                until = datetime.now() + timedelta(seconds=lockdown_duration)
                await client.ban_chat_member(chat_id, user.id, until_date=until)
            except RPCError:
                pass

# --- Admin Commands ---

@Client.on_message(filters.command("antiraid") & filters.group)
async def antiraid_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    chat_id = message.chat.id
    now = time.time()
    settings = await antiraid_db.find_one({"chat_id": chat_id}) or {}
    default_raidtime = settings.get("raidtime", 21600)
    is_currently_active = active_raids.get(chat_id, 0) > now

    if len(message.command) < 2:
        status = f"ON (active for {int((active_raids[chat_id] - now)//60)} mins)" if is_currently_active else "OFF"
        return await message.reply_text(f"AntiRaid status in **{message.chat.title}**: `{status}`")

    arg = message.command[1].lower()
    if arg in ["off", "no", "disable"]:
        if not is_currently_active:
            return await message.reply_text("❌ AntiRaid is already disabled!")
        active_raids[chat_id] = 0
        await message.reply_text("✅ AntiRaid disabled.")
    else:
        parsed = parse_time(arg)
        duration = parsed if parsed else default_raidtime
        
        # Check if already enabled with exact same active state
        if is_currently_active:
            remaining_mins = int((active_raids[chat_id] - now) // 60)
            if remaining_mins == (duration // 60):
                return await message.reply_text(f"❌ AntiRaid is already enabled for `{remaining_mins}` minutes!")

        active_raids[chat_id] = now + duration
        mins = duration // 60
        await message.reply_text(f"🚨 **AntiRaid Enabled** for `{mins}` minutes. All new joins will be temporarily banned.")

@Client.on_message(filters.command("raidtime") & filters.group)
async def raidtime_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    chat_id = message.chat.id
    settings = await antiraid_db.find_one({"chat_id": chat_id}) or {}
    current_time = settings.get("raidtime", 21600)

    if len(message.command) < 2:
        val = current_time // 3600
        return await message.reply_text(f"Current AntiRaid active duration is `{val}h`.")

    seconds = parse_time(message.command[1])
    if not seconds:
        return await message.reply_text("Invalid duration format. Example: `/raidtime 6h` or `/raidtime 30m`")

    if current_time == seconds:
        return await message.reply_text(f"❌ AntiRaid duration is already set to `{seconds // 60}` minutes!")

    await antiraid_db.update_one({"chat_id": chat_id}, {"$set": {"raidtime": seconds}}, upsert=True)
    await message.reply_text(f"✅ AntiRaid duration set to `{seconds // 60}` minutes.")

@Client.on_message(filters.command("lockdowntime") & filters.group)
async def lockdowntime_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    chat_id = message.chat.id
    settings = await antiraid_db.find_one({"chat_id": chat_id}) or {}
    current_lockdown = settings.get("lockdowntime", 3600)

    if len(message.command) < 2:
        val = current_lockdown // 3600
        return await message.reply_text(f"Current lockdown ban duration for new joins is `{val}h`.")

    seconds = parse_time(message.command[1])
    if not seconds:
        return await message.reply_text("Invalid duration format. Example: `/lockdowntime 1h` or `/lockdowntime 30m`")

    if current_lockdown == seconds:
        return await message.reply_text(f"❌ Lockdown ban time is already set to `{seconds // 60}` minutes!")

    await antiraid_db.update_one({"chat_id": chat_id}, {"$set": {"lockdowntime": seconds}}, upsert=True)
    await message.reply_text(f"✅ Lockdown ban time set to `{seconds // 60}` minutes.")

@Client.on_message(filters.command("autoantiraid") & filters.group)
async def autoantiraid_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    chat_id = message.chat.id
    settings = await antiraid_db.find_one({"chat_id": chat_id}) or {}
    current_limit = settings.get("autoantiraid", 0)

    if len(message.command) < 2:
        status = f"`{current_limit}` joins/min" if current_limit > 0 else "`Disabled`"
        return await message.reply_text(f"Current Auto-AntiRaid trigger limit is {status}.")

    arg = message.command[1].lower()
    if arg in ["off", "no", "0"]:
        if current_limit == 0:
            return await message.reply_text("❌ Auto-AntiRaid is already disabled!")
        await antiraid_db.update_one({"chat_id": chat_id}, {"$set": {"autoantiraid": 0}}, upsert=True)
        await message.reply_text("✅ Auto-AntiRaid disabled.")
    else:
        try:
            limit = int(arg)
            if current_limit == limit:
                return await message.reply_text(f"❌ Auto-AntiRaid limit is already set to `{limit}` joins per minute!")
            await antiraid_db.update_one({"chat_id": chat_id}, {"$set": {"autoantiraid": limit}}, upsert=True)
            await message.reply_text(f"✅ Auto-AntiRaid will trigger if over `{limit}` users join within 1 minute.")
        except ValueError:
            await message.reply_text("Please specify a valid number or 'off'.")
