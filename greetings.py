import re
from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- DEDICATED BANNER IMAGE URL ---
BANNER_GREETINGS = "https://files.catbox.moe/bwjq31.png"

# --- IN-MEMORY DATABASE FOR GREETINGS ---
GREETINGS_DB = {}

# --- HELP TEXT CONTENT ---
GREETINGS_HELP_TEXT = (
    "**Greetings**\n\n"
    "Give your members a warm welcome with the greetings module! "
    "Or a sad goodbye... Depends!\n\n"
    "**Admin commands:**\n"
    "• `/welcome [yes/no/on/off]`: Enable or disable welcome messages.\n"
    "• `/goodbye [yes/no/on/off]`: Enable or disable goodbye messages.\n"
    "• `/setwelcome [text]`: Set a new welcome message. Supports markdown, buttons, and fillings.\n"
    "• `/resetwelcome`: Reset the welcome message to default.\n"
    "• `/setgoodbye [text]`: Set a new goodbye message. Supports markdown, buttons, and fillings.\n"
    "• `/resetgoodbye`: Reset the goodbye message to default.\n"
    "• `/cleanwelcome [yes/no/on/off]`: Delete old welcome messages automatically."
)

# --- HELPER FUNCTION FOR FILLINGS ---
def parse_fillings(text: str, message: Message) -> str:
    user = message.from_user
    chat = message.chat
    
    first_name = user.first_name if user else "User"
    last_name = user.last_name if user and user.last_name else ""
    full_name = f"{first_name} {last_name}".strip()
    username = f"@{user.username}" if user and user.username else first_name
    mention = user.mention if user else first_name
    user_id = str(user.id) if user else "0"
    chat_name = chat.title if chat.title else "this group"

    parsed = text.replace("{first}", first_name)
    parsed = parsed.replace("{last}", last_name)
    parsed = parsed.replace("{fullname}", full_name)
    parsed = parsed.replace("{username}", username)
    parsed = parsed.replace("{mention}", mention)
    parsed = parsed.replace("{id}", user_id)
    parsed = parsed.replace("{chatname}", chat_name)
    return parsed

# --- INLINE CALLBACK HANDLER ---

@Client.on_callback_query(filters.regex(r"^help_greetings$"))
async def help_greetings_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{GREETINGS_HELP_TEXT}\n[\u200b]({BANNER_GREETINGS})"
    
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

