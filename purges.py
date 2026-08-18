from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError
import asyncio

# --- BANNER IMAGE URL ---
BANNER_PURGES = "https://files.catbox.moe/lzx2ph.png"

# --- IN-MEMORY DB FOR PURGEFROM COMMAND ---
PURGE_FROM_DB = {} # {chat_id: message_id}

# --- EXACT HELP TEXT FROM SCREENSHOT (NO CODE BLOCKS TO PREVENT COPY TO CLIPBOARD) ---
PURGES_HELP_TEXT = (
    "**Purges**\n\n"
    "Need to delete lots of messages? That's what purges are for!\n\n"
    "**Admin commands:**\n"
    "• /purge: Delete all messages from the replied to message, to the current message.\n"
    "• /purge <X>: Delete the following X messages after the replied to message.\n"
    "• /spurge: Same as purge, but doesn't send the final confirmation message.\n"
    "• /del: Deletes the replied to message.\n"
    "• /purgefrom: Reply to a message to mark the message as where to purge from - this should be used followed by a /purgeto.\n"
    "• /purgeto: Delete all messages between the replied to message, and the message marked by the latest /purgefrom.\n\n"
    "**Examples:**\n"
    "- Delete all messages from the replied message, until now.\n"
    "-> /purge\n\n"
    "- Mark the first message to purge from (as a reply).\n"
    "-> /purgefrom\n\n"
    "- Mark the message to purge to (as a reply). All messages between the previously marked /purgefrom and the newly marked /purgeto will be deleted.\n"
    "-> /purgeto"
)

# --- HELPER FUNCTIONS ---
async def can_delete(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status == ChatMemberStatus.OWNER:
            return True
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            return member.privileges.can_delete_messages
        return False
    except Exception:
        return False

# --- INLINE CALLBACK HANDLER (MATCHES help_purges) ---

@Client.on_callback_query(filters.regex(r"^(help_purges|purges_help|help_purges)$"))
async def purges_help_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{PURGES_HELP_TEXT}\n[\u200b]({BANNER_PURGES})"
    
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

# --- REAL WORKING COMMAND HANDLERS WITH STRICT GROUP SCOPE ENFORCEMENT ---

# 1. DELETE SINGLE REPLIED MESSAGE (/del)
@Client.on_message(filters.command("del"))
async def delete_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await can_delete(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need delete message permissions to use this command.")

    if not message.reply_to_message:
        return await message.reply_text("❌ Reply to a message to delete it!")

    try:
        await message.reply_to_message.delete()
        await message.delete()
    except RPCError as e:
        await message.reply_text(f"❌ Failed to delete message: `{e}`")

# 2. PURGE MESSAGES (/purge & /spurge)
@Client.on_message(filters.command(["purge", "spurge"]))
async def purge_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await can_delete(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need delete message permissions to use this command.")

    if not message.reply_to_message:
        return await message.reply_text("❌ Reply to a message to start purging from!")

    chat_id = message.chat.id
    start_message_id = message.reply_to_message.id
    is_silent = message.command[0].lower() == "spurge"

    # Check for X count limit argument
    limit_x = None
    if len(message.command) > 1 and message.command[1].isdigit():
        limit_x = int(message.command[1])
        end_message_id = start_message_id + limit_x + 1
    else:
        end_message_id = message.id

    message_ids = list(range(start_message_id, end_message_id + 1))
    
    # Process batch deletions (100 messages at a time)
    deleted_count = 0
    for i in range(0, len(message_ids), 100):
        batch = message_ids[i:i + 100]
        try:
            await client.delete_messages(chat_id=chat_id, message_ids=batch)
            deleted_count += len(batch)
        except RPCError:
            pass

    if not is_silent:
        status_msg = await client.send_message(
            chat_id=chat_id,
            text=f"✅ Fast purge complete! Deleted **{deleted_count}** messages."
        )
        await asyncio.sleep(4)
        try:
            await status_msg.delete()
        except RPCError:
            pass

# 3. MARK STARTING MESSAGE FOR PURGE (/purgefrom)
@Client.on_message(filters.command("purgefrom"))
async def purgefrom_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await can_delete(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need delete message permissions to use this command.")

    if not message.reply_to_message:
        return await message.reply_text("❌ Reply to a message to mark where to purge from!")

    PURGE_FROM_DB[message.chat.id] = message.reply_to_message.id
    await message.reply_text("✅ Marked message to purge from. Now use /purgeto as a reply to the end message.")

# 4. EXECUTE PURGE TO MARKED MESSAGE (/purgeto)
@Client.on_message(filters.command("purgeto"))
async def purgeto_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside groups!")

    if not await can_delete(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need delete message permissions to use this command.")

    chat_id = message.chat.id
    start_message_id = PURGE_FROM_DB.get(chat_id)

    if not start_message_id:
        return await message.reply_text("❌ You haven't set a /purgefrom message yet!")

    if message.reply_to_message:
        end_message_id = message.reply_to_message.id
    else:
        end_message_id = message.id

    if start_message_id > end_message_id:
        start_message_id, end_message_id = end_message_id, start_message_id

    message_ids = list(range(start_message_id, end_message_id + 1))
    
    deleted_count = 0
    for i in range(0, len(message_ids), 100):
        batch = message_ids[i:i + 100]
        try:
            await client.delete_messages(chat_id=chat_id, message_ids=batch)
            deleted_count += len(batch)
        except RPCError:
            pass

    # Clear saved mark
    PURGE_FROM_DB.pop(chat_id, None)

    status_msg = await client.send_message(
        chat_id=chat_id,
        text=f"✅ Purge complete! Deleted **{deleted_count}** messages."
    )
    await asyncio.sleep(4)
    try:
        await status_msg.delete()
    except RPCError:
        pass
