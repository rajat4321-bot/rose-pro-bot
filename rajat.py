from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType
from pyrogram.errors import RPCError

# --- BANNER IMAGE URL ---
BANNER_PRIVACY = "https://files.catbox.moe/y0szup.png"

# --- EXACT HELP TEXT FROM SCREENSHOT (WITHOUT MONOSPACE TO PREVENT COPY TO CLIPBOARD) ---
PRIVACY_HELP_TEXT = (
    "**Privacy**\n\n"
    "The privacy module allows you to see the bot privacy policy, as "
    "well as view and delete the data the bot stores about you.\n\n"
    "**The single command which can only be used in PM:**\n"
    "• /privacy: Provides all the tools relating to privacy, such as listing "
    "the privacy policy, retrieving, and deleting your data."
)

# --- INLINE CALLBACK HANDLER (MATCHES help_privacy) ---

@Client.on_callback_query(filters.regex(r"^(help_privacy|privacy_help)$"))
async def privacy_help_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{PRIVACY_HELP_TEXT}\n[\u200b]({BANNER_PRIVACY})"
    
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

# --- COMMAND HANDLERS WITH STRICT PM SCOPE ENFORCEMENT ---

@Client.on_message(filters.command("privacy"))
async def privacy_cmd(client: Client, message: Message):
    # Enforce PM Only rule
    if message.chat.type != ChatType.PRIVATE:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Privacy Policy", url=f"https://t.me/{client.me.username}?start=privacy")]
        ])
        return await message.reply_text(
            "❌ The privacy command can only be used in PM to manage your personal data.",
            reply_markup=keyboard
        )

    # Output in PM
    privacy_policy_text = (
        "**User Privacy Policy**\n\n"
        "We value your privacy and security. Here is how your data is handled:\n\n"
        "• **Data Storage:** We only store minimal user IDs and chat settings required for moderation.\n"
        "• **Data Retention:** Data is automatically cleaned when the bot leaves a chat or upon request.\n"
        "• **Data Sharing:** We never share, sell, or process your chat data with third parties.\n\n"
        "To request a full export or deletion of your stored records, contact our support team."
    )
    await message.reply_text(privacy_policy_text, parse_mode=enums.ParseMode.MARKDOWN)
