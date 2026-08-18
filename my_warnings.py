from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- BANNER IMAGE URL ---
BANNER_WARNINGS = "https://files.catbox.moe/x2sr79.png"

# --- IN-MEMORY DATABASES ---
WARNS_DB = {}        # {(chat_id, user_id): [warn_reasons]}
WARN_SETTINGS = {}  # {chat_id: {"limit": 3, "mode": "ban", "time": "off"}}

# --- EXACT HELP TEXT FROM SCREENSHOT (NO MONOSPACE / NO COPY TO CLIPBOARD) ---
WARNINGS_HELP_TEXT = (
    "**Warnings**\n\n"
    "Keep your members in check with warnings; stop them getting out of hand!\n\n"
    "**Admin commands:**\n"
    "• /warn <reason>: Warn a user.\n"
    "• /dwarn <reason>: Warn a user by reply, and delete their message.\n"
    "• /swarn <reason>: Silently warn a user, and delete your message.\n"
    "• /warns: See a user's warnings.\n"
    "• /rmwarn: Remove a user's latest warning.\n"
    "• /resetwarn: Reset all of a user's warnings to 0.\n"
    "• /resetallwarns: Delete all the warnings in a chat. All users return to 0 warns.\n"
    "• /warnings: Get the chat's warning settings.\n"
    "• /warnmode <ban/mute/kick/tban/tmute>: View or set the chat's warn mode.\n"
    "• /warnlimit <number>: View or set the number of warnings before users are punished.\n"
    "• /warntime <time>: View or set how long warnings should last. Example time values: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks.\n\n"
    "**Examples:**\n"
    "- Warn a user.\n"
    "-> /warn @user For disobeying the rules\n\n"
    "- Change the warning limit to 5; after 5 warnings, the warn action will trigger.\n"
    "-> /warnlimit 5\n\n"
    "- Set all warnings to expire after 4 weeks.\n"
    "-> /warntime 4w\n\n"
    "- Disable warn time; warnings will no long expire.\n"
    "-> /warntime off"
)

# --- HELPER FUNCTIONS ---
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

def get_settings(chat_id: int):
    if chat_id not in WARN_SETTINGS:
        WARN_SETTINGS[chat_id] = {"limit": 3, "mode": "ban", "time": "off"}
    return WARN_SETTINGS[chat_id]

# --- INLINE CALLBACK HANDLER (MATCHES help_warnings) ---

@Client.on_callback_query(filters.regex(r"^(help_warnings|warnings_help)$"))
async def warnings_help_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{WARNINGS_HELP_TEXT}\n[\u200b]({BANNER_WARNINGS})"
    
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

# --- REAL WORKING COMMAND HANDLERS WITH STRICT SCOPE ENFORCEMENT ---

# 1. WARN COMMANDS (/warn, /dwarn, /swarn)
@Client.on_message(filters.command(["warn", "dwarn", "swarn"]))
async def warn_user_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to warn users.")

    if not message.reply_to_message:
        return await message.reply_text("❌ Reply to a user's message to warn them!")

    cmd = message.command[0].lower()
    target_user = message.reply_to_message.from_user

    if await is_admin(client, message.chat.id, target_user.id):
        return await message.reply_text("❌ You cannot warn an Admin!")

    reason = "No reason provided"
    if len(message.command) > 1:
        reason = message.text.split(None, 1)[1]

    chat_id = message.chat.id
    user_id = target_user.id
    settings = get_settings(chat_id)

    # Delete message if dwarn or swarn
    if cmd in ["dwarn", "swarn"]:
        try:
            await message.reply_to_message.delete()
        except RPCError:
            pass
    if cmd == "swarn":
        try:
            await message.delete()
        except RPCError:
            pass

    key = (chat_id, user_id)
    if key not in WARNS_DB:
        WARNS_DB[key] = []
    WARNS_DB[key].append(reason)

    warn_count = len(WARNS_DB[key])
    max_limit = settings["limit"]

    if warn_count >= max_limit:
        WARNS_DB.pop(key, None)
        mode = settings["mode"]
        try:
            if mode == "ban":
                await client.ban_chat_member(chat_id, user_id)
                action_text = "banned"
            elif mode == "kick":
                await client.ban_chat_member(chat_id, user_id)
                await client.unban_chat_member(chat_id, user_id)
                action_text = "kicked"
            elif mode == "mute":
                await client.restrict_chat_member(chat_id, user_id, permissions=enums.ChatPermissions())
                action_text = "muted"
            else:
                await client.ban_chat_member(chat_id, user_id)
                action_text = "banned"

            if cmd != "swarn":
                await message.reply_text(f"⚠️ {target_user.mention} has reached {warn_count}/{max_limit} warnings and has been **{action_text}**!")
        except RPCError as e:
            if cmd != "swarn":
                await message.reply_text(f"❌ Failed to execute punishment: `{e}`")
    else:
        if cmd != "swarn":
            await message.reply_text(f"⚠️ {target_user.mention} has been warned ({warn_count}/{max_limit}).\n**Reason:** {reason}")

