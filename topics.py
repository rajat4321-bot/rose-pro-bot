from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import RPCError

# --- BANNER IMAGE URL ---
BANNER_TOPICS = "https://files.catbox.moe/im7s6n.png"

# --- IN-MEMORY DATABASE FOR ACTION TOPIC ---
ACTION_TOPIC_DB = {} # {chat_id: topic_id}

# --- EXACT HELP TEXT FROM SCREENSHOT (NO MONOSPACE / NO COPY TO CLIPBOARD) ---
TOPICS_HELP_TEXT = (
    "**Topics**\n\n"
    "Manage your topic settings through Rose!\n\n"
    "Topics introduce lots of small differences to normal supergroups; "
    "this could affect how you would usually manage your chat.\n"
    "For example, certain forums might want to customise which topic "
    "the bot sends welcome messages in, so they don't end up in the default \"general\" chat.\n\n"
    "You can also use the bot to create, rename, close and delete your topics.\n\n"
    "**Admin commands:**\n"
    "• /actiontopic: Get the action topic for this forum.\n"
    "• /setactiontopic: Set the current topic as the default action topic for this forum.\n"
    "• /newtopic <name>: Create a new topic.\n"
    "• /renametopic <name>: Rename the current topic.\n"
    "• /closetopic: Close the current topic.\n"
    "• /reopentopic: Reopen the current closed topic.\n"
    "• /deletetopic: Delete the current topic, and all the topic messages. Cannot be undone!"
)

# --- HELPER FUNCTIONS ---
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

# --- INLINE CALLBACK HANDLER (MATCHES help_topics) ---

@Client.on_callback_query(filters.regex(r"^(help_topics|topics_help)$"))
async def topics_help_cb(client: Client, callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="help_back")]
    ])
    full_text = f"{TOPICS_HELP_TEXT}\n[\u200b]({BANNER_TOPICS})"
    
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

# --- REAL WORKING COMMAND HANDLERS WITH STRICT FORUM/GC SCOPE ENFORCEMENT ---

# 1. GET ACTION TOPIC (/actiontopic)
@Client.on_message(filters.command("actiontopic"))
async def actiontopic_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside Forum groups!")

    if not message.chat.is_forum:
        return await message.reply_text("❌ This group is not a Forum enabled group!")

    chat_id = message.chat.id
    topic_id = ACTION_TOPIC_DB.get(chat_id)

    if topic_id:
        await message.reply_text(f"The current action topic for this chat is ID: `{topic_id}`")
    else:
        await message.reply_text("No action topic has been set. Defaulting to General topic.")

# 2. SET ACTION TOPIC (/setactiontopic)
@Client.on_message(filters.command("setactiontopic"))
async def setactiontopic_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside Forum groups!")

    if not message.chat.is_forum:
        return await message.reply_text("❌ This group is not a Forum enabled group!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to set action topic.")

    topic_id = message.message_thread_id
    if not topic_id:
        return await message.reply_text("❌ Use this command inside a specific topic channel!")

    ACTION_TOPIC_DB[message.chat.id] = topic_id
    await message.reply_text(f"✅ Successfully set current topic (ID: `{topic_id}`) as default action topic!")

# 3. CREATE NEW TOPIC (/newtopic <name>)
@Client.on_message(filters.command("newtopic"))
async def newtopic_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside Forum groups!")

    if not message.chat.is_forum:
        return await message.reply_text("❌ This group is not a Forum enabled group!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to create topics.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Please provide a name for the new topic! Example: `/newtopic Updates`")

    topic_name = message.text.split(None, 1)[1]
    try:
        created_topic = await client.create_forum_topic(chat_id=message.chat.id, title=topic_name)
        await message.reply_text(f"✅ Topic **{created_topic.title}** created successfully!")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to create topic: `{e}`")

# 4. RENAME TOPIC (/renametopic <name>)
@Client.on_message(filters.command("renametopic"))
async def renametopic_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside Forum groups!")

    if not message.chat.is_forum:
        return await message.reply_text("❌ This group is not a Forum enabled group!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to rename topics.")

    if len(message.command) < 2:
        return await message.reply_text("❌ Please provide a new name!")

    topic_id = message.message_thread_id
    if not topic_id:
        return await message.reply_text("❌ Use this command inside the topic you want to rename!")

    new_title = message.text.split(None, 1)[1]
    try:
        await client.edit_forum_topic(chat_id=message.chat.id, message_thread_id=topic_id, title=new_title)
        await message.reply_text("✅ Topic renamed successfully!")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to rename topic: `{e}`")

# 5. CLOSE TOPIC (/closetopic)
@Client.on_message(filters.command("closetopic"))
async def closetopic_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside Forum groups!")

    if not message.chat.is_forum:
        return await message.reply_text("❌ This group is not a Forum enabled group!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to close topics.")

    topic_id = message.message_thread_id
    if not topic_id:
        return await message.reply_text("❌ Use this command inside the topic you want to close!")

    try:
        await client.close_forum_topic(chat_id=message.chat.id, message_thread_id=topic_id)
        await message.reply_text("🔒 Topic closed successfully.")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to close topic: `{e}`")

# 6. REOPEN TOPIC (/reopentopic)
@Client.on_message(filters.command("reopentopic"))
async def reopentopic_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside Forum groups!")

    if not message.chat.is_forum:
        return await message.reply_text("❌ This group is not a Forum enabled group!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to reopen topics.")

    topic_id = message.message_thread_id
    if not topic_id:
        return await message.reply_text("❌ Use this command inside the topic you want to reopen!")

    try:
        await client.reopen_forum_topic(chat_id=message.chat.id, message_thread_id=topic_id)
        await message.reply_text("🔓 Topic reopened successfully.")
    except RPCError as e:
        await message.reply_text(f"❌ Failed to reopen topic: `{e}`")

# 7. DELETE TOPIC (/deletetopic)
@Client.on_message(filters.command("deletetopic"))
async def deletetopic_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ This command can only be used inside Forum groups!")

    if not message.chat.is_forum:
        return await message.reply_text("❌ This group is not a Forum enabled group!")

    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an Admin to delete topics.")

    topic_id = message.message_thread_id
    if not topic_id:
        return await message.reply_text("❌ Use this command inside the topic you want to delete!")

    try:
        await client.delete_forum_topic(chat_id=message.chat.id, message_thread_id=topic_id)
    except RPCError as e:
        await message.reply_text(f"❌ Failed to delete topic: `{e}`")
