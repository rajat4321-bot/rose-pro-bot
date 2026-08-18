from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- BANNER IMAGE URL ---
BANNER_RULES = "https://files.catbox.moe/04jwbf.png"

# --- IN-MEMORY DATABASE FOR RULES SETTINGS ---
RULES_DB = {}          # {chat_id: "rules_text"}
PRIVATERULES_DB = {}   # {chat_id: bool}
RULES_BUTTON_DB = {}   # {chat_id: "button_name"}

# --- EXACT HELP TEXT FROM SCREENSHOT (NO MONOSPACE / NO COPY-TO-CLIPBOARD) ---
RULES_HELP_TEXT = (
    "**Rules**\n\n"
    "Every chat works with different rules; this module will help make those rules clearer!\n\n"
    "**User commands:**\n"
    "• /rules: Check the current chat rules.\n\n"
    "**Admin commands:**\n"
    "• /setrules <text>: Set the rules for this chat. Supports markdown, buttons, fillings, etc.\n"
    "• /privaterules <yes/no/on/off>: Enable/disable whether the rules should be sent in private.\n"
    "• /clearrules: Reset the chat rules to default.\n"
    "• /setrulesbutton: Set the rules button name when using {rules}.\n"
    "• /resetrulesbutton: Reset the rules button name from {rules} to default.\n\n"
    "**Examples:**\n"
    "- Get the unformatted rules text, to make them easier to edit.\n"
    "-> /rules noformat\n\n"
    "- Set the name of the button to use when using the {rules} filling.\n"
    "-> /setrulesbutton Press me for the chat rules"
)

# --- HELPER FUNCTIONS ---
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

# --- INLINE CALLBACK HANDLER (ONLY BACK BUTTON - NO FORMATTING BUTTON) ---

@Client.on_callback_query(filters.regex(r"^(help_rules|rules_help)$"))
async def rules_help_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{RULES_HELP_TEXT}\n[\u200b]({BANNER_RULES})"
    
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

# 1. CHECK RULES (/rules)
@Client.on_message(filters.command("rules"))
async def rules_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ Use /rules inside a group to check that group's rules!")

    chat_id = message.chat.id
    rules_text = RULES_DB.get(chat_id, "No rules have been set for this chat yet!")
    is_private = PRIVATERULES_DB.get(chat_id, False)

    # Handle noformat argument
    if len(message.command) > 1 and message.command[1].lower() in ["noformat", "raw"]:
        return await message.reply_text(f"```\n{rules_text}\n```", parse_mode=enums.ParseMode.MARKDOWN)

    # Private Rules Mode Handling
    if is_private:
        button_name = RULES_BUTTON_DB.get(chat_id, "Click here for rules")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(button_name, url=f"https://t.me/{client.me.username}?start=rules_{chat_id}")]
        ])
        return await message.reply_text(
            "Click the button below to view the rules in PM:",
            reply_markup=keyboard
        )

    await message.reply_text(
        f"**Rules for {message.chat.title}:**\n\n{rules_text}",
        parse_mode=enums.ParseMode.MARKDOWN
    )

# 2. SET RULES (/setrules)
@Client.on_message(filters.command("setrules"))
async def setrules_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to set rules.")

    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply_text("❌ Provide text or reply to a message to set as rules!")

    if message.reply_to_message:
        new_rules = message.reply_to_message.text or message.reply_to_message.caption or ""
    else:
        new_rules = message.text.split(None, 1)[1]

    RULES_DB[message.chat.id] = new_rules
    await message.reply_text("✅ Chat rules updated successfully!")

# 3. PRIVATE RULES TOGGLE (/privaterules)
@Client.on_message(filters.command("privaterules"))
async def privaterules_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to toggle private rules setting.")

    chat_id = message.chat.id
    args = message.command[1:]

    if not args:
        status = "ON" if PRIVATERULES_DB.get(chat_id, False) else "OFF"
        return await message.reply_text(f"Private Rules mode is currently: **{status}**")

    param = args[0].lower()
    if param in ["yes", "on", "true"]:
        PRIVATERULES_DB[chat_id] = True
        await message.reply_text("✅ Rules will now be sent in PM when users request them.")
    elif param in ["no", "off", "false"]:
        PRIVATERULES_DB[chat_id] = False
        await message.reply_text("✅ Rules will now be sent directly in the group.")
    else:
        await message.reply_text("Usage: `/privaterules <yes/no/on/off>`")

# 4. RESET RULES (/clearrules or /resetrules)
@Client.on_message(filters.command(["clearrules", "resetrules"]))
async def clearrules_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to reset rules.")

    RULES_DB.pop(message.chat.id, None)
    await message.reply_text("✅ Chat rules have been reset to default.")

# 5. SET RULES BUTTON NAME (/setrulesbutton)
@Client.on_message(filters.command("setrulesbutton"))
async def setrulesbutton_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to change rules button text.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Provide a button name! Example: `/setrulesbutton Read Rules`")

    btn_text = message.text.split(None, 1)[1]
    RULES_BUTTON_DB[message.chat.id] = btn_text
    await message.reply_text(f"✅ Rules button text updated to: **{btn_text}**")

# 6. RESET RULES BUTTON NAME (/resetrulesbutton)
@Client.on_message(filters.command("resetrulesbutton"))
async def resetrulesbutton_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to reset rules button text.")

    RULES_BUTTON_DB.pop(message.chat.id, None)
    await message.reply_text("✅ Rules button name reset to default.")
