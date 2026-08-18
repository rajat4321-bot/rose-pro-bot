from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus

# --- /id COMMAND HANDLER ---
@Client.on_message(filters.command("id"))
async def get_id(client: Client, message: Message):
    # If replied to another message, get target user's ID
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if target_user:
            return await message.reply_text(
                f"**User ID:** `{target_user.id}`\n"
                f"**Chat ID:** `{message.chat.id}`"
            )
    
    # Standard output based on chat type
    if message.chat.type.name == "PRIVATE":
        await message.reply_text(f"**Your User ID:** `{message.from_user.id}`")
    else:
        await message.reply_text(
            f"**Chat ID:** `{message.chat.id}`\n"
            f"**Your User ID:** `{message.from_user.id}`"
        )

# --- /info COMMAND HANDLER ---
@Client.on_message(filters.command("info"))
async def get_user_info(client: Client, message: Message):
    # Determine target user (Replied user, Tagged argument, or Self)
    target_user = None
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        user_param = message.command[1]
        try:
            target_user = await client.get_users(user_param)
        except Exception:
            return await message.reply_text("❌ User not found or invalid ID/username provided.")
    else:
        target_user = message.from_user

    if not target_user:
        return await message.reply_text("❌ Could not fetch user information.")

    # Fetch User Details
    first_name = target_user.first_name or "N/A"
    last_name = target_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    username = f"@{target_user.username}" if target_user.username else "None"
    user_id = target_user.id
    mention = target_user.mention

    # Default Status
    status = "User"
    
    # Check Admin/Owner Status if executed inside a Group
    if message.chat.type.name != "PRIVATE":
        try:
            member = await client.get_chat_member(message.chat.id, user_id)
            if member.status == ChatMemberStatus.OWNER:
                status = "Chat Creator"
            elif member.status == ChatMemberStatus.ADMINISTRATOR:
                status = "Administrator"
            elif member.status == ChatMemberStatus.RESTRICTED:
                status = "Restricted"
            elif member.status == ChatMemberStatus.BANNED:
                status = "Banned"
        except Exception:
            pass

    info_text = (
        f"**User Information:**\n\n"
        f"• **ID:** `{user_id}`\n"
        f"• **First Name:** {first_name}\n"
        f"• **Last Name:** {last_name if last_name else 'N/A'}\n"
        f"• **Username:** {username}\n"
        f"• **Userlink:** {mention}\n"
        f"• **Status:** {status}"
    )

    await message.reply_text(info_text)
