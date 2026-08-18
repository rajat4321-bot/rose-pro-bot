from pyrogram import Client
import config
from help import register_help_handlers

app = Client(
    "RoseProBot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="modules") # Auto-load all separate modules
)

# Help module handlers registration
register_help_handlers(app)

if __name__ == "__main__":
    print("Rose Pro Bot Ready & Starting...")
    app.run()
