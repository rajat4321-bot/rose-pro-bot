from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError
from database import db

antiflood_db = db["antiflood"]
flood_cache = {}

BANNER_URL = "https://files.catbox.moe/pym6sl.png"

ANTIFLOOD_HELP = (
    "**Antiflood**\n\n"
    "You know how sometimes, people join, send 100 messages, and ruin your chat? With antiflood, that happens no more!\n\n"
    "Antiflood allows you to take action on users that send more than X messages in a row. Actions are: ban/mute/kick/tban/tmute.\n\n"
    "**Admin commands:**\n"
    "• /flood: Get the current antiflood settings.\n"
    "• /setflood <number/off/no>: Get the number of consecutive messages to trigger antiflood. Set to '0', 'off', or 'no' to disable.\n"
    "• /floodtimer <count> <duration>: Set the number of messages and time required for timed antiflood. Set to 'just off' or 'no' to disable.\n"
    "• /floodmode <action type>: Choose which action to take on a user who has been flooding. Possible actions: ban/mute/kick/tban/tmute\n"
    "• /clearflood <yes/no/on/off>: Whether to delete the messages that triggered the flood.\n"
)

async def is_user_admin(client: Client, message: Message) -> bool:
    if message.chat.type.name == "PRIVATE":
        return False
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

@Client.on_callback_query(filters.regex("^help_antiflood$"))
async def help_antiflood_menu(client: Client, callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="help_back")]])
    await callback.message.edit_text(
        text=f"{ANTIFLOOD_HELP}\n[\u200b]({BANNER_URL})",
        reply_markup=keyboard,
        disable_web_page_preview=False
    )

@Client.on_message(filters.command(["flood", "setflood", "floodmode", "clearflood", "floodtimer"]) & filters.private)
async def antiflood_pm_handler(client: Client, message: Message):
    await message.reply_text("❌ This command can only be used in groups.")

# --- Real-Time Flood Listener ---
@Client.on_message(filters.group & ~filters.service & ~filters.bot, group=10)
async def antiflood_enforcer(client: Client, message: Message):
    if not message.from_user or message.from_user.is_self:
        return
    
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Skip checking for admins/owners
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return
    except Exception:
        pass

    settings = await antiflood_db.find_one({"chat_id": chat_id})
    limit = settings.get("limit", 0) if settings else 0
    if limit <= 0:
        return

    if chat_id not in flood_cache:
        flood_cache[chat_id] = {}
    if user_id not in flood_cache[chat_id]:
        flood_cache[chat_id][user_id] = 0
    
    flood_cache[chat_id][user_id] += 1
    count = flood_cache[chat_id][user_id]
    
    if count >= limit:
        mode = settings.get("mode", "ban") if settings else "ban"
        flood_cache[chat_id][user_id] = 0
        
        try:
            if mode == "ban":
                await client.ban_chat_member(chat_id, user_id)
                await message.reply_text(f"🚫 {message.from_user.mention} was banned for flooding.")
            elif mode == "mute":
                await client.restrict_chat_member(
                    chat_id, 
                    user_id, 
                    permissions=ChatPermissions(can_send_messages=False)
                )
                await message.reply_text(f"🔇 {message.from_user.mention} was muted for flooding.")
            elif mode == "kick":
                await client.ban_chat_member(chat_id, user_id)
                await client.unban_chat_member(chat_id, user_id)
                await message.reply_text(f"👢 {message.from_user.mention} was kicked for flooding.")
        except RPCError as e:
            await message.reply_text(f"❌ Failed to take action: {e.MESSAGE}")

# --- Commands ---
@Client.on_message(filters.command("flood") & filters.group)
async def get_flood(client: Client, message: Message):
    settings = await antiflood_db.find_one({"chat_id": message.chat.id})
    limit = settings.get("limit", "Off") if settings else "Off"
    mode = settings.get("mode", "ban") if settings else "ban"
    await message.reply_text(f"**Antiflood settings for {message.chat.title}:**\nLimit: `{limit}`\nMode: `{mode}`")

@Client.on_message(filters.command("setflood") & filters.group)
async def set_flood(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/setflood <number/off/no>`")
    
    chat_id = message.chat.id
    settings = await antiflood_db.find_one({"chat_id": chat_id}) or {}
    current_limit = settings.get("limit", 0)

    val = message.command[1].lower()
    if val in ["off", "no", "0"]:
        if current_limit <= 0:
            return await message.reply_text("❌ AntiFlood is already disabled!")
        await antiflood_db.update_one({"chat_id": chat_id}, {"$set": {"limit": 0}}, upsert=True)
        await message.reply_text("✅ Antiflood disabled.")
    else:
        try:
            limit = int(val)
            if limit <= 0:
                return await message.reply_text("Please provide a number greater than 0.")
            if current_limit == limit:
                return await message.reply_text(f"❌ Antiflood limit is already set to `{limit}`!")
            
            await antiflood_db.update_one({"chat_id": chat_id}, {"$set": {"limit": limit}}, upsert=True)
            await message.reply_text(f"✅ Antiflood limit set to `{limit}`.")
        except ValueError:
            await message.reply_text("Please provide a valid number.")

@Client.on_message(filters.command("floodmode") & filters.group)
async def set_floodmode(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/floodmode <ban/mute/kick>`")
    
    chat_id = message.chat.id
    settings = await antiflood_db.find_one({"chat_id": chat_id}) or {}
    current_mode = settings.get("mode", "ban")

    mode = message.command[1].lower()
    if mode in ["ban", "mute", "kick"]:
        if current_mode == mode:
            return await message.reply_text(f"❌ Flood action is already set to `{mode}`!")
            
        await antiflood_db.update_one({"chat_id": chat_id}, {"$set": {"mode": mode}}, upsert=True)
        await message.reply_text(f"✅ Flood action set to: `{mode}`.")
    else:
        await message.reply_text("Supported actions: `ban`, `mute`, `kick`.")
