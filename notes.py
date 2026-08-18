from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- BANNER IMAGE URL ---
BANNER_NOTES = "https://files.catbox.moe/dmhclh.png"

# --- DATABASE IN-MEMORY FOR NOTES ---
# Structure: {chat_id: {note_name: {"text": str, "file_id": str/None, "type": str}}}
NOTES_DB = {}
PRIVATE_NOTES_SETTINGS = {} # {chat_id: bool}

# --- EXACT HELP TEXT FROM SCREENSHOT ---
NOTES_HELP_TEXT = (
    "**Notes**\n\n"
    "Save data for future users with notes!\n\n"
    "Notes are great to save random tidbits of information; a phone number, a nice gif, a funny picture - anything!\n\n"
    "**User commands:**\n"
    "• `/get <notename>`: Get a note.\n"
    "• `#notename`: Same as `/get`.\n\n"
    "**Admin commands:**\n"
    "• `/save <notename> <note text>`: Save a new note called \"word\". Replying to a message will save that message. Even works on media!\n"
    "• `/clear <notename>`: Delete the associated note.\n"
    "• `/notes`: List all notes in the current chat.\n"
    "• `/saved`: Same as `/notes`.\n"
    "• `/clearall`: Delete ALL notes in a chat. This cannot be undone.\n"
    "• `/privatenotes`: Whether or not to send notes in PM. Will send a message with a button which users can click to get the note in PM."
)

# --- ADMIN CHECKER HELPER ---
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

# --- INLINE CALLBACK HANDLERS (MATCHES help_notes & help_back) ---

@Client.on_callback_query(filters.regex(r"^(help_notes|notes_help)$"))
async def notes_help_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{NOTES_HELP_TEXT}\n[\u200b]({BANNER_NOTES})"
    
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

@Client.on_callback_query(filters.regex(r"^get_note_pm_(.+)"))
async def get_note_pm_cb(client: Client, callback: CallbackQuery):
    note_name = callback.matches[0].group(1)
    chat_id = callback.message.chat.id
    
    notes = NOTES_DB.get(chat_id, {})
    if note_name in notes:
        note = notes[note_name]
        try:
            if note["type"] == "text":
                await client.send_message(callback.from_user.id, note["text"])
            else:
                await client.send_cached_media(callback.from_user.id, note["file_id"], caption=note.get("text", ""))
            await callback.answer("✅ Note sent to your PM!", show_alert=True)
        except Exception:
            await callback.answer("❌ Please start me in PM first so I can send you the note!", show_alert=True)
    else:
        await callback.answer("❌ Note no longer exists.", show_alert=True)

# --- REAL WORKING COMMAND HANDLERS WITH STRICT SCOPE ENFORCEMENT ---

# 1. SAVE NOTE (Group/Supergroup Admins Only)
@Client.on_message(filters.command("save"))
async def save_note_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to save notes.")

    args = message.command[1:]
    if not args and not message.reply_to_message:
        return await message.reply_text("Usage: `/save <notename> <note text>` or reply to a message with `/save <notename>`")

    note_name = args[0].lower() if args else None
    if not note_name:
        return await message.reply_text("❌ Please specify a note name.")

    chat_id = message.chat.id
    if chat_id not in NOTES_DB:
        NOTES_DB[chat_id] = {}

    if message.reply_to_message:
        replied = message.reply_to_message
        if replied.text:
            NOTES_DB[chat_id][note_name] = {"type": "text", "text": replied.text}
        elif replied.media:
            media_type = replied.media.value
            file_id = getattr(replied, media_type).file_id
            caption = replied.caption or ""
            NOTES_DB[chat_id][note_name] = {"type": "media", "file_id": file_id, "text": caption}
    else:
        if len(args) < 2:
            return await message.reply_text("❌ Please provide text for the note.")
        note_text = " ".join(args[1:])
        NOTES_DB[chat_id][note_name] = {"type": "text", "text": note_text}

    await message.reply_text(f"✅ Saved note `#{note_name}`!", parse_mode=enums.ParseMode.MARKDOWN)

