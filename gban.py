from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType
from pyrogram.errors import RPCError

# --- BANNER IMAGE URL ---
BANNER_GBAN = "https://files.catbox.moe/g6g85s.png"

# --- OWNER & SUDO LIST (Replace with your Owner ID) ---
OWNER_ID = 8667794762  # Replace with actual Bot Owner Telegram User ID
SUDO_USERS = [OWNER_ID]  # Add other sudo user IDs if needed

# --- IN-MEMORY DATABASES ---
GBANNED_USERS = {}  # {user_id: reason}
GBAN_STAT_DB = {}   # {chat_id: bool} (GBan protection enable/disable per group)

# --- EXACT HELP TEXT (NO MONOSPACE / NO COPY TO CLIPBOARD) ---
GBAN_HELP_TEXT = (
    "**Global Bans**\n\n"
    "Global ban (GBan) allows bot owners and sudo users to globally ban malicious users, "
    "spammers, and scammers across all groups where the bot is present!\n\n"
    "**Sudo / Owner commands:**\n"
    "• /gban <user> <reason>: Globally ban a user from all chats managed by the bot.\n"
    "• /ungban <user>: Remove a user from the global ban list.\n"
    "• /gbanlist: View the list of all currently globally banned users.\n"
    "• /gbanstat: Check if global ban enforcement is enabled in the current chat.\n\n"
    "**Admin commands:**\n"
    "• /antigban <yes/no/on/off>: Enable or disable GBan enforcement in your group.\n\n"
    "**Examples:**\n"
    "- Globally ban a spammer across all chats.\n"
    "-> /gban @spammer Spamming link in groups\n\n"
    "- Remove global ban from a user.\n"
    "-> /ungban @spammer"
)

# --- HELPER FUNCTIONS ---
def is_sudo(user_id: int) -> bool:
    return user_id in SUDO_USERS

# --- INLINE CALLBACK HANDLER (MATCHES help_gban) ---

@Client.on_callback_query(filters.regex(r"^(help_gban|gban_help)$"))
async def gban_help_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{GBAN_HELP_TEXT}\n[\u200b]({BANNER_GBAN})"
    
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

# 1. GLOBAL BAN COMMAND (/gban) - SUDO / OWNER ONLY (PM & GC BOTH ALLOWED)
@Client.on_message(filters.command("gban"))
async def gban_cmd(client: Client, message: Message):
    if not is_sudo(message.from_user.id):
        return await message.reply_text("❌ This command is restricted to Bot Owner and Sudo users only.")

    target_user = None
    reason = "No reason provided."

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if len(message.command) > 1:
            reason = message.text.split(None, 1)[1]
    elif len(message.command) > 1:
        user_input = message.command[1]
        try:
            target_user = await client.get_users(user_input)
            if len(message.command) > 2:
                reason = message.text.split(None, 2)[2]
        except Exception:
            return await message.reply_text("❌ Could not find that user.")

    if not target_user:
        return await message.reply_text("❌ Reply to a user or mention their ID/username to GBan!")

    if is_sudo(target_user.id):
        return await message.reply_text("❌ You cannot globally ban a Sudo user or Owner!")

    GBANNED_USERS[target_user.id] = reason
    await message.reply_text(
        f"🚨 **Global Ban Initiated!**\n\n"
        f"• **User:** {target_user.mention}\n"
        f"• **ID:** `{target_user.id}`\n"
        f"• **Reason:** {reason}"
    )

# 2. UNGBAN COMMAND (/ungban) - SUDO / OWNER ONLY
@Client.on_message(filters.command("ungban"))
async def ungban_cmd(client: Client, message: Message):
    if not is_sudo(message.from_user.id):
        return await message.reply_text("❌ This command is restricted to Bot Owner and Sudo users only.")

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        user_input = message.command[1]
        try:
            target_user = await client.get_users(user_input)
        except Exception:
            return await message.reply_text("❌ Could not find that user.")

    if not target_user:
        return await message.reply_text("❌ Reply to a user or mention their ID/username to UnGBan!")

    if target_user.id not in GBANNED_USERS:
        return await message.reply_text("❌ This user is not globally banned.")

    GBANNED_USERS.pop(target_user.id, None)
    await message.reply_text(f"✅ Removed global ban for {target_user.mention}.")

# 3. GBAN LIST COMMAND (/gbanlist)
@Client.on_message(filters.command("gbanlist"))
async def gbanlist_cmd(client: Client, message: Message):
    if not GBANNED_USERS:
        return await message.reply_text("There are currently no globally banned users.")

    res = "**Globally Banned Users List:**\n\n"
    for idx, (u_id, reason) in enumerate(GBANNED_USERS.items(), 1):
        res += f"• {idx}. User ID: `{u_id}` | Reason: {reason}\n"

    await message.reply_text(res)

# 4. CHECK GBAN STAT IN CHAT (/gbanstat) - GROUP ONLY
@Client.on_message(filters.command("gbanstat"))
async def gbanstat_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    is_enabled = GBAN_STAT_DB.get(message.chat.id, True)
    status = "ENABLED" if is_enabled else "DISABLED"
    await message.reply_text(f"Global Ban enforcement is currently **{status}** in this chat.")

# 5. ANTIGBAN TOGGLE FOR GROUP ADMINS (/antigban) - GROUP ONLY
@Client.on_message(filters.command("antigban"))
async def antigban_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    chat_id = message.chat.id
    args = message.command[1:]

    if not args:
        status = "DISABLED" if GBAN_STAT_DB.get(chat_id, True) else "ENABLED"
        return await message.reply_text(f"Anti-GBan mode is currently: **{status}**")

    param = args[0].lower()
    if param in ["yes", "on", "true"]:
        GBAN_STAT_DB[chat_id] = False  # Anti-GBan ON = GBan Disabled
        await message.reply_text("✅ Anti-GBan enabled! Globally banned users will not be auto-banned here.")
    elif param in ["no", "off", "false"]:
        GBAN_STAT_DB[chat_id] = True   # Anti-GBan OFF = GBan Enabled
        await message.reply_text("✅ Anti-GBan disabled! GBan enforcement is now active.")
    else:
        await message.reply_text("Usage: `/antigban <yes/no/on/off>`")

# 6. AUTO-BAN GBANNED USER ON MESSAGE / JOIN (AUTOMATIC HANDLER)
@Client.on_message(filters.group, group=-1)
async def auto_gban_enforcer(client: Client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Skip if GBan protection is disabled in this chat
    if not GBAN_STAT_DB.get(chat_id, True):
        return

    if user_id in GBANNED_USERS:
        try:
            await client.ban_chat_member(chat_id, user_id)
            await message.delete()
            reason = GBANNED_USERS[user_id]
            await client.send_message(
                chat_id,
                f"🚨 **Global Ban Enforced!**\n\n"
                f"User {message.from_user.mention} was automatically banned because they are globally banned.\n"
                f"**Reason:** {reason}"
            )
        except RPCError:
            pass
