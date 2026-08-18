import uuid
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError

# --- DEDICATED BANNER IMAGE URLS ---
BANNER_MAIN = "https://files.catbox.moe/jvojov.png"
BANNER_ADMIN = "https://files.catbox.moe/185dow.png"  # Dedicated Admin Banner URL
BANNER_OWNER = "https://files.catbox.moe/hpia7l.png"  # Dedicated Owner Banner URL
BANNER_USER = "https://files.catbox.moe/readn4.png"    # Dedicated User Banner URL

# --- IN-MEMORY FEDERATION DATABASE ---
FEDERATIONS = {}
CHAT_FED = {}  # chat_id -> fed_id

def get_user_feds(user_id: int):
    return [fid for fid, data in FEDERATIONS.items() if data["owner"] == user_id or user_id in data["admins"]]

def is_fed_owner(fed_id: str, user_id: int) -> bool:
    return fed_id in FEDERATIONS and FEDERATIONS[fed_id]["owner"] == user_id

def is_fed_admin(fed_id: str, user_id: int) -> bool:
    if fed_id not in FEDERATIONS:
        return False
    return FEDERATIONS[fed_id]["owner"] == user_id or user_id in FEDERATIONS[fed_id]["admins"]

# --- HELP TEXT STRINGS ---

MAIN_FED_HELP = (
    "**⚡ Federations**\n\n"
    "Ah, group management. It's all fun and games, until you start getting spammers in, and you need to ban them. "
    "Then you need to start banning more, and more, and it gets painful.\n\n"
    "But then you have multiple groups, and you don't want these spammers in any of your groups - how can you deal? "
    "Do you have to ban them manually in all your groups?\n\n"
    "No more! With federations, you can make a ban in one chat overlap to all your other chats. "
    "You can even appoint federation admins, so that your trustworthiest admins can ban across all the chats that you want to protect."
)

FED_ADMIN_HELP = (
    "**⚡ Fed Admin Commands**\n\n"
    "The following is the list of all fed admin commands. To run these, you have to be a federation admin in the current federation.\n\n"
    "**Commands:**\n"
    "• /fban [user]: Bans a user from the current chat's federation.\n"
    "• /unfban [user]: Unbans a user from the current chat's federation.\n"
    "• /feddemoteme [fed_id]: Demote yourself from a fed.\n"
    "• /myfeds: List all feds you are an admin in."
)

FED_OWNER_HELP = (
    "**⚡ Federation Owner Commands**\n\n"
    "These are the list of available fed owner commands. To run these, you have to own the current federation.\n\n"
    "**Owner Commands:**\n"
    "• /newfed [fed_name]: Creates a new federation with the given name.\n"
    "• /renamefed [fed_name]: Rename your federation.\n"
    "• /delfed [fed_id]: Deletes your federation and data.\n"
    "• /fedtransfer [user]: Transfer your federation to another user.\n"
    "• /fedpromote [user]: Promote a user to fedadmin in your fed.\n"
    "• /feddemote [user]: Demote a federation admin in your fed.\n"
    "• /fednotifs [yes/no/on/off]: Toggle PM notifications of fed actions.\n"
    "• /fedreason [yes/no/on/off]: Toggle mandatory reasons for fedbans.\n"
    "• /subfed [fed_id]: Subscribe your federation to another.\n"
    "• /unsubfed [fed_id]: Unsubscribe your federation from another.\n"
    "• /fedexport: Export list of banned users.\n"
    "• /fedimport: Import list of banned users.\n"
    "• /setfedlog: Sets current chat as the federation log channel.\n"
    "• /unsetfedlog: Unsets the federation log channel."
)

FED_USER_HELP = (
    "**⚡ User Commands**\n\n"
    "These commands do not require you to be admin of a federation. These commands are for general commands, "
    "such as looking up information on a fed, or checking a user's fbans.\n\n"
    "**Commands:**\n"
    "• /fedinfo [fed_id]: Information about a federation.\n"
    "• /fedadmins [fed_id]: List the admins in a federation.\n"
    "• /fedsubs [fed_id]: List all federations your federation is subscribed to.\n"
    "• /joinfed [fed_id]: Join the current chat to a federation (Chat owners only).\n"
    "• /leavefed: Leave the current federation (Chat owners only).\n"
    "• /fedstat: List all the federations that you have been banned in.\n"
    "• /fedstat [user]: List all the federations that a user has been banned in.\n"
    "• /chatfed: Information about the federation the current chat is in.\n"
    "• /quietfed [yes/no/on/off]: Toggle ban notification messages in chat."
)

# --- INLINE CALLBACK HANDLERS ---

