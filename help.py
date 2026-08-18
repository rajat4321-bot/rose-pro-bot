from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

HELP_PHOTO = "https://files.catbox.moe/k5ixyn.png"

HELP_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Admin", callback_data="help_admin"),
        InlineKeyboardButton("Antiflood", callback_data="help_antiflood"),
        InlineKeyboardButton("Antiraid", callback_data="help_antiraid"),
    ],
    [
        InlineKeyboardButton("Approval", callback_data="help_approval"),
        InlineKeyboardButton("Bans", callback_data="help_bans"),
        InlineKeyboardButton("Blocklists", callback_data="help_blocklists"),
    ],
    [
        InlineKeyboardButton("CAPTCHA", callback_data="help_captcha"),
        InlineKeyboardButton("Clean Commands", callback_data="help_cleanCmds"),
        InlineKeyboardButton("Clean Service", callback_data="help_cleanService"),
    ],
    [
        InlineKeyboardButton("Connections", callback_data="help_connections"),
        InlineKeyboardButton("Disabling", callback_data="help_disabling"),
        InlineKeyboardButton("Federations", callback_data="help_federations"),
    ],
    [
        InlineKeyboardButton("Filters", callback_data="help_filters"),
        InlineKeyboardButton("Formatting", callback_data="help_formatting"),
        InlineKeyboardButton("Greetings", callback_data="help_greetings"),
    ],
    [
        InlineKeyboardButton("Import/Export", callback_data="help_import"),
        InlineKeyboardButton("Languages", callback_data="help_languages"),
        InlineKeyboardButton("Locks", callback_data="help_locks"),
    ],
    [
        InlineKeyboardButton("Log Channels", callback_data="help_log"),
        InlineKeyboardButton("Misc", callback_data="help_misc"),
        InlineKeyboardButton("Notes", callback_data="help_notes"),
    ],
    [
        InlineKeyboardButton("Pin", callback_data="help_pin"),
        InlineKeyboardButton("Privacy", callback_data="help_privacy"),
        InlineKeyboardButton("Purges", callback_data="help_purges"),
    ],
    [
        InlineKeyboardButton("Reports", callback_data="help_reports"),
        InlineKeyboardButton("Rules", callback_data="help_rules"),
        InlineKeyboardButton("Topics", callback_data="help_topics"),
    ],
    [
        InlineKeyboardButton("Warnings", callback_data="help_warnings"),
    ],
    [
        InlineKeyboardButton("gban", callback_data="help_gban"),
    ],
])

def register_help_handlers(app: Client):

    @app.on_message(filters.command("help") & filters.private)
    async def help_command(client: Client, message: Message):
        help_text = (
            f"Hey {message.from_user.mention}! 👋\n\n"
            "I am **ATHER X MANAGEMENT**, built to assist group admins in keeping chats secure, active, and fully automated.\n"
            "I come equipped with anti-spam, customizable filters, warnings, locks, and powerful moderation toolsets.\n\n"
            "**Helpful commands:**\n"
            "• /start - Starts the bot and checks live status.\n"
            "• /help - Opens this detailed menu to manage your chat.\n"
            "• /privacy - Shows data processing and security rules.\n\n"
            "Select any category button below to inspect command usages!"
            f"[\u200b]({HELP_PHOTO})"
        )

        await message.reply_text(
            text=help_text,
            reply_markup=HELP_KEYBOARD,
            disable_web_page_preview=False
        )

    # Back Button Handler to return to Main Help Menu
    @app.on_callback_query(filters.regex("^help_back$"))
    async def help_back_menu(client: Client, callback: CallbackQuery):
        await callback.answer()
        help_text = (
            f"Hey {callback.from_user.mention}! 👋\n\n"
            "I am **ATHER X MANAGEMENT**, built to assist group admins in keeping chats secure, active, and fully automated.\n"
            "I come equipped with anti-spam, customizable filters, warnings, locks, and powerful moderation toolsets.\n\n"
            "**Helpful commands:**\n"
            "• /start - Starts the bot and checks live status.\n"
            "• /help - Opens this detailed menu to manage your chat.\n"
            "• /privacy - Shows data processing and security rules.\n\n"
            "Select any category button below to inspect command usages!"
            f"[\u200b]({HELP_PHOTO})"
        )
        await callback.message.edit_text(
            text=help_text,
            reply_markup=HELP_KEYBOARD,
            disable_web_page_preview=False
        )
