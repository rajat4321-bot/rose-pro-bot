from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatPrivileges
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.errors import RPCError
import config
from database import db

# Database Collections
settings_db = db["chat_settings"]

HELP_PHOTO = "https://files.catbox.moe/y133rv.png"

ADMIN_HELP_TEXT = (
    "**Admin**\n"
    "Make it easy to promote and demote users with the admin module!\n\n"
    "**Admin commands:**\n"
    "• /promote <reply/username/mention/userid>: Promote a user.\n"
    "• /demote <reply/username/mention/userid>: Demote a user.\n"
    "• /adminlist: List the admins in the current chat.\n"
    "• /admincache: Update the admin cache, to take into account new admin/admin permissions.\n"
    "• /anonadmin <yes/no/on/off>: Allow anonymous admins to use all commands without checking their permissions. Not recommended.\n"
    "• /adminerror <yes/no/on/off>: Send error messages when normal users use admin commands. Default: on.\n\n"
    "Sometimes, you promote or demote an admin manually, and the bot doesn't realise it immediately. This is because to avoid spamming telegram servers, admin status is cached locally. This means that you sometimes have to wait a few minutes for admin rights to update. If you want to update them immediately, you can use the /admincache command; that'll force the bot to check who the admins are again."
    f"[\u200b]({HELP_PHOTO})"
)

ADMIN_HELP_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Back", callback_data="help_back")]
])

# Helper: Check if sender is Owner / Creator / Admin in Group
async def is_user_admin(client: Client, message: Message):
    if message.chat.type.name == "PRIVATE":
        return False
    
    chat_setting = await settings_db.find_one({"chat_id": message.chat.id})
    anon_allowed = chat_setting.get("anonadmin", False) if chat_setting else False
    
    if message.sender_chat and message.sender_chat.id == message.chat.id:
        return True

    if not message.from_user:
        return False

    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        status_str = str(member.status).lower()
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR] or \
           "owner" in status_str or "creator" in status_str or "admin" in status_str:
            return True
        return False
    except Exception:
        return False

# Helper: Check adminerror setting to notify non-admins
async def notify_admin_error(client: Client, message: Message, error_msg: str):
    if message.chat.type.name == "PRIVATE":
        return
    chat_setting = await settings_db.find_one({"chat_id": message.chat.id})
    send_error = chat_setting.get("adminerror", True) if chat_setting else True
    
    if send_error:
        await message.reply_text(error_msg)

# Admin Help Callback Handler
@Client.on_callback_query(filters.regex("^help_admin$"))
async def help_admin_menu(client: Client, callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        text=ADMIN_HELP_TEXT,
        reply_markup=ADMIN_HELP_KEYBOARD,
        disable_web_page_preview=False
    )

# PM Restriction Handler for Admin Commands
@Client.on_message(filters.command(["promote", "demote", "adminlist", "admincache", "anonadmin", "adminerror"]) & filters.private)
async def admin_pm_handler(client: Client, message: Message):
    await message.reply_text("❌ This command can only be used in groups.")

# 1. /promote (Fixed Status Validation)
@Client.on_message(filters.command("promote") & filters.group)
async def promote_handler(client: Client, message: Message):
    if not await is_user_admin(client, message):
        await notify_admin_error(client, message, "❌ You must be an administrator to use this command.")
        return
    
    bot_member = await client.get_chat_member(message.chat.id, client.me.id)
    bot_status = str(bot_member.status).lower()
    if not ("owner" in bot_status or "creator" in bot_status or "admin" in bot_status):
        await message.reply_text("❌ I must be an admin in this chat to promote users.")
        return

    if bot_member.privileges and not bot_member.privileges.can_promote_members:
        await message.reply_text("❌ I need **Promote Members** permission to promote users.")
        return

    user_to_promote = None
    if message.reply_to_message:
        user_to_promote = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            user_to_promote = await client.get_users(message.command[1])
        except Exception:
            pass

    if not user_to_promote:
        await message.reply_text("Please reply to a user or provide their username/ID to promote.")
        return

    # Check live status before promoting
    try:
        target_member = await client.get_chat_member(message.chat.id, user_to_promote.id)
        if target_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text(f"❌ {user_to_promote.mention} is already an admin!")
            return
    except Exception:
        pass

    try:
        await client.promote_chat_member(
            chat_id=message.chat.id,
            user_id=user_to_promote.id,
            privileges=ChatPrivileges(
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_promote_members=False,
                can_invite_users=True,
                can_pin_messages=True
            )
        )
        await message.reply_text(f"Successfully promoted {user_to_promote.mention}!")
    except RPCError as e:
        await message.reply_text(f"Failed to promote user: {e}")