@Client.on_callback_query(filters.regex(r"^help_federations$"))
async def help_federations_main(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Fed Admin Commands", callback_data="fed_cmd_admin"),
            InlineKeyboardButton("Federation Owner Commands", callback_data="fed_cmd_owner")
        ],
        [InlineKeyboardButton("User Commands", callback_data="fed_cmd_user")],
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{MAIN_FED_HELP}\n[\u200b]({BANNER_MAIN})"
    try:
        await callback.message.edit_text(text=full_text, reply_markup=keyboard, disable_web_page_preview=False)
    except RPCError:
        pass
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^fed_cmd_admin$"))
async def fed_cmd_admin_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="help_federations")]])
    full_text = f"{FED_ADMIN_HELP}\n[\u200b]({BANNER_ADMIN})"
    try:
        await callback.message.edit_text(text=full_text, reply_markup=keyboard, disable_web_page_preview=False)
    except RPCError:
        pass
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^fed_cmd_owner$"))
async def fed_cmd_owner_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="help_federations")]])
    full_text = f"{FED_OWNER_HELP}\n[\u200b]({BANNER_OWNER})"
    try:
        await callback.message.edit_text(text=full_text, reply_markup=keyboard, disable_web_page_preview=False)
    except RPCError:
        pass
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^fed_cmd_user$"))
async def fed_cmd_user_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="help_federations")]])
    full_text = f"{FED_USER_HELP}\n[\u200b]({BANNER_USER})"
    try:
        await callback.message.edit_text(text=full_text, reply_markup=keyboard, disable_web_page_preview=False)
    except RPCError:
        pass
    await callback.answer()

# --- REAL LOGIC ENFORCEMENT COMMAND HANDLERS ---

# 1. OWNER COMMANDS

@Client.on_message(filters.command("newfed"))
async def newfed_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: /newfed [fed_name]")
    
    name = " ".join(args)
    fed_id = str(uuid.uuid4())[:8]
    user_id = message.from_user.id
    
    FEDERATIONS[fed_id] = {
        "name": name,
        "owner": user_id,
        "admins": set(),
        "banned": {},
        "chats": set(),
        "log_chat": None,
        "quiet": False,
        "reason_req": False,
        "notifs": True
    }
    await message.reply_text(f"✅ Created new federation **{name}**!\n**Fed ID:** `{fed_id}`")

@Client.on_message(filters.command("delfed"))
async def delfed_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: /delfed [fed_id]")
    
    fed_id = args[0]
    user_id = message.from_user.id
    
    if fed_id not in FEDERATIONS:
        return await message.reply_text("❌ Invalid Federation ID.")
    if not is_fed_owner(fed_id, user_id):
        return await message.reply_text("❌ Only the owner of the federation can delete it.")
    
    del FEDERATIONS[fed_id]
    await message.reply_text("✅ Successfully deleted federation.")

@Client.on_message(filters.command("fedpromote"))
async def fedpromote_cmd(client: Client, message: Message):
    args = message.command[1:]
    user_id = message.from_user.id
    my_feds = [fid for fid, d in FEDERATIONS.items() if d["owner"] == user_id]
    
    if not my_feds:
        return await message.reply_text("❌ You do not own any federation.")
    
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif args:
        try:
            target_user = await client.get_users(args[0])
        except Exception:
            return await message.reply_text("❌ User not found.")
    else:
        return await message.reply_text("Usage: /fedpromote [user/reply]")

    fed_id = my_feds[0]
    FEDERATIONS[fed_id]["admins"].add(target_user.id)
    await message.reply_text(f"✅ Promoted {target_user.mention} to Fed Admin in **{FEDERATIONS[fed_id]['name']}**.")

@Client.on_message(filters.command("feddemote"))
async def feddemote_cmd(client: Client, message: Message):
    args = message.command[1:]
    user_id = message.from_user.id
    my_feds = [fid for fid, d in FEDERATIONS.items() if d["owner"] == user_id]
    
    if not my_feds:
        return await message.reply_text("❌ You do not own any federation.")
    
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif args:
        try:
            target_user = await client.get_users(args[0])
        except Exception:
            return await message.reply_text("❌ User not found.")
    else:
        return await message.reply_text("Usage: /feddemote [user/reply]")

    fed_id = my_feds[0]
    if target_user.id in FEDERATIONS[fed_id]["admins"]:
        FEDERATIONS[fed_id]["admins"].remove(target_user.id)
        await message.reply_text(f"✅ Demoted {target_user.mention} from Fed Admin in **{FEDERATIONS[fed_id]['name']}**.")
    else:
        await message.reply_text("ℹ️ User is not an admin in your fed.")

# 2. ADMIN COMMANDS

