import re
from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- DEDICATED BANNER IMAGE URLS ---
BANNER_LOCKS_MAIN = "https://files.catbox.moe/ltse7h.png"
BANNER_LOCKS_EXAMPLES = "https://files.catbox.moe/4usb44.png"
BANNER_LOCKS_DESCRIPTIONS = "https://files.catbox.moe/7sr8li.png"

# --- IN-MEMORY DATABASE FOR LOCKS & ALLOWLIST ---
# LOCKS_DB[chat_id] = {
#     "locks": {"sticker": True, "url": False},
#     "warns": True,
#     "allowlist": []
# }
LOCKS_DB = {}

# --- ALL LOCKABLE TYPES ---
SUPPORTED_LOCKS = [
    "all", "album", "audio", "bot", "button", "command", "contact",
    "document", "email", "emoji", "emojipack", "forward", "game",
    "gif", "inline", "invitelink", "location", "phone", "photo",
    "polls", "spoiler", "sticker", "text", "url", "video", "videonote", "voice"
]

# --- HELP TEXT CONTENT ---
LOCKS_MAIN_HELP = (
    "**Locks**\n\n"
    "Do stickers annoy you? Or want to avoid people sharing links or pictures? "
    "You're in the right place!\n\n"
    "The locks module allows you to lock away some common items in the Telegram world; "
    "the bot will automatically delete them!\n\n"
    "**Admin commands:**\n"
    "• `/lock <item(s)>`: Lock one or more items. Now, only admins can use this type!\n"
    "• `/unlock <item(s)>`: Unlock one or more items. Everyone can use this type again!\n"
    "• `/locks`: List currently locked items.\n"
    "• `/lockwarns [yes/no/on/off]`: Enable or disable whether a user should be warned when using a locked item.\n"
    "• `/locktypes`: Show the list of all lockable items.\n"
    "• `/allowlist <url/id/command/@username(s)>`: Allowlist a URL, group ID, channel, @bot, command, cashtag, or stickerpack link to stop them being deleted.\n"
    "• `/rmallowlist <url/id/@channelname(s)>`: Remove an item from the allowlist.\n"
    "• `/rmallowlistall`: Remove all allowlisted items."
)

LOCKS_EXAMPLES_HELP = (
    "**Example Commands**\n\n"
    "Locks are a powerful tool, with lots of different options. So here are a few examples to get you started and familiar on how exactly to use them.\n\n"
    "**Examples:**\n"
    "• Stop all users from sending stickers with:\n"
    "`/lock sticker`\n\n"
    "• You can lock/unlock multiple items by chaining them:\n"
    "`/lock sticker photo gif video`\n\n"
    "• Want a harsher punishment for certain actions? Set a custom lock action:\n"
    "`/lock invitelink ### no promoting other chats (ban)`\n\n"
    "• Reset the custom lock action and reason for a single item:\n"
    "`/lock emoji ###`\n\n"
    "• Reset all custom lock actions and reasons:\n"
    "`/lock all ###`\n\n"
    "• List all locks at once:\n"
    "`/locks list`\n\n"
    "• To allow forwards from a specific channel, e.g. @RoseSupport, you can allowlist it:\n"
    "`/allowlist @ather`\n\n"
    "• Allow specific sticker packs:\n"
    "`/allowlist t.me/addstickers/Pinup_Girl`"
)

LOCKS_DESCRIPTIONS_HELP = (
    "**Lock Descriptions**\n\n"
    "There are lots of different locks, and some of them might not be obvious. "
    "This section aims to explain each lock in detail.\n\n"
    "**Types:**\n"
    "• `all`: All messages.\n"
    "• `album`: Media groups (documents, photos, etc).\n"
    "• `audio`: Audio files.\n"
    "• `bot`: Messages sent by bots.\n"
    "• `button`: Inline buttons added to messages.\n"
    "• `command`: Telegram bot commands.\n"
    "• `contact`: Contact card messages.\n"
    "• `document`: Documents and general files.\n"
    "• `email`: Messages containing email addresses.\n"
    "• `emoji`: Custom premium emojis.\n"
    "• `emojipack`: Custom emoji packs.\n"
    "• `forward`: Messages forwarded from other chats/channels.\n"
    "• `game`: Telegram bot game messages.\n"
    "• `gif`: Animated GIFs.\n"
    "• `inline`: Messages sent via inline bots.\n"
    "• `invitelink`: Telegram group and channel invite links.\n"
    "• `location`: Location sharing messages.\n"
    "• `phone`: Phone numbers in text messages.\n"
    "• `photo`: Photo and image messages.\n"
    "• `polls`: Telegram poll messages.\n"
    "• `spoiler`: Text with spoiler formatting.\n"
    "• `sticker`: Regular stickers.\n"
    "• `text`: Pure text messages.\n"
    "• `url`: Web URLs and hyperlinks.\n"
    "• `video`: Video files.\n"
    "• `videonote`: Quick round video notes.\n"
    "• `voice`: Voice message notes."
)