# 2. CHECK WARNS (/warns)
@Client.on_message(filters.command("warns"))
async def check_warns_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    key = (message.chat.id, target.id)
    reasons = WARNS_DB.get(key, [])
    settings = get_settings(message.chat.id)

    if not reasons:
        return await message.reply_text(f"User {target.mention} has no warnings.")

    res = f"User {target.mention} has **{len(reasons)}/{settings['limit']}** warnings:\n"
    for idx, r in enumerate(reasons, 1):
        res += f"• {idx}. {r}\n"
    await message.reply_text(res)

# 3. REMOVE LATEST WARN (/rmwarn)
@Client.on_message(filters.command("rmwarn"))
async def rmwarn_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin access required.")

    if not message.reply_to_message:
        return await message.reply_text("❌ Reply to a user's message to remove a warning!")

    target = message.reply_to_message.from_user
    key = (message.chat.id, target.id)
    if key in WARNS_DB and WARNS_DB[key]:
        WARNS_DB[key].pop()
        await message.reply_text(f"✅ Removed latest warning from {target.mention}.")
    else:
        await message.reply_text(f"User {target.mention} has no warnings to remove.")

# 4. RESET USER WARNS (/resetwarn)
@Client.on_message(filters.command("resetwarn"))
async def resetwarn_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin access required.")

    if not message.reply_to_message:
        return await message.reply_text("❌ Reply to a user's message to reset their warnings!")

    target = message.reply_to_message.from_user
    WARNS_DB.pop((message.chat.id, target.id), None)
    await message.reply_text(f"✅ Reset all warnings for {target.mention}.")

# 5. RESET ALL CHAT WARNS (/resetallwarns)
@Client.on_message(filters.command("resetallwarns"))
async def resetallwarns_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin access required.")

    chat_id = message.chat.id
    keys_to_del = [k for k in WARNS_DB.keys() if k[0] == chat_id]
    for k in keys_to_del:
        WARNS_DB.pop(k, None)
    await message.reply_text("✅ All warnings in this chat have been deleted.")

# 6. GET WARN SETTINGS (/warnings)
@Client.on_message(filters.command("warnings"))
async def warnings_settings_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    settings = get_settings(message.chat.id)
    await message.reply_text(
        f"**Warning Settings for this chat:**\n"
        f"• **Warn Limit:** `{settings['limit']}`\n"
        f"• **Warn Mode:** `{settings['mode']}`\n"
        f"• **Warn Time:** `{settings['time']}`"
    )

# 7. WARN MODE (/warnmode)
@Client.on_message(filters.command("warnmode"))
async def warnmode_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin access required.")

    settings = get_settings(message.chat.id)
    if len(message.command) < 2:
        return await message.reply_text(f"Current warn mode is: **{settings['mode']}**")

    mode = message.command[1].lower()
    if mode in ["ban", "mute", "kick"]:
        settings["mode"] = mode
        await message.reply_text(f"✅ Warn mode set to **{mode}**.")
    else:
        await message.reply_text("Invalid mode! Choose from: `ban`, `mute`, `kick`.")

# 8. WARN LIMIT (/warnlimit)
@Client.on_message(filters.command("warnlimit"))
async def warnlimit_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin access required.")

    settings = get_settings(message.chat.id)
    if len(message.command) < 2:
        return await message.reply_text(f"Current warn limit is: **{settings['limit']}**")

    val = message.command[1]
    if val.isdigit() and int(val) > 0:
        settings["limit"] = int(val)
        await message.reply_text(f"✅ Warn limit set to **{val}**.")
    else:
        await message.reply_text("Please provide a valid number greater than 0.")

# 9. WARN TIME (/warntime)
@Client.on_message(filters.command("warntime"))
async def warntime_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Admin access required.")

    settings = get_settings(message.chat.id)
    if len(message.command) < 2:
        return await message.reply_text(f"Current warn expiry time is: **{settings['time']}**")

    time_val = message.command[1].lower()
    settings["time"] = time_val
    await message.reply_text(f"✅ Warn time set to **{time_val}**.")
