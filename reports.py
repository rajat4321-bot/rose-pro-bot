from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- BANNER IMAGE URL ---
BANNER_REPORTS = "https://files.catbox.moe/kjoa25.png"

# --- IN-MEMORY DATABASE FOR SETTINGS ---
REPORTS_SETTING_DB = {} # {chat_id: bool}

# --- EXACT HELP TEXT FROM SCREENSHOT (NO CODE BLOCKS TO PREVENT COPY TO CLIPBOARD) ---
REPORTS_HELP_TEXT = (
    "**Reports**\n\n"
    "We're all busy people who don't have time to monitor our groups 24/7. "
    "But how do you react if someone in your group is spamming?\n\n"
    "Presenting reports; if someone in your group thinks someone needs reporting, "
    "they now have an easy way to call all admins.\n\n"
    "**User commands:**\n"
    "• /report: Reply to a message to report it for admins to review.\n"
    "• @admin: Same as /report\n\n"
    "**Admin commands:**\n"
    "• /reports <yes/no/on/off>: Enable/disable user reports.\n\n"
    "To report a user, simply reply to his message with @admin or /report; Rose will then reply with a message "
    "stating that admins have been notified. This message tags all the chat admins; same as if they had been @'ed.\n\n"
    "Note that the report commands do not work when admins use them; or when used to report an admin. "
    "Rose assumes that admins don't need to report, or be reported!"
)

# --- HELPER FUNCTIONS ---
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

# --- INLINE CALLBACK HANDLER (MATCHES help_reports) ---

@Client.on_callback_query(filters.regex(r"^(help_reports|reports_help)$"))
async def reports_help_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{REPORTS_HELP_TEXT}\n[\u200b]({BANNER_REPORTS})"
    
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

# --- REAL WORKING COMMAND HANDLERS WITH STRICT GROUP SCOPE ENFORCEMENT ---

# 1. USER REPORT COMMAND (/report OR @admin)
@Client.on_message((filters.command("report") | filters.regex(r"^@admin$")) & ~filters.private)
async def report_cmd(client: Client, message: Message):
    chat_id = message.chat.id

    # Check if reports feature is turned OFF
    if not REPORTS_SETTING_DB.get(chat_id, True):
        return

    # Check if user replied to a message
    if not message.reply_to_message:
        return await message.reply_text("❌ Reply to a message to report it to admins!")

    reporter = message.from_user
    reported_user = message.reply_to_message.from_user

    # Ignored if done by Admin
    if reporter and await is_admin(client, chat_id, reporter.id):
        return await message.reply_text("Admins don't need to report messages.")

    # Ignored if reported target is an Admin
    if reported_user and await is_admin(client, chat_id, reported_user.id):
        return await message.reply_text("You cannot report an admin!")

    # Fetch all admins and tag them
    admin_mentions = []
    async for member in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        if not member.user.is_bot:
            admin_mentions.append(f"[\u200b](tg://user?id={member.user.id})")

    tag_text = "".join(admin_mentions)
    report_msg = (
        f"⚠️ **Report Notification**\n\n"
        f"• **Reported by:** {reporter.mention if reporter else 'User'}\n"
        f"• **Reported User:** {reported_user.mention if reported_user else 'User'}\n\n"
        f"Admins have been notified!{tag_text}"
    )

    await message.reply_text(
        text=report_msg,
        reply_to_message_id=message.reply_to_message.id,
        parse_mode=enums.ParseMode.MARKDOWN
    )

# PM ENFORCEMENT FOR /report
@Client.on_message(filters.command("report") & filters.private)
async def report_pm_cmd(client: Client, message: Message):
    await message.reply_text("❌ The `/report` command can only be used inside groups!")

# 2. ADMIN SETTING TOGGLE (/reports)
@Client.on_message(filters.command("reports"))
async def reports_toggle_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to toggle reports setting.")

    chat_id = message.chat.id
    args = message.command[1:]

    if not args:
        status = "ENABLED" if REPORTS_SETTING_DB.get(chat_id, True) else "DISABLED"
        return await message.reply_text(f"Reports are currently **{status}** in this chat.")

    param = args[0].lower()
    if param in ["yes", "on", "true"]:
        REPORTS_SETTING_DB[chat_id] = True
        await message.reply_text("✅ Users can now report messages to admins using `/report` or `@admin`.")
    elif param in ["no", "off", "false"]:
        REPORTS_SETTING_DB[chat_id] = False
        await message.reply_text("✅ Users can no longer report messages in this chat.")
    else:
        await message.reply_text("Usage: `/reports <yes/no/on/off>`")