# --- HELPER FUNCTIONS ---

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

def get_chat_locks(chat_id: int) -> dict:
    if chat_id not in LOCKS_DB:
        LOCKS_DB[chat_id] = {"locks": {}, "warns": True, "allowlist": []}
    return LOCKS_DB[chat_id]

# --- INLINE NAVIGATION CALLBACK HANDLERS ---

@Client.on_callback_query(filters.regex(r"^help_locks$"))
async def help_locks_main_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Example commands", callback_data="locks_examples"),
            InlineKeyboardButton("Lock descriptions", callback_data="locks_descriptions")
        ],
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{LOCKS_MAIN_HELP}\n[\u200b]({BANNER_LOCKS_MAIN})"
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

@Client.on_callback_query(filters.regex(r"^locks_examples$"))
async def help_locks_examples_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_locks")]
    ])
    full_text = f"{LOCKS_EXAMPLES_HELP}\n[\u200b]({BANNER_LOCKS_EXAMPLES})"
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

@Client.on_callback_query(filters.regex(r"^locks_descriptions$"))
async def help_locks_descriptions_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_locks")]
    ])
    full_text = f"{LOCKS_DESCRIPTIONS_HELP}\n[\u200b]({BANNER_LOCKS_DESCRIPTIONS})"
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

# --- COMMAND HANDLERS WITH STRICT SCOPE ENFORCEMENT ---

@Client.on_message(filters.command("lock"))
async def lock_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to lock items.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/lock <item(s)>` (e.g., `/lock sticker photo`)", parse_mode=enums.ParseMode.MARKDOWN)

    chat_data = get_chat_locks(message.chat.id)
    locked_items = []
    
    for item in args:
        item_lower = item.lower()
        if item_lower in SUPPORTED_LOCKS:
            chat_data["locks"][item_lower] = True
            locked_items.append(item_lower)

    if locked_items:
        await message.reply_text(f"✅ Locked: `{', '.join(locked_items)}`", parse_mode=enums.ParseMode.MARKDOWN)
    else:
        await message.reply_text("❌ No valid lockable items provided. Use `/locktypes` to check available types.", parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("unlock"))
async def unlock_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to unlock items.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/unlock <item(s)>` (e.g., `/unlock sticker photo`)", parse_mode=enums.ParseMode.MARKDOWN)

    chat_data = get_chat_locks(message.chat.id)
    unlocked_items = []

    for item in args:
        item_lower = item.lower()
        if item_lower in SUPPORTED_LOCKS:
            chat_data["locks"][item_lower] = False
            unlocked_items.append(item_lower)

    if unlocked_items:
        await message.reply_text(f"✅ Unlocked: `{', '.join(unlocked_items)}`", parse_mode=enums.ParseMode.MARKDOWN)
    else:
        await message.reply_text("❌ No valid items provided to unlock.", parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("locks"))
async def locks_list_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    chat_data = get_chat_locks(message.chat.id)
    active_locks = [k for k, v in chat_data["locks"].items() if v]

    if active_locks:
        text = "**Currently locked items in this chat:**\n" + "\n".join([f"• `{item}`" for item in active_locks])
    else:
        text = "There are no locked items in this chat."

    await message.reply_text(text, parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("locktypes"))
async def locktypes_cmd(client: Client, message: Message):
    text = "**Available lock types:**\n" + ", ".join([f"`{t}`" for t in SUPPORTED_LOCKS])
    await message.reply_text(text, parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("lockwarns"))
