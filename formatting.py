from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import RPCError

# --- DEDICATED BANNER IMAGE URLS FOR FORMATTING ---
BANNER_FORMATTING_MAIN = "https://files.catbox.moe/bis9tm.png"
BANNER_MARKDOWN = "https://files.catbox.moe/z9fl2j.png"
BANNER_FILLINGS = "https://files.catbox.moe/hy6sxi.png"
BANNER_RANDOM = "https://files.catbox.moe/6lhrwr.png"
BANNER_BUTTONS = "https://files.catbox.moe/5jcaqm.png"


# --- TEXT CONTENT DEFINITIONS ---

FORMATTING_MAIN_TEXT = (
    "**Formatting**\n\n"
    "Formatting supports a large number of options to make your messages "
    "more expressive. Take a look!"
)

MARKDOWN_TEXT = (
    "**Markdown Formatting**\n\n"
    "You can format your message using bold, italics, underline, and much more. "
    "Go ahead and experiment!\n\n"
    "**Supported Markdown:**\n"
    "• `code words`: Backticks are used for monospace fonts. Shows as `code words`.\n"
    "• `*italic words*`: Single asterisks are used for italic fonts. Shows as *italic words*.\n"
    "• `**bold words**`: Asterisks are used for bold fonts. Shows as **bold words**.\n"
    "• `~strikethrough~`: Tildes are used for strikethrough. Shows as ~~strikethrough~~.\n"
    "• `__underline__`: Double underscores are used for underlines. Shows as __underline__.\n"
    "• `||spoiler||`: Double vertical bars are used for spoilers. Shows as ||spoiler||\n"
    "• ```python\necho 'hi'\n```: Triple backticks are used for codeblocks.\n"
    "• `> quote`: You can quote a line by prefixing it with `>`.\n"
    "• `[hyperlink](google.com)`: Create clickable hyperlinks."
)

FILLINGS_TEXT = (
    "**Fillings**\n\n"
    "You can also customise the contents of your message with contextual data. "
    "For example, you could mention a user by name in the welcome message, or mention them in a filter!\n\n"
    "**Supported Fillings:**\n"
    "• `{first}`: The user's first name.\n"
    "• `{last}`: The user's last name.\n"
    "• `{fullname}`: The user's full name.\n"
    "• `{username}`: The user's username.\n"
    "• `{mention}`: Mentions the user with their firstname.\n"
    "• `{id}`: The user's ID.\n"
    "• `{chatname}`: The chat's name.\n"
    "• `{rules}`: Create a button to the chat's rules on a new row.\n"
    "• `{preview}`: Enables link previews for this message.\n"
    "• `{protect}`: Stop this message from being forwarded or screenshotted.\n\n"
    "**Example Usage:**\n"
    "• `/filter test Hey {first}, triggered this filter.`\n"
    "• `/setwelcome Welcome {mention} to {chatname}!`"
)

RANDOM_TEXT = (
    "**Random Content**\n\n"
    "You can make your bot respond with random messages, quotes, or replies "
    "using random formatting variables!\n\n"
    "**Syntax:**\n"
    "`/filter hello ::: Hi! ::: Hello there! ::: Hey!`\n\n"
    "Whenever a user triggers the filter, the bot will pick one random option "
    "from the provided list separated by `:::`."
)

BUTTONS_TEXT = (
    "**Buttons**\n\n"
    "One of Telegram's popular features is the ability to add buttons to your "
    "welcome messages, notes, or filters. This module explains all about this!\n\n"
    "**Simple Buttons:**\n"
    "`[Google](buttonurl://google.com)`\n\n"
    "**Buttons on the Same Line:**\n"
    "`[Google](buttonurl://google.com)`\n"
    "`[Bing](buttonurl://bing.com:same)`\n\n"
    "**Note Buttons:**\n"
    "`[First Note](buttonurl://#my_note)`\n"
    "`[Second Note](buttonurl://#second_note:same)`"
)


# --- CALLBACK ROUTERS & HANDLERS ---

@Client.on_callback_query(filters.regex(r"^help_formatting$"))
async def formatting_main_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Markdown formatting", callback_data="fmt_markdown"),
            InlineKeyboardButton("Fillings", callback_data="fmt_fillings")
        ],
        [
            InlineKeyboardButton("Random content", callback_data="fmt_random"),
            InlineKeyboardButton("Buttons", callback_data="fmt_buttons")
        ],
        [
            InlineKeyboardButton("Back", callback_data="help_back")
        ]
    ])
    
    full_text = f"{FORMATTING_MAIN_TEXT}\n[\u200b]({BANNER_FORMATTING_MAIN})"
    
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^fmt_markdown$"))
async def fmt_markdown_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_formatting")]
    ])
    full_text = f"{MARKDOWN_TEXT}\n[\u200b]({BANNER_MARKDOWN})"
    
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^fmt_fillings$"))
async def fmt_fillings_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_formatting")]
    ])
    full_text = f"{FILLINGS_TEXT}\n[\u200b]({BANNER_FILLINGS})"
    
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^fmt_random$"))
async def fmt_random_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_formatting")]
    ])
    full_text = f"{RANDOM_TEXT}\n[\u200b]({BANNER_RANDOM})"
    
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass
    await callback.answer()


@Client.on_callback_query(filters.regex(r"^fmt_buttons$"))
async def fmt_buttons_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_formatting")]
    ])
    full_text = f"{BUTTONS_TEXT}\n[\u200b]({BANNER_BUTTONS})"
    
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass
    await callback.answer()
