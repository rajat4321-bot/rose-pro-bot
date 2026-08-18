from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- DEDICATED BANNER IMAGE URL ---
BANNER_LANGUAGES = "https://files.catbox.moe/une76f.png"

# --- IN-MEMORY DATABASE FOR CHAT LANGUAGES ---
LANG_DB = {}

# --- EXACT HELP TEXT FROM SCREENSHOT ---
LANGUAGES_HELP_TEXT = (
    "**Languages**\n\n"
    "Not every group speaks fluent English; some groups would rather have Rose respond in their own language.\n\n"
    "This is where translations come in; you can change the language of the bot's replies to be in the language of your choice!\n\n"
    "**Available languages are:**\n"
    "• AR (العربية)\n"
    "• AZ (azərbaycan)\n"
    "• BE (беларуская)\n"
    "• BG (български)\n"
    "• BS (bosanski)\n"
    "• DE (Deutsch)\n"
    "• EL (Ελληνικά)\n"
    "• EN-GB (British English)\n"
    "• EN-PT (Pirate)\n"
    "• ES (español)\n"
    "• ES-AR (español)\n"
    "• FA-AF (دری)\n"
    "• FA (فارسی)\n"
    "• FI (suomi)\n"
    "• FR (français)\n"
    "• HE (עברית)\n"
    "• HR (hrvatski)\n"
    "• HU (magyar)\n"
    "• ID (Indonesia)\n"
    "• IT (italiano)\n"
    "• KO (한국어)\n"
    "• ML-IN (മലയാളം)\n"
    "• MY (Bahasa Melayu)\n"
    "• NL (Nederlands)\n"
    "• PL (polski)\n"
    "• PT-BR (português brasileiro)\n"
    "• PT-PT (português)\n"
    "• RU (русский)\n"
    "• SK (slovenčina)\n"
    "• SR-CS (srpski)\n"
    "• TA (தமிழ்)\n"
    "• TR (Türkçe)\n"
    "• UK (українська)\n"
    "• UZ (o'zbek)\n"
    "• VI (Tiếng Việt)\n"
    "• ZH-CN (简体)\n"
    "• ZH-TW (繁體)\n\n"
    "Note: The `/help` and `/start` commands are not translated.\n\n"
    "**Admin commands:**\n"
    "• `/setlang <languagecode>`: Set the bot language."
)

# --- INLINE CALLBACK HANDLER (ONLY BACK BUTTON) ---

@Client.on_callback_query(filters.regex(r"^help_languages$"))
async def help_languages_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{LANGUAGES_HELP_TEXT}\n[\u200b]({BANNER_LANGUAGES})"
    
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

# --- STRICT ADMIN CHECKER ---
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

# --- COMMAND HANDLERS WITH STRICT PM/GROUP ENFORCEMENT ---

@Client.on_message(filters.command(["setlang", "setlanguage"]))
async def set_language_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to change the group language.")

    args = message.command[1:]
    if not args:
        current_lang = LANG_DB.get(message.chat.id, "en")
        return await message.reply_text(
            f"The current language for this chat is `{current_lang}`.\n"
            "Usage: `/setlang <language_code>` (e.g., `/setlang en` or `/setlang hi`)",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    new_lang = args[0].lower()
    LANG_DB[message.chat.id] = new_lang
    await message.reply_text(
        f"✅ Chat language updated to `{new_lang}` successfully!",
        parse_mode=enums.ParseMode.MARKDOWN
    )

@Client.on_message(filters.command(["lang", "languages"]))
async def get_language_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text(
            "Bot default language is `English (en)`.",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    current_lang = LANG_DB.get(message.chat.id, "en")
    await message.reply_text(
        f"This group's language is set to: `{current_lang}`.",
        parse_mode=enums.ParseMode.MARKDOWN
    )