@Client.on_message(filters.command("fban"))
async def fban_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    fed_id = CHAT_FED.get(chat_id)
    
    if not fed_id or fed_id not in FEDERATIONS:
        return await message.reply_text("❌ This chat is not connected to any federation!")

    user_id = message.from_user.id
    if not is_fed_admin(fed_id, user_id):
        return await message.reply_text("❌ You are not a Fed Admin in this chat's federation.")

    args = message.command[1:]
    target_user = None
    reason = "No reason given."

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if args:
            reason = " ".join(args)
    elif args:
        try:
            target_user = await client.get_users(args[0])
            if len(args) > 1:
                reason = " ".join(args[1:])
        except Exception:
            return await message.reply_text("❌ Invalid user specified.")
    else:
        return await message.reply_text("Usage: /fban [user] [reason]")

    if not target_user:
        return await message.reply_text("❌ Target user not found.")

    FEDERATIONS[fed_id]["banned"][target_user.id] = reason
    await message.reply_text(
        f"✅ **FedBan Enforced!**\n\n"
        f"• **User:** {target_user.mention} (`{target_user.id}`)\n"
        f"• **Fed:** {FEDERATIONS[fed_id]['name']}\n"
        f"• **Reason:** {reason}"
    )

@Client.on_message(filters.command("unfban"))
async def unfban_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    fed_id = CHAT_FED.get(chat_id)

    if not fed_id or fed_id not in FEDERATIONS:
        return await message.reply_text("❌ This chat is not connected to any federation!")

    user_id = message.from_user.id
    if not is_fed_admin(fed_id, user_id):
        return await message.reply_text("❌ You are not a Fed Admin in this chat's federation.")

    args = message.command[1:]
    target_user = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif args:
        try:
            target_user = await client.get_users(args[0])
        except Exception:
            return await message.reply_text("❌ Invalid user specified.")
    else:
        return await message.reply_text("Usage: /unfban [user]")

    if target_user.id in FEDERATIONS[fed_id]["banned"]:
        del FEDERATIONS[fed_id]["banned"][target_user.id]
        await message.reply_text(f"✅ Un-fedbanned {target_user.mention} from **{FEDERATIONS[fed_id]['name']}**.")
    else:
        await message.reply_text("ℹ️ User is not fedbanned in this federation.")

@Client.on_message(filters.command("myfeds"))
async def myfeds_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    feds = get_user_feds(user_id)
    
    if not feds:
        return await message.reply_text("ℹ️ You are not an admin or owner of any federation.")
    
    text = "**Federations you participate in:**\n\n"
    for fid in feds:
        role = "Owner" if FEDERATIONS[fid]["owner"] == user_id else "Admin"
        text += f"• **{FEDERATIONS[fid]['name']}** (`{fid}`) - `{role}`\n"
    
    await message.reply_text(text)

# 3. USER / GROUP COMMANDS

@Client.on_message(filters.command("joinfed") & filters.group)
async def joinfed_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    
    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status != ChatMemberStatus.OWNER:
            return await message.reply_text("❌ Only the group creator can connect this chat to a federation.")
    except Exception:
        return

    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: /joinfed [fed_id]")

    fed_id = args[0]
    if fed_id not in FEDERATIONS:
        return await message.reply_text("❌ Federation does not exist.")

    CHAT_FED[message.chat.id] = fed_id
    FEDERATIONS[fed_id]["chats"].add(message.chat.id)
    await message.reply_text(f"✅ Successfully joined federation **{FEDERATIONS[fed_id]['name']}**!")

@Client.on_message(filters.command("leavefed") & filters.group)
async def leavefed_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    
    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status != ChatMemberStatus.OWNER:
            return await message.reply_text("❌ Only the group creator can remove this chat from a federation.")
    except Exception:
        return

    chat_id = message.chat.id
    if chat_id not in CHAT_FED:
        return await message.reply_text("ℹ️ This chat is not in any federation.")

    fed_id = CHAT_FED[chat_id]
    FEDERATIONS[fed_id]["chats"].discard(chat_id)
    del CHAT_FED[chat_id]
    await message.reply_text("✅ Chat has left the federation.")

@Client.on_message(filters.command("chatfed") & filters.group)
async def chatfed_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    fed_id = CHAT_FED.get(chat_id)

    if not fed_id or fed_id not in FEDERATIONS:
        return await message.reply_text("ℹ️ This chat is not currently connected to any federation.")

    fed = FEDERATIONS[fed_id]
    await message.reply_text(
        f"**Chat Federation Info:**\n\n"
        f"• **Fed Name:** {fed['name']}\n"
        f"• **Fed ID:** `{fed_id}`"
    )

@Client.on_message(filters.command("fedinfo"))
async def fedinfo_cmd(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        chat_id = message.chat.id
        fed_id = CHAT_FED.get(chat_id)
        if not fed_id:
            return await message.reply_text("Usage: /fedinfo [fed_id]")
    else:
        fed_id = args[0]

    if fed_id not in FEDERATIONS:
        return await message.reply_text("❌ Federation not found.")

    fed = FEDERATIONS[fed_id]
    text = (
        f"**Federation Information:**\n\n"
        f"• **Name:** {fed['name']}\n"
        f"• **ID:** `{fed_id}`\n"
        f"• **Owner ID:** `{fed['owner']}`\n"
        f"• **Admins:** {len(fed['admins'])}\n"
        f"• **Banned Users:** {len(fed['banned'])}\n"
        f"• **Connected Chats:** {len(fed['chats'])}"
    )
    await message.reply_text(text)