async def lockwarns_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to change lock warning settings.")

    args = message.command[1:]
    chat_data = get_chat_locks(message.chat.id)

    if not args:
        status = "enabled" if chat_data["warns"] else "disabled"
        return await message.reply_text(f"Lock warnings are currently `{status}`.", parse_mode=enums.ParseMode.MARKDOWN)

    state = args[0].lower()
    if state in ["yes", "on", "true"]:
        chat_data["warns"] = True
        await message.reply_text("✅ Lock warnings enabled.")
    elif state in ["no", "off", "false"]:
        chat_data["warns"] = False
        await message.reply_text("✅ Lock warnings disabled.")
    else:
        await message.reply_text("Invalid argument. Use `on` or `off`.", parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("allowlist"))
async def allowlist_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to modify the allowlist.")

    args = message.command[1:]
    chat_data = get_chat_locks(message.chat.id)

    if not args:
        if chat_data["allowlist"]:
            text = "**Allowlisted items:**\n" + "\n".join([f"• `{item}`" for item in chat_data["allowlist"]])
        else:
            text = "The allowlist is currently empty."
        return await message.reply_text(text, parse_mode=enums.ParseMode.MARKDOWN)

    for item in args:
        if item not in chat_data["allowlist"]:
            chat_data["allowlist"].append(item)

    await message.reply_text(f"✅ Added `{len(args)}` item(s) to the allowlist.", parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("rmallowlist"))
async def rmallowlist_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to modify the allowlist.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: `/rmallowlist <item(s)>`", parse_mode=enums.ParseMode.MARKDOWN)

    chat_data = get_chat_locks(message.chat.id)
    removed = 0
    for item in args:
        if item in chat_data["allowlist"]:
            chat_data["allowlist"].remove(item)
            removed += 1

    await message.reply_text(f"✅ Removed `{removed}` item(s) from the allowlist.", parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command("rmallowlistall"))
async def rmallowlistall_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command is group-only. Please use it inside a Telegram group.")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to clear the allowlist.")

    chat_data = get_chat_locks(message.chat.id)
    chat_data["allowlist"].clear()
    await message.reply_text("✅ Cleared all items from the allowlist.", parse_mode=enums.ParseMode.MARKDOWN)

# --- REAL EVENT ENFORCEMENT ENGINE (AUTO DELETION HANDLER) ---

@Client.on_message(filters.group & ~filters.me, group=1)
async def lock_checker_engine(client: Client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    chat_data = LOCKS_DB.get(chat_id)
    if not chat_data or not chat_data.get("locks"):
        return

    # Skip enforcement for Admins
    if await is_admin(client, chat_id, message.from_user.id):
        return

    locks = chat_data["locks"]
    should_delete = False
    lock_type_hit = ""

    # Check lock types
    if locks.get("all", False):
        should_delete = True
        lock_type_hit = "all"
    elif locks.get("sticker", False) and message.sticker:
        should_delete = True
        lock_type_hit = "sticker"
    elif locks.get("photo", False) and message.photo:
        should_delete = True
        lock_type_hit = "photo"
    elif locks.get("video", False) and message.video:
        should_delete = True
        lock_type_hit = "video"
    elif locks.get("audio", False) and message.audio:
        should_delete = True
        lock_type_hit = "audio"
    elif locks.get("document", False) and message.document:
        should_delete = True
        lock_type_hit = "document"
    elif locks.get("forward", False) and message.forward_date:
        should_delete = True
        lock_type_hit = "forward"
    elif locks.get("contact", False) and message.contact:
        should_delete = True
        lock_type_hit = "contact"
    elif locks.get("location", False) and message.location:
        should_delete = True
        lock_type_hit = "location"
    elif locks.get("url", False) and (message.text or message.caption):
        content = message.text or message.caption
        if "http://" in content or "https://" in content or "t.me/" in content:
            should_delete = True
            lock_type_hit = "url"

    if should_delete:
        try:
            await message.delete()
            if chat_data.get("warns", True):
                warn_msg = await client.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ {message.from_user.mention}, sending `{lock_type_hit}` is locked in this chat!",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
        except RPCError:
            pass