@Client.on_message(filters.command("welcome"))
async def toggle_welcome(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to execute this command.")

    args = message.command[1:]
    if not args:
        return await message.reply_text(
            "Usage: `/welcome yes` or `/welcome no`",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    state = args[0].lower()
    chat_id = message.chat.id
    if chat_id not in GREETINGS_DB:
        GREETINGS_DB[chat_id] = {"welcome_enabled": True, "welcome_text": "Hey {mention}, welcome to **{chatname}**!", "goodbye_enabled": True, "goodbye_text": "Goodbye {first}!"}

    if state in ["yes", "on", "true"]:
        GREETINGS_DB[chat_id]["welcome_enabled"] = True
        await message.reply_text("✅ Welcome messages enabled for this chat.")
    elif state in ["no", "off", "false"]:
        GREETINGS_DB[chat_id]["welcome_enabled"] = False
        await message.reply_text("✅ Welcome messages disabled for this chat.")
    else:
        await message.reply_text("Invalid argument. Use `yes` or `no`.")

@Client.on_message(filters.command("goodbye"))
async def toggle_goodbye(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to execute this command.")

    args = message.command[1:]
    if not args:
        return await message.reply_text(
            "Usage: `/goodbye yes` or `/goodbye no`",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    state = args[0].lower()
    chat_id = message.chat.id
    if chat_id not in GREETINGS_DB:
        GREETINGS_DB[chat_id] = {"welcome_enabled": True, "welcome_text": "Hey {mention}, welcome to **{chatname}**!", "goodbye_enabled": True, "goodbye_text": "Goodbye {first}!"}

    if state in ["yes", "on", "true"]:
        GREETINGS_DB[chat_id]["goodbye_enabled"] = True
        await message.reply_text("✅ Goodbye messages enabled for this chat.")
    elif state in ["no", "off", "false"]:
        GREETINGS_DB[chat_id]["goodbye_enabled"] = False
        await message.reply_text("✅ Goodbye messages disabled for this chat.")
    else:
        await message.reply_text("Invalid argument. Use `yes` or `no`.")

@Client.on_message(filters.command("setwelcome"))
async def set_welcome_text(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to execute this command.")

    raw_text = message.text.split(None, 1)[1] if len(message.text.split(None, 1)) > 1 else ""
    if not raw_text and not message.reply_to_message:
        return await message.reply_text("Usage: `/setwelcome text` or reply to a message.")

    chat_id = message.chat.id
    if chat_id not in GREETINGS_DB:
        GREETINGS_DB[chat_id] = {"welcome_enabled": True, "welcome_text": "", "goodbye_enabled": True, "goodbye_text": "Goodbye {first}!"}

    text_to_save = raw_text if raw_text else (message.reply_to_message.text or message.reply_to_message.caption or "Welcome!")
    GREETINGS_DB[chat_id]["welcome_text"] = text_to_save
    await message.reply_text("✅ Custom welcome message updated successfully!")

@Client.on_message(filters.command("resetwelcome"))
async def reset_welcome(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to execute this command.")

    chat_id = message.chat.id
    default_text = "Hey {mention}, welcome to **{chatname}**!"
    if chat_id in GREETINGS_DB:
        GREETINGS_DB[chat_id]["welcome_text"] = default_text
    await message.reply_text("✅ Reset welcome message to default.")

@Client.on_message(filters.command("setgoodbye"))
async def set_goodbye_text(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to execute this command.")

    raw_text = message.text.split(None, 1)[1] if len(message.text.split(None, 1)) > 1 else ""
    if not raw_text and not message.reply_to_message:
        return await message.reply_text("Usage: `/setgoodbye text` or reply to a message.")

    chat_id = message.chat.id
    if chat_id not in GREETINGS_DB:
        GREETINGS_DB[chat_id] = {"welcome_enabled": True, "welcome_text": "Hey {mention}!", "goodbye_enabled": True, "goodbye_text": ""}

    text_to_save = raw_text if raw_text else (message.reply_to_message.text or message.reply_to_message.caption or "Goodbye!")
    GREETINGS_DB[chat_id]["goodbye_text"] = text_to_save
    await message.reply_text("✅ Custom goodbye message updated successfully!")

@Client.on_message(filters.command("resetgoodbye"))
async def reset_goodbye(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to execute this command.")

    chat_id = message.chat.id
    default_text = "Goodbye {first}, we will miss you!"
    if chat_id in GREETINGS_DB:
        GREETINGS_DB[chat_id]["goodbye_text"] = default_text
    await message.reply_text("✅ Reset goodbye message to default.")

# --- REAL EVENT HANDLERS ---

@Client.on_message(filters.new_chat_members)
async def welcome_event_handler(client: Client, message: Message):
    chat_id = message.chat.id
    conf = GREETINGS_DB.get(chat_id, {
        "welcome_enabled": True,
        "welcome_text": "Hey {mention}, welcome to **{chatname}**!"
    })

    if not conf.get("welcome_enabled", True):
        return

    raw_text = conf.get("welcome_text", "Hey {mention}, welcome to **{chatname}**!")
    final_text = parse_fillings(raw_text, message)
    
    await client.send_message(chat_id=chat_id, text=final_text, disable_web_page_preview=False)

@Client.on_message(filters.left_chat_member)
async def goodbye_event_handler(client: Client, message: Message):
    chat_id = message.chat.id
    conf = GREETINGS_DB.get(chat_id, {
        "goodbye_enabled": True,
        "goodbye_text": "Goodbye {first}, we will miss you!"
    })

    if not conf.get("goodbye_enabled", True):
        return

    raw_text = conf.get("goodbye_text", "Goodbye {first}, we will miss you!")
    final_text = parse_fillings(raw_text, message)
    
    await client.send_message(chat_id=chat_id, text=final_text, disable_web_page_preview=False)
