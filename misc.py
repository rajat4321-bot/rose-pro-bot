import random
from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType
from pyrogram.errors import RPCError

# --- DEDICATED BANNER IMAGE URLS ---
BANNER_MISC_MAIN = "https://files.catbox.moe/j7unjf.png"
BANNER_MISC_SILENT = "https://files.catbox.moe/ipfrqq.png"
BANNER_MISC_BOT2BOT = "https://files.catbox.moe/osx6pd.png"

# --- RANDOM RUN STRINGS FOR /runs ---
RUNS_STRINGS = [
    "Runs away as fast as possible! 🏃💨",
    "Disappears into thin air... 🌫️",
    "Gotta go fast! 🦔💨",
    "Runs to the nearest hiding spot! 🙈",
    "Escapes from the scene like a ninja! 🥷"
]

# --- HELP TEXT CONTENT ---

MISC_MAIN_HELP = (
    "**Misc**\n\n"
    "An 'odds and ends' module for small, simple commands which don't really fit anywhere.\n\n"
    "**Commands:**\n"
    "• `/runs`: Respond with a randomly generated \"run away\" string.\n"
    "• `/id`: Get the ID of a user, group, or channel. Can be used by reply, username, or mention.\n"
    "• `/info`: Get a user's info.\n"
    "• `/markdownhelp`: Information on how to use markdown with the bot. PM only.\n"
    "• `/limits`: Show the bot's limits."
)

MISC_SILENT_HELP = (
    "**Silent Actions**\n\n"
    "Silent automated actions allow you to silently automate admin actions in your group. "
    "This can be through either locks, blocklists, or antiflood.\n\n"
    "**Actions available:** `sban`/`smute`/`skick`/`swarn`\n\n"
    "**Note:** To ensure that admins are aware of Rose's actions, a log channel is required to enable silent actions. "
    "If you unset your log channel, or disable silent actions, all existing actions will return to being loud.\n\n"
    "**Enabling silent actions:**\n"
    "• `/stenactions <yes/no/on/off>`: Enable/disable silent action features.\n\n"
    "**Example usages:**\n"
    "• Silently ban anonymous channels using locks:\n"
    "`/lock anonchannel ### This chat is for users only (sban)`\n\n"
    "• Using silent actions in blocklists:\n"
    "`/addblocklist \"yarr\" We dont want any pirates here! (skick)`\n\n"
    "• Using temporary silent actions by adding a time value:\n"
    "`/addblocklist \"fight club\" We dont talk about fight club! (smute 12h)`\n\n"
    "• Using temporary silent actions in antiflood:\n"
    "`/setfloodmode sban 1h`"
)

MISC_BOT2BOT_HELP = (
    "**Bot To Bot**\n\n"
    "Bot To Bot allows other bots to send commands to Rose. This is useful for automation and AI, "
    "but should be used with care.\n\n"
    "The following options are supported, where `off` is the default:\n"
    "• `off`: Bots cannot use any of Rose's commands.\n"
    "• `admin`: Bots with admin privileges can use Rose's commands.\n"
    "• `all`: All bots can use Rose's commands, regardless of admin status.\n\n"
    "If Bot To Bot is turned on, and an admin bot uses an admin command, the command has to be reviewed (and approved) by a human admin.\n"
    "This can be turned off by enabling the 'skip review' feature - in which case the calling bot's admin permissions will be followed.\n\n"
    "**Commands:**\n"
    "• `/bot2bot <off/admin/all>`: Set up rules for which bots can interact with Rose.\n"
    "• `/bot2botskipreview <yes/no/on/off>`: Enable or disable the admin review of bot commands before execution."
)

# --- INLINE CALLBACK HANDLERS FOR NAVIGATION ---

@Client.on_callback_query(filters.regex(r"^help_misc$"))
async def help_misc_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Silent actions", callback_data="misc_silent"),
            InlineKeyboardButton("Bot To Bot", callback_data="misc_bot2bot")
        ],
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{MISC_MAIN_HELP}\n[\u200b]({BANNER_MISC_MAIN})"
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

@Client.on_callback_query(filters.regex(r"^misc_silent$"))
async def misc_silent_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_misc")]
    ])
    full_text = f"{MISC_SILENT_HELP}\n[\u200b]({BANNER_MISC_SILENT})"
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

@Client.on_callback_query(filters.regex(r"^misc_bot2bot$"))
async def misc_bot2bot_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_misc")]
    ])
    full_text = f"{MISC_BOT2BOT_HELP}\n[\u200b]({BANNER_MISC_BOT2BOT})"
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

# --- COMMAND HANDLERS WITH STRICT PM / GROUP ENFORCEMENT ---

@Client.on_message(filters.command("runs"))
async def runs_cmd(client: Client, message: Message):
    res = random.choice(RUNS_STRINGS)
    await message.reply_text(res)

@Client.on_message(filters.command("id"))
async def id_cmd(client: Client, message: Message):
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if target_user:
            return await message.reply_text(
                f"User `{target_user.first_name}` ID: `{target_user.id}`\n"
                f"Current Chat ID: `{message.chat.id}`",
                parse_mode=enums.ParseMode.MARKDOWN
            )
    
    args = message.command[1:]
    if args:
        try:
            user = await client.get_users(args[0])
            return await message.reply_text(
                f"User `{user.first_name}` ID: `{user.id}`",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        except Exception:
            return await message.reply_text("❌ User not found.")

    await message.reply_text(
        f"Your ID: `{message.from_user.id}`\n"
        f"Chat ID: `{message.chat.id}`",
        parse_mode=enums.ParseMode.MARKDOWN
    )

@Client.on_message(filters.command("info"))
async def info_cmd(client: Client, message: Message):
    user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            user = await client.get_users(message.command[1])
        except Exception:
            return await message.reply_text("❌ Invalid username or user ID.")
    else:
        user = message.from_user

    if not user:
        return await message.reply_text("❌ User info could not be retrieved.")

    info_text = (
        f"**User Info:**\n"
        f"• **First Name:** {user.first_name}\n"
        f"• **Last Name:** {user.last_name or 'None'}\n"
        f"• **ID:** `{user.id}`\n"
        f"• **Username:** @{user.username if user.username else 'None'}\n"
        f"• **User Link:** {user.mention}"
    )
    await message.reply_text(info_text, parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("markdownhelp"))
async def markdownhelp_cmd(client: Client, message: Message):
    if message.chat.type != ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used in PM! Please message me privately.")

    md_text = (
        "**Markdown Help**\n\n"
        "Rose supports the following markdown formatting:\n\n"
        "• `*bold*` or `**bold**`: **bold text**\n"
        "• `_italic_` or `__italic__`: _italic text_\n"
        "• `` `code` ``: `code text`\n"
        "• `~strikethrough~`: ~strikethrough text~\n"
        "• `||spoiler||`: ||spoiler text||\n"
        "• `[text](url)`: [inline link](https://telegram.org)\n"
        "• `[button name](buttonurl:link)`: Adds an inline button."
    )
    await message.reply_text(md_text, parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("limits"))
async def limits_cmd(client: Client, message: Message):
    limits_text = (
        "**Bot Limits:**\n\n"
        "• **Max Rules Length:** 4000 characters\n"
        "• **Max Welcome Text:** 2000 characters\n"
        "• **Max Buttons per Message:** 8 rows x 8 columns\n"
        "• **Max Active Filters per Chat:** 100"
    )
    await message.reply_text(limits_text, parse_mode=enums.ParseMode.MARKDOWN)
