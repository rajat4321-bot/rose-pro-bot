import re
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    ChatPermissions
)
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError

# Alag-alag Banner Images (Yahan apni dono alag URLs daal lein)
MAIN_BANNER_URL = "https://files.catbox.moe/itcyv8.png"  # Main Blocklist Banner
EXAMPLES_BANNER_URL = "https://files.catbox.moe/ggq4sn.png"  # How to use / Examples Banner

# In-memory storage structure
BLOCKLIST_DATA = {}

BLOCKLIST_HELP_TEXT = (
    "**Blocklists**\n\n"
    "Want to stop people asking stupid questions? Or ban anyone saying censored words? Blocklists is the module for you!\n\n"
    "From blocking rude words, filenames/extensions, to specific email, everything is possible.\n\n"
    "**Admin commands:**\n"
    "• `/addblocklist <blocklist trigger> <reason>`: Add a blocklist trigger. You can blocklist an entire sentence by putting it in \"quotes\".\n"
    "• `/unblocklist <blocklist trigger>`: Remove a blocklist trigger.\n"
    "• `/rmblocklist`: Remove all blocklist triggers - chat creator only.\n"
    "• `/blocklist`: List all blocklisted items.\n"
    "• `/blocklistmode <blocklist mode>`: Set the desired action to take when someone says a blocklisted item. Available: nothing/ban/mute/kick/warn/tban/tmute.\n"
    "• `/blocklistdelete <yes/no/on/off>`: Set whether blocklisted messages should be deleted. Default: on.\n"
    "• `/setblocklistreason <reason>`: Set the default blocklist reason to warn people with.\n"
    "• `/resetblocklistreason`: Reset the default blocklist reason to default - nothing.\n\n"
    "**Top tip:**\n"
    "Blocklists allow you to use some modifiers to match 'unknown' characters. The following patterns can be used:\n"
    "• `?` matches a single occurrence of any non-whitespace character.\n"
    "• `*` matches any number of any non-whitespace character. If you want to blocklist urls, this will allow you to match the full thing.\n"
    "• `**` matches any number of any character (including spaces)."
)

BLOCKLIST_EXAMPLES_TEXT = (
    "**Blocklist Process/Examples**\n\n"
    "If you're still unclear on how blocklists work, here are some examples you can copy:\n\n"
    "**Unwarn/unblocklist commands:**\n"
    "• Automatically warn someone when any blocklisted word is said.\n"
    "  `/blocklistmode warn`\n\n"
    "• Temporarily blocklist words for a single offense; users that say this will get a 10-minute to 24-hour ban, instead of standard action:\n"
    "  `/addblocklist \"bad word\" 10m` or `/addblocklist \"bad word\" 1d` or `/addblocklist \"bad word\"`\n\n"
    "• Add a custom reason for the blocklist. This would delete any messages matching the trigger.\n"
    "  `/addblocklist \"bad word\" You said a bad word!`\n\n"
    "• Add multiple blocklist triggers at once by separating/wrapping in brackets, and separating with commas:\n"
    "  `/addblocklist (word1, word2, word3) Stop saying bad words!`\n\n"
    "• Stop any `.png` links followed by exactly three characters, to block e.g. `.png?raw=true`:\n"
    "  `/addblocklist \"http*???.png\" We don't like 3-char png parameters!`\n\n"
    "• Stop any `.png` links using `*` for wildcard to match any character:\n"
    "  `/addblocklist \"http*.png\" We don't like png parameters!`\n\n"
    "• You example can be used to stop \"follow me on PC or office app\" by blocking full link sent to chat, avoiding spam words:\n"
    "  `/addblocklist \"http*telegram*\" No promoting Telegram channels!`\n\n"
    "• Stop people sending zip files, by blocklisting `.zip`:\n"
    "  `/addblocklist \"*.zip\" Zip files are not allowed here.`\n\n"
    "• Stop people asking for `.apk` files by blocklisting `.apk`:\n"
    "  `/addblocklist \"*.apk\" APKs are not allowed here.`\n\n"
    "• Stop forwards from a channel by adding:\n"
    "  `/addblocklist \"forward:channel\" Forwards from channels are not allowed here.`\n\n"
    "• Stop messages that contain a specific user ID:\n"
    "  `/addblocklist \"user:12345678\" Messages from this user are not allowed here.`\n\n"
    "• Stop messages that start with certain prefixes:\n"
    "  `/addblocklist \"prefix:!\" Auto-delete messages that start with '!'`\n\n"
    "• Stop messages containing visually similar words, for example:\n"
    "  `/addblocklist \"badw?rd\" You cannot use variations of bad words!`\n\n"
    "• Stop any 🐱 emoji or any sticker containing it:\n"
    "  `/addblocklist 🐱 This emoji is not allowed here.`\n\n"
    "• Blocklist a stickerpack, simply reply to a sticker with your command:\n"
    "  `/addblocklist (replying to a sticker)`\n\n"
    "• Blocklist a stickerpack and assign a reason, reply the sticker with:\n"
    "  `/addblocklist \"Reason\" (replying to a sticker)`\n\n"
    "• Blocklist custom emojis/pack in a message, reply to the message and specify `/addblocklist`:\n"
    "  `/addblocklist (replying to custom emoji message)`\n\n"
    "• To stop a single blocklist item from deleting messages when mentioned, set delete off:\n"
    "  `/blocklistdelete off`\n\n"
    "• If you've disabled blocklist delete, users start to configure some items to still delete:\n"
    "  `/addblocklist (word) (delete:yes) Stop this specific phrase!`"
)