# 2. GET NOTE (Group Only)
@Client.on_message(filters.command("get"))
async def get_note_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ Use `#notename` or `/get` directly inside groups.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/get <notename>`")

    note_name = args[0].lower()
    chat_id = message.chat.id
    notes = NOTES_DB.get(chat_id, {})

    if note_name not in notes:
        return await message.reply_text("❌ This note doesn't exist.")

    # Check Private Notes Mode
    is_pm_mode = PRIVATE_NOTES_SETTINGS.get(chat_id, False)
    if is_pm_mode:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Click to get Note in PM", url=f"https://t.me/{client.me.username}?start=note_{chat_id}_{note_name}")]
        ])
        return await message.reply_text(f"Click the button below to get the note **{note_name}** in PM:", reply_markup=keyboard)

    note = notes[note_name]
    if note["type"] == "text":
        await message.reply_text(note["text"])
    else:
        await message.reply_cached_media(note["file_id"], caption=note.get("text", ""))

# 3. HASHTAG TRIGGER (#notename - Group Only)
@Client.on_message(filters.regex(r"^#(\w+)") & ~filters.private)
async def hashtag_note_cmd(client: Client, message: Message):
    note_name = message.matches[0].group(1).lower()
    chat_id = message.chat.id
    notes = NOTES_DB.get(chat_id, {})

    if note_name in notes:
        is_pm_mode = PRIVATE_NOTES_SETTINGS.get(chat_id, False)
        if is_pm_mode:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Click to get Note in PM", url=f"https://t.me/{client.me.username}?start=note_{chat_id}_{note_name}")]
            ])
            return await message.reply_text(f"Click the button below to get the note **{note_name}** in PM:", reply_markup=keyboard)

        note = notes[note_name]
        if note["type"] == "text":
            await message.reply_text(note["text"])
        else:
            await message.reply_cached_media(note["file_id"], caption=note.get("text", ""))

# 4. LIST NOTES (/notes & /saved - Group Only)
@Client.on_message(filters.command(["notes", "saved"]))
async def list_notes_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ Note list is group-specific. Use this command in a group.")

    chat_id = message.chat.id
    notes = NOTES_DB.get(chat_id, {})

    if not notes:
        return await message.reply_text("No notes saved in this chat.")

    notes_list = "\n".join([f"• `#{name}`" for name in notes.keys()])
    await message.reply_text(f"**Notes in {message.chat.title}:**\n\n{notes_list}", parse_mode=enums.ParseMode.MARKDOWN)

# 5. CLEAR NOTE (Group Admins Only)
@Client.on_message(filters.command("clear"))
async def clear_note_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to clear notes.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/clear <notename>`")

    note_name = args[0].lower()
    chat_id = message.chat.id

    if chat_id in NOTES_DB and note_name in NOTES_DB[chat_id]:
        del NOTES_DB[chat_id][note_name]
        await message.reply_text(f"✅ Removed note `#{note_name}`.", parse_mode=enums.ParseMode.MARKDOWN)
    else:
        await message.reply_text("❌ That note does not exist.")

# 6. CLEAR ALL NOTES (Group Admins Only)
@Client.on_message(filters.command("clearall"))
async def clearall_notes_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to clear all notes.")

    chat_id = message.chat.id
    if chat_id in NOTES_DB and NOTES_DB[chat_id]:
        NOTES_DB[chat_id].clear()
        await message.reply_text("✅ Deleted ALL notes in this chat.")
    else:
        await message.reply_text("No notes to clear in this chat.")

# 7. TOGGLE PRIVATE NOTES (Group Admins Only)
@Client.on_message(filters.command("privatenotes"))
async def privatenotes_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to configure private notes.")

    args = message.command[1:]
    chat_id = message.chat.id

    if not args:
        current = PRIVATE_NOTES_SETTINGS.get(chat_id, False)
        status = "ON" if current else "OFF"
        return await message.reply_text(f"Private notes mode is currently: **{status}**")

    param = args[0].lower()
    if param in ["on", "yes", "true"]:
        PRIVATE_NOTES_SETTINGS[chat_id] = True
        await message.reply_text("✅ Private notes enabled. Notes will now be delivered via PM buttons.")
    elif param in ["off", "no", "false"]:
        PRIVATE_NOTES_SETTINGS[chat_id] = False
        await message.reply_text("✅ Private notes disabled. Notes will be sent directly in the group.")
    else:
        await message.reply_text("Usage: `/privatenotes <on/off>`")
