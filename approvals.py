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
from database import db

# Database Collection for Approved Users
approvals_db = db["approvals"]

BANNER_URL = "https://files.catbox.moe/n6o10y.png"

APPROVAL_HELP_TEXT = (
    "**Approval**\n\n"
    "Sometimes, you might trust a user not to send unwanted content. "
    "Maybe not enough to make them admin, but you might be ok with locks, blocklists, and antiflood not applying to them.\n\n"
    "That's what approvals are for - approve of trustworthy users to allow them to send.\n\n"
    "**User commands:**\n"
    "• /approval: Check a user's approval status in this chat.\n\n"
    "**Admin commands:**\n"
    "• /approve: Approve of a user. Locks, blocklists, and antiflood won't apply to them anymore.\n"
    "• /unapprove: Unapprove of a user. They will now be subject to locks, blocklists, and antiflood again.\n"
    "• /approved: List all approved users.\n"
    "• /unapproveall: Unapprove ALL users in a chat. This cannot be undone."
)

# --- Shared Helper Function for Other Modules ---
async def is_approved(chat_id: int, user_id: int) -> bool:
    """Check if a user is approved in a chat (used by antiflood, locks, blocklists)."""
    doc = await approvals_db.find_one({"chat_id": chat_id, "user_id": user_id})
    return bool(doc)

# --- Admin Status Checker ---
async def is_user_admin(client: Client, message: Message) -> bool:
    if message.chat.type.name == "PRIVATE":
        return False
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

# --- User Extractor (Extract User ID & Mention from Reply/Args) ---
async def extract_user(client: Client, message: Message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        if user:
            return user.id, user.first_name, user.mention
    
    if len(message.command) > 1:
        arg = message.command[1]
        if arg.isdigit():
            user_id = int(arg)
            try:
                user = await client.get_users(user_id)
                return user.id, user.first_name, user.mention
            except Exception:
                return user_id, str(user_id), f"[User](tg://user?id={user_id})"
        elif arg.startswith("@"):
            try:
                user = await client.get_users(arg)
                return user.id, user.first_name, user.mention
            except Exception:
                return None, None, None
    return None, None, None

# --- Inline Callback Handler ---
@Client.on_callback_query(filters.regex("^help_approval$"))
async def help_approval_menu(client: Client, callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="help_back")]])
    full_text = f"{APPROVAL_HELP_TEXT}\n[\u200b]({BANNER_URL})"
    
    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    except RPCError:
        pass

# --- PM Restrictions ---
@Client.on_message(filters.command(["approval", "approve", "unapprove", "approved", "unapproveall"]) & filters.private)
async def approval_pm_handler(client: Client, message: Message):
    await message.reply_text("❌ This command can only be used in groups.")

# --- USER COMMAND: /approval ---
@Client.on_message(filters.command("approval") & filters.group)
async def check_approval_cmd(client: Client, message: Message):
    user_id, first_name, mention = await extract_user(client, message)
    
    if not user_id:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        mention = message.from_user.mention

    approved = await is_approved(message.chat.id, user_id)
    if approved:
        await message.reply_text(f"✅ {mention} is approved in **{message.chat.title}**.")
    else:
        await message.reply_text(f"❌ {mention} is not approved in **{message.chat.title}**.")

# --- ADMIN COMMAND: /approve ---
@Client.on_message(filters.command("approve") & filters.group)
async def approve_user_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    user_id, first_name, mention = await extract_user(client, message)
    if not user_id:
        return await message.reply_text("You need to specify a user to approve - by reply or username/ID.")

    # Check if target user is admin/owner
    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await message.reply_text(f"❌ {mention} is an admin! They are automatically approved.")
    except Exception:
        pass

    already = await is_approved(message.chat.id, user_id)
    if already:
        return await message.reply_text(f"❌ {mention} is already approved.")

    await approvals_db.update_one(
        {"chat_id": message.chat.id, "user_id": user_id},
        {"$set": {"name": first_name}},
        upsert=True
    )
    await message.reply_text(f"✅ Approved {mention}! Locks, blocklists, and antiflood will no longer apply to them.")

# --- ADMIN COMMAND: /unapprove ---
@Client.on_message(filters.command("unapprove") & filters.group)
async def unapprove_user_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    user_id, first_name, mention = await extract_user(client, message)
    if not user_id:
        return await message.reply_text("You need to specify a user to unapprove - by reply or username/ID.")

    already = await is_approved(message.chat.id, user_id)
    if not already:
        return await message.reply_text(f"❌ {mention} is not approved!")

    await approvals_db.delete_one({"chat_id": message.chat.id, "user_id": user_id})
    await message.reply_text(f"❌ {mention} is no longer approved. Locks, blocklists, and antiflood will apply to them again.")

# --- ADMIN COMMAND: /approved ---
@Client.on_message(filters.command("approved") & filters.group)
async def list_approved_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    cursor = approvals_db.find({"chat_id": message.chat.id})
    approved_users = await cursor.to_list(length=200)

    if not approved_users:
        return await message.reply_text(f"No users are approved in **{message.chat.title}**.")

    msg_text = f"**Approved users in {message.chat.title}:**\n"
    for user_doc in approved_users:
        u_id = user_doc["user_id"]
        u_name = user_doc.get("name", "User")
        msg_text += f"• [{u_name}](tg://user?id={u_id}) (`{u_id}`)\n"

    await message.reply_text(msg_text)

# --- ADMIN/OWNER COMMAND: /unapproveall ---
@Client.on_message(filters.command("unapproveall") & filters.group)
async def unapprove_all_cmd(client: Client, message: Message):
    if not await is_user_admin(client, message):
        return await message.reply_text("❌ You must be an administrator to use this command.")

    count = await approvals_db.count_documents({"chat_id": message.chat.id})
    if count == 0:
        return await message.reply_text("❌ No approved users to remove.")

    result = await approvals_db.delete_many({"chat_id": message.chat.id})
    await message.reply_text(f"✅ Unapproved `{result.deleted_count}` users in **{message.chat.title}**.")