BLOCKLIST_CMDS = [
    "addblocklist", "unblocklist", "rmblocklist", "blocklist",
    "blocklistmode", "blocklistdelete", "setblocklistreason", "resetblocklistreason"
]

def get_chat_config(chat_id: int):
    if chat_id not in BLOCKLIST_DATA:
        BLOCKLIST_DATA[chat_id] = {
            "triggers": {},
            "mode": "nothing",
            "delete": True,
            "reason": None
        }
    return BLOCKLIST_DATA[chat_id]

async def is_user_admin(client: Client, message: Message) -> bool:
    if message.chat.type.name == "PRIVATE":
        return False
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

async def is_user_owner(client: Client, message: Message) -> bool:
    if message.chat.type.name == "PRIVATE":
        return False
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status == ChatMemberStatus.OWNER
    except Exception:
        return False

# --- PM RESTRICTION HANDLER ---
@Client.on_message(filters.command(BLOCKLIST_CMDS) & filters.private)
async def blocklists_pm_handler(client: Client, message: Message):
    await message.reply_text("❌ This command can only be used in groups.")

# --- DYNAMIC INLINE HELP HANDLERS (WITH SEPARATE BANNER PICS) ---

# 1. Main Blocklist Menu (Uses MAIN_BANNER_URL)
@Client.on_callback_query(filters.regex("^help_blocklists$"))
async def help_blocklists_menu(client: Client, callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Blocklist Command Examples", callback_data="blocklist_examples")],
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    
    try:
        if callback.message.photo:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=MAIN_BANNER_URL, caption=BLOCKLIST_HELP_TEXT),
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                text=f"{BLOCKLIST_HELP_TEXT}\n[\u200b]({MAIN_BANNER_URL})",
                reply_markup=keyboard,
                disable_web_page_preview=False
            )
    except RPCError:
        pass

# 2. Blocklist Examples Menu (Uses EXAMPLES_BANNER_URL)
@Client.on_callback_query(filters.regex("^blocklist_examples$"))
async def blocklist_examples_menu(client: Client, callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="help_blocklists")]])
    
    try:
        if callback.message.photo:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=EXAMPLES_BANNER_URL, caption=BLOCKLIST_EXAMPLES_TEXT),
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                text=f"{BLOCKLIST_EXAMPLES_TEXT}\n[\u200b]({EXAMPLES_BANNER_URL})",
                reply_markup=keyboard,
                disable_web_page_preview=False
            )
    except RPCError:
        pass

# --- COMMAND HANDLERS ---

@Client.on_message(filters.command("addblocklist") & filters.group)
async def addblocklist_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply_text("Usage: `/addblocklist <trigger> [reason]`")
    
    raw_input = args[1].strip()
    reason = None
    trigger = ""

    if raw_input.startswith('"'):
        match = re.match(r'^"([^"]+)"\s*(.*)$', raw_input)
        if match:
            trigger = match.group(1).lower()
            reason = match.group(2).strip() or None
        else:
            return await message.reply_text("❌ Invalid format! Please close the quote.")
    else:
        parts = raw_input.split(maxsplit=1)
        trigger = parts[0].lower()
        if len(parts) > 1:
            reason = parts[1].strip()

    cfg = get_chat_config(message.chat.id)
    cfg["triggers"][trigger] = reason
    await message.reply_text(f"✅ Added blocklist trigger: `{trigger}`")

@Client.on_message(filters.command("unblocklist") & filters.group)
async def unblocklist_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply_text("Usage: `/unblocklist <trigger>`")

    trigger = args[1].strip().strip('"').lower()
    cfg = get_chat_config(message.chat.id)

    if trigger in cfg["triggers"]:
        del cfg["triggers"][trigger]
        await message.reply_text(f"✅ Removed `{trigger}` from blocklist.")
    else:
        await message.reply_text(f"❌ `{trigger}` is not in the blocklist.")