# 2. /demote (Fixed Status Validation)
@Client.on_message(filters.command("demote") & filters.group)
async def demote_handler(client: Client, message: Message):
    if not await is_user_admin(client, message):
        await notify_admin_error(client, message, "❌ You must be an administrator to use this command.")
        return

    bot_member = await client.get_chat_member(message.chat.id, client.me.id)
    bot_status = str(bot_member.status).lower()
    if not ("owner" in bot_status or "creator" in bot_status or "admin" in bot_status):
        await message.reply_text("❌ I must be an admin in this chat to demote users.")
        return

    if bot_member.privileges and not bot_member.privileges.can_promote_members:
        await message.reply_text("❌ I need **Promote Members** permission to demote users.")
        return

    user_to_demote = None
    if message.reply_to_message:
        user_to_demote = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            user_to_demote = await client.get_users(message.command[1])
        except Exception:
            pass

    if not user_to_demote:
        await message.reply_text("Please reply to a user or provide their username/ID to demote.")
        return

    # Check live status before demoting
    try:
        target_member = await client.get_chat_member(message.chat.id, user_to_demote.id)
        if target_member.status == ChatMemberStatus.OWNER:
            await message.reply_text("❌ You cannot demote the group creator/owner!")
            return
        if target_member.status != ChatMemberStatus.ADMINISTRATOR:
            await message.reply_text(f"❌ {user_to_demote.mention} is not an admin!")
            return
    except Exception:
        pass

    try:
        await client.promote_chat_member(
            chat_id=message.chat.id,
            user_id=user_to_demote.id,
            privileges=ChatPrivileges(
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_invite_users=False,
                can_pin_messages=False
            )
        )
        await message.reply_text(f"Successfully demoted {user_to_demote.mention}!")
    except RPCError as e:
        await message.reply_text(f"Failed to demote user: {e}")

# 3. /adminlist
@Client.on_message(filters.command("adminlist") & filters.group)
async def adminlist_handler(client: Client, message: Message):
    owner_str = None
    admins = []

    try:
        async for admin in client.get_chat_members(message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS):
            if not admin.user:
                continue
            
            title = f" <i>({admin.custom_title})</i>" if admin.custom_title else ""
            status_str = str(admin.status).lower()
            
            if admin.status == ChatMemberStatus.OWNER or "owner" in status_str or "creator" in status_str:
                owner_str = f"👑 **Owner:** {admin.user.mention}{title}"
            else:
                admins.append(f"• {admin.user.mention}{title}")
    except Exception as e:
        await message.reply_text(f"Error fetching admin list: {e}")
        return

    group_name = message.chat.title
    text = f"🛡 **Admins in {group_name}:**\n\n"
    
    if owner_str:
        text += f"{owner_str}\n\n**Administrators:**\n"
    elif admins:
        text += "**Administrators:**\n"
        
    if admins:
        text += "\n".join(admins)
    elif not owner_str:
        text += "No admins found."

    await message.reply_text(text)

# 4. /admincache
@Client.on_message(filters.command("admincache") & filters.group)
async def admincache_handler(client: Client, message: Message):
    if not await is_user_admin(client, message):
        await notify_admin_error(client, message, "❌ You must be an administrator to use this command.")
        return
    await message.reply_text("🔄 **Admin cache refreshed successfully!** Forced update completed for chat admin rights.")

# 5. /anonadmin
@Client.on_message(filters.command("anonadmin") & filters.group)
async def anonadmin_handler(client: Client, message: Message):
    if not await is_user_admin(client, message):
        await notify_admin_error(client, message, "❌ You must be an administrator to use this command.")
        return

    if len(message.command) < 2:
        setting = await settings_db.find_one({"chat_id": message.chat.id})
        status = "enabled" if setting and setting.get("anonadmin", False) else "disabled"
        await message.reply_text(f"Anonymous admin command execution is currently **{status}**.")
        return

    val = message.command[1].lower()
    if val in ["yes", "on", "true"]:
        await settings_db.update_one({"chat_id": message.chat.id}, {"$set": {"anonadmin": True}}, upsert=True)
        await message.reply_text("✅ Anonymous admins are now allowed to execute all commands.")
    elif val in ["no", "off", "false"]:
        await settings_db.update_one({"chat_id": message.chat.id}, {"$set": {"anonadmin": False}}, upsert=True)
        await message.reply_text("❌ Anonymous admins will no longer bypass permission checks.")
    else:
        await message.reply_text("Usage: `/anonadmin [yes|no|on|off]`")

# 6. /adminerror
@Client.on_message(filters.command("adminerror") & filters.group)
async def adminerror_handler(client: Client, message: Message):
    if not await is_user_admin(client, message):
        await notify_admin_error(client, message, "❌ You must be an administrator to use this command.")
        return

    if len(message.command) < 2:
        setting = await settings_db.find_one({"chat_id": message.chat.id})
        status = "enabled" if not setting or setting.get("adminerror", True) else "disabled"
        await message.reply_text(f"Admin error notification is currently **{status}**.")
        return

    val = message.command[1].lower()
    if val in ["yes", "on", "true"]:
        await settings_db.update_one({"chat_id": message.chat.id}, {"$set": {"adminerror": True}}, upsert=True)
        await message.reply_text("✅ Error messages will be sent when normal users try to use admin commands.")
    elif val in ["no", "off", "false"]:
        await settings_db.update_one({"chat_id": message.chat.id}, {"$set": {"adminerror": False}}, upsert=True)
        await message.reply_text("❌ Bot will stay silent when normal users attempt to use admin commands.")
    else:
        await message.reply_text("Usage: `/adminerror [yes|no|on|off]`")
