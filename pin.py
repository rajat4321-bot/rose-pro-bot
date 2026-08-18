from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- BANNER IMAGE URL ---
BANNER_PIN = "https://files.catbox.moe/l0fswu.png"

# --- IN-MEMORY DATABASE FOR SETTINGS ---
ANTI_CHANNEL_PIN_DB = {} # {chat_id: bool}
CLEAN_LINKED_DB = {}       # {chat_id: bool}

# --- EXACT HELP TEXT FROM SCREENSHOT ---
PIN_HELP_TEXT = (
    "**Pin**\n\n"
    "All the pin related commands can be found here; keep your chat up to date on the latest news with a simple pinned message!\n\n"
    "**User commands:**\n"
    "• `/pinned`: Get the current pinned message.\n\n"
    "**Admin commands:**\n"
    "• `/pin`: Pin the message you replied to. Add 'loud' or 'notify' to send a notification to group members.\n"
    "• `/permapin <text>`: Pin a custom message through the bot. This message can contain markdown, buttons, and all the other cool features.\n"
    "• `/unpin`: Unpin the current pinned message. If used as a reply, unpins the replied to message.\n"
    "• `/unpinall`: Unpins all pinned messages.\n"
    "• `/antichannelpin <yes/no/on/off>`: Don't let telegram auto-pin linked channels. If no arguments are given, shows current setting.\n"
    "• `/cleanlinked <yes/no/on/off>`: Delete messages sent by the linked channel."
)

# --- HELPER FUNCTIONS ---
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

async def can_pin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status == ChatMemberStatus.OWNER:
            return True
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            return member.privileges.can_pin_messages
        return False
    except Exception:
        return False

# --- INLINE CALLBACK HANDLER ---

@Client.on_callback_query(filters.regex(r"^(help_pin|pin_help)$"))
async def pin_help_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{PIN_HELP_TEXT}\n[\u200b]({BANNER_PIN})"
    
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

# 1. GET PINNED MESSAGE (Group Only)
@Client.on_message(filters.command("pinned"))
async def pinned_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    chat = await client.get_chat(message.chat.id)
    if not chat.pinned_message:
        return await message.reply_text("There is no pinned message in this chat.")

    pinned_link = chat.pinned_message.link
    await message.reply_text(
        f"The current pinned message is [here]({pinned_link}).",
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.MARKDOWN
    )

# 2. PIN MESSAGE (Group Admins with Pin Rights)
@Client.on_message(filters.command("pin"))
async def pin_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await can_pin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need pin rights to use this command.")

    if not message.reply_to_message:
        return await message.reply_text("❌ Reply to a message to pin it!")

    disable_notification = True
    if len(message.command) > 1 and message.command[1].lower() in ["loud", "notify"]:
        disable_notification = False

    try:
        await client.pin_chat_message(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.id,
            disable_notification=disable_notification
        )
        await message.reply_text("✅ Successfully pinned the message!")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to pin message: `{e}`")

# 3. PERMAPIN CUSTOM MESSAGE (Group Admins)
@Client.on_message(filters.command("permapin"))
async def permapin_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await can_pin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need pin rights to use this command.")

    text_to_pin = ""
    if message.reply_to_message:
        text_to_pin = message.reply_to_message.text or message.reply_to_message.caption or ""
    elif len(message.command) > 1:
        text_to_pin = message.text.split(None, 1)[1]

    if not text_to_pin:
        return await message.reply_text("❌ Provide text or reply to a message to permapin!")

    try:
        sent_msg = await client.send_message(message.chat.id, text_to_pin)
        await client.pin_chat_message(message.chat.id, sent_msg.id, disable_notification=True)
    except RPCError as e:
        await message.reply_text(f"❌ Failed to permapin: `{e}`")

# 4. UNPIN MESSAGE (Group Admins)
@Client.on_message(filters.command("unpin"))
async def unpin_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await can_pin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need pin rights to use this command.")

    try:
        if message.reply_to_message:
            await client.unpin_chat_message(message.chat.id, message.reply_to_message.id)
            await message.reply_text("✅ Successfully unpinned the replied message.")
        else:
            await client.unpin_chat_message(message.chat.id)
            await message.reply_text("✅ Successfully unpinned the last pinned message.")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to unpin message: `{e}`")

# 5. UNPIN ALL MESSAGES (Group Admins)
@Client.on_message(filters.command("unpinall"))
async def unpinall_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to unpin all messages.")

    try:
        await client.unpin_all_chat_messages(message.chat.id)
        await message.reply_text("✅ Successfully unpinned all messages in this chat.")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to unpin all messages: `{e}`")

# 6. ANTI CHANNEL PIN TOGGLE (Group Admins)
@Client.on_message(filters.command("antichannelpin"))
async def antichannelpin_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to edit this setting.")

    chat_id = message.chat.id
    args = message.command[1:]

    if not args:
        status = "ON" if ANTI_CHANNEL_PIN_DB.get(chat_id, False) else "OFF"
        return await message.reply_text(f"Anti Channel Pin mode is currently: **{status}**")

    param = args[0].lower()
    if param in ["yes", "on", "true"]:
        ANTI_CHANNEL_PIN_DB[chat_id] = True
        await message.reply_text("✅ Anti Channel Pin enabled! Auto-pinned posts from linked channels will be unpinned.")
    elif param in ["no", "off", "false"]:
        ANTI_CHANNEL_PIN_DB[chat_id] = False
        await message.reply_text("✅ Anti Channel Pin disabled.")
    else:
        await message.reply_text("Usage: `/antichannelpin <yes/no/on/off>`")

# 7. CLEAN LINKED TOGGLE (Group Admins)
@Client.on_message(filters.command("cleanlinked"))
async def cleanlinked_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to edit this setting.")

    chat_id = message.chat.id
    args = message.command[1:]

    if not args:
        status = "ON" if CLEAN_LINKED_DB.get(chat_id, False) else "OFF"
        return await message.reply_text(f"Clean Linked Channel messages mode is currently: **{status}**")

    param = args[0].lower()
    if param in ["yes", "on", "true"]:
        CLEAN_LINKED_DB[chat_id] = True
        await message.reply_text("✅ Clean Linked enabled! Automatic posts from linked channels will be deleted.")
    elif param in ["no", "off", "false"]:
        CLEAN_LINKED_DB[chat_id] = False
        await message.reply_text("✅ Clean Linked disabled.")
    else:
        await message.reply_text("Usage: `/cleanlinked <yes/no/on/off>`")

# --- AUTOMATIC ENFORCERS (AUTO UNPIN / DELETE LINKED MESSAGES) ---

@Client.on_message(filters.linked_channel & ~filters.private, group=10)
async def handle_linked_channel_posts(client: Client, message: Message):
    chat_id = message.chat.id

    if CLEAN_LINKED_DB.get(chat_id, False):
        try:
            await message.delete()
            return
        except RPCError:
            pass

    if ANTI_CHANNEL_PIN_DB.get(chat_id, False):
        try:
            await client.unpin_chat_message(chat_id, message.id)
        except RPCError:
            pass
