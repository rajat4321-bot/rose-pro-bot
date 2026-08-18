import re
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError

BANNER_URL = "https://files.catbox.moe/ku2m55.png"

# In-memory database for active connections and history
# Format: USER_CONNECTIONS[user_id] = {"current": chat_id, "history": chat_id}
USER_CONNECTIONS = {}

CONNECTIONS_HELP_TEXT = (
    "**Connections**\n\n"
    "Sometimes, you just want to add some notes and filters to a group chat, but you don't want everyone to see; This is where connections come in...\n\n"
    "This allows you to connect to a chat's database, and add things to it without the chat knowing about it! For obvious reasons, you need to be an admin to add things, but any member can view your data. (banned/kicked users can't)\n\n"
    "**Admin commands:**\n"
    "• /connect [chatid/username]: Connect to the specified chat, allowing you to view/edit contents.\n"
    "• /disconnect: Disconnect from the current chat.\n"
    "• /reconnect: Reconnect to the previously connected chat.\n"
    "• /connection: See information about the currently connected chat.\n\n"
    "**Tips:**\n"
    "• Connect to a chat by ID (obtained from /id):\n"
    "  /connect -100123456789\n\n"
    "• Connect to a chat by username:\n"
    "  /connect @groupusername\n\n"
    "• When in a group, the connect command will create a connection to the current chat:\n"
    "  (in a group) /connect\n\n"
    "• When in private, the connect command will list recently connected chats:\n"
    "  (in private) /connect\n\n"
    "You can retrieve the chat ID by using the /id command in your chat. Don't be surprised if the ID is negative; all supergroups have negative IDs."
)

CONNECT_CMDS = ["connect", "disconnect", "reconnect", "connection"]

def get_user_data(user_id: int):
    if user_id not in USER_CONNECTIONS:
        USER_CONNECTIONS[user_id] = {"current": None, "history": None}
    return USER_CONNECTIONS[user_id]

async def is_user_admin_in_chat(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

# --- INLINE HELP CALLBACK HANDLER ---
@Client.on_callback_query(filters.regex(r"^help_connections$"))
async def help_connections_menu(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{CONNECTIONS_HELP_TEXT}\n[\u200b]({BANNER_URL})"
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass
    await callback.answer()

# --- COMMAND HANDLERS ---

@Client.on_message(filters.command("connect"))
async def connect_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    udata = get_user_data(user_id)

    # 1. GROUP USE: Directly connect to the group
    if message.chat.type.name != "PRIVATE":
        if not await is_user_admin_in_chat(client, message.chat.id, user_id):
            return await message.reply_text("❌ You must be an administrator in this chat to connect to it.")
        
        udata["history"] = udata["current"]
        udata["current"] = message.chat.id
        return await message.reply_text(f"✅ Successfully connected to **{message.chat.title}** (`{message.chat.id}`).")

    # 2. PRIVATE USE
    args = message.command[1:]
    
    # If no args given in PM: List recent connection status
    if not args:
        if udata["current"]:
            try:
                chat = await client.get_chat(udata["current"])
                return await message.reply_text(f"ℹ️ Currently connected to **{chat.title}** (`{chat.id}`).")
            except Exception:
                return await message.reply_text(f"ℹ️ Currently connected to chat ID `{udata['current']}`.")
        else:
            return await message.reply_text("❌ You are not connected to any chat right now!\n\n**Usage:** /connect [chatid/username]")

    target = args[0]
    
    # Try fetching the target group
    try:
        if target.startswith("-100") or target.lstrip("-").isdigit():
            target_chat_id = int(target)
        else:
            target_chat_id = target

        chat = await client.get_chat(target_chat_id)
    except Exception:
        return await message.reply_text("❌ Could not find the specified chat. Make sure I am an admin there and the ID/username is correct.")

    if chat.type.name == "PRIVATE":
        return await message.reply_text("❌ Connections can only be established with Groups or Channels.")

    # Check admin status in that chat
    if not await is_user_admin_in_chat(client, chat.id, user_id):
        return await message.reply_text(f"❌ You are not an administrator in **{chat.title}**.")

    udata["history"] = udata["current"]
    udata["current"] = chat.id
    await message.reply_text(f"✅ Successfully connected to **{chat.title}** (`{chat.id}`).")

@Client.on_message(filters.command("disconnect"))
async def disconnect_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    udata = get_user_data(user_id)

    if not udata["current"]:
        return await message.reply_text("❌ You are not connected to any chat!")

    curr_id = udata["current"]
    udata["history"] = curr_id
    udata["current"] = None

    try:
        chat = await client.get_chat(curr_id)
        await message.reply_text(f"✅ Disconnected from **{chat.title}**.")
    except Exception:
        await message.reply_text("✅ Disconnected from the current chat.")

@Client.on_message(filters.command("reconnect"))
async def reconnect_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    udata = get_user_data(user_id)

    if not udata["history"]:
        return await message.reply_text("❌ There is no previous connection history to reconnect to.")

    target_id = udata["history"]

    if not await is_user_admin_in_chat(client, target_id, user_id):
        return await message.reply_text("❌ You are no longer an administrator in the previously connected chat.")

    udata["history"] = udata["current"]
    udata["current"] = target_id

    try:
        chat = await client.get_chat(target_id)
        await message.reply_text(f"✅ Reconnected to **{chat.title}** (`{chat.id}`).")
    except Exception:
        await message.reply_text(f"✅ Reconnected to chat ID `{target_id}`.")

@Client.on_message(filters.command("connection"))
async def connection_info_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    udata = get_user_data(user_id)

    if not udata["current"]:
        return await message.reply_text("ℹ️ Active Connection: **None**\nYou are not connected to any chat.")

    try:
        chat = await client.get_chat(udata["current"])
        text = (
            f"**Currently Connected Chat:**\n\n"
            f"• **Title:** {chat.title}\n"
            f"• **Chat ID:** `{chat.id}`\n"
            f"• **Username:** @{chat.username if chat.username else 'N/A'}"
        )
    except Exception:
        text = f"**Currently Connected Chat ID:** `{udata['current']}`"

    await message.reply_text(text)