@Client.on_message(filters.command("rmblocklist") & filters.group)
async def rmblocklist_cmd(client: Client, message: Message):
    if not await is_user_owner(client, message):
        return await message.reply_text("❌ Only the chat creator/owner can remove all blocklist triggers.")

    cfg = get_chat_config(message.chat.id)
    cfg["triggers"].clear()
    await message.reply_text("✅ All blocklist triggers have been removed!")

@Client.on_message(filters.command("blocklist") & filters.group)
async def blocklist_list_cmd(client: Client, message: Message):
    cfg = get_chat_config(message.chat.id)
    triggers = cfg["triggers"]
    
    if not triggers:
        return await message.reply_text("There are no blocklisted items in this chat.")

    res = f"**Current blocklisted items in {message.chat.title}:**\n"
    for trig, reas in triggers.items():
        if reas:
            res += f"• `{trig}` (Reason: {reas})\n"
        else:
            res += f"• `{trig}`\n"
    await message.reply_text(res)

@Client.on_message(filters.command("blocklistmode") & filters.group)
async def blocklistmode_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.command
    valid_modes = ["nothing", "ban", "mute", "kick", "warn", "tban", "tmute"]

    if len(args) < 2:
        cfg = get_chat_config(message.chat.id)
        return await message.reply_text(f"Current blocklist mode is: `{cfg['mode']}`")

    mode = args[1].lower()
    if mode not in valid_modes:
        return await message.reply_text(f"❌ Invalid mode! Choose from: `{', '.join(valid_modes)}`")

    cfg = get_chat_config(message.chat.id)
    cfg["mode"] = mode
    await message.reply_text(f"✅ Blocklist mode updated to: `{mode}`")

@Client.on_message(filters.command("blocklistdelete") & filters.group)
async def blocklistdelete_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.command
    cfg = get_chat_config(message.chat.id)

    if len(args) < 2:
        status = "on" if cfg["delete"] else "off"
        return await message.reply_text(f"Blocklist deletion is currently set to: `{status}`")

    val = args[1].lower()
    if val in ["yes", "on", "true"]:
        cfg["delete"] = True
        await message.reply_text("✅ Blocklisted messages will now be deleted.")
    elif val in ["no", "off", "false"]:
        cfg["delete"] = False
        await message.reply_text("✅ Blocklisted messages will no longer be deleted.")
    else:
        await message.reply_text("❌ Use `yes/on` or `no/off`.")

@Client.on_message(filters.command("setblocklistreason") & filters.group)
async def setblocklistreason_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply_text("Usage: `/setblocklistreason <reason>`")

    reason = args[1].strip()
    cfg = get_chat_config(message.chat.id)
    cfg["reason"] = reason
    await message.reply_text(f"✅ Default blocklist reason set to: `{reason}`")

@Client.on_message(filters.command("resetblocklistreason") & filters.group)
async def resetblocklistreason_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    cfg = get_chat_config(message.chat.id)
    cfg["reason"] = None
    await message.reply_text("✅ Default blocklist reason reset to nothing.")

# --- REAL AUTO-ENFORCEMENT LISTENER ---
@Client.on_message(filters.group & ~filters.service, group=10)
async def blocklist_enforcer(client: Client, message: Message):
    if not message.text and not message.caption:
        return
    if await is_user_admin(client, message):
        return

    text = (message.text or message.caption).lower()
    cfg = get_chat_config(message.chat.id)
    triggers = cfg["triggers"]

    matched_trigger = None
    matched_reason = None

    for trig, reas in triggers.items():
        if trig in text:
            matched_trigger = trig
            matched_reason = reas or cfg["reason"]
            break

    if matched_trigger:
        if cfg["delete"]:
            try:
                await message.delete()
            except RPCError:
                pass

        user = message.from_user
        mode = cfg["mode"]
        reason_msg = f" Reason: {matched_reason}" if matched_reason else ""

        try:
            if mode == "ban":
                await client.ban_chat_member(message.chat.id, user.id)
                await client.send_message(message.chat.id, f"🚫 Banned {user.mention} for saying blocklisted word!{reason_msg}")
            elif mode == "mute":
                await client.restrict_chat_member(message.chat.id, user.id, permissions=ChatPermissions(can_send_messages=False))
                await client.send_message(message.chat.id, f"🔇 Muted {user.mention} for saying blocklisted word!{reason_msg}")
            elif mode == "kick":
                await client.ban_chat_member(message.chat.id, user.id)
                await client.unban_chat_member(message.chat.id, user.id)
                await client.send_message(message.chat.id, f"👢 Kicked {user.mention} for saying blocklisted word!{reason_msg}")
            elif mode == "warn":
                await client.send_message(message.chat.id, f"⚠️ Warned {user.mention} for saying blocklisted word!{reason_msg}")
        except RPCError:
            pass
