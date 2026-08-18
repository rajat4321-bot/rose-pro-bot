from motor.motor_asyncio import AsyncIOMotorClient
import config

client = AsyncIOMotorClient(config.MONGO_DB_URI)
db = client["AtherXManagement"]

users_db = db["users"]
feds_db = db["federations"]
filters_db = db["filters"]
notes_db = db["notes"]
warns_db = db["warnings"]

async def register_user(user_id: int, first_name: str, username: str, lang: str):
    """User profile aur default states initialize/update karta hai"""
    user_data = {
        "_id": user_id,
        "first_name": first_name,
        "username": username or "",
        "lang": lang or "en-GB",
        "started_bot": True,
    }
    await users_db.update_one(
        {"_id": user_id},
        {"$set": user_data},
        upsert=True
    )

async def get_user_full_privacy_data(user_id: int):
    """Real time MongoDB collections se LIVE data pull karta hai"""
    user_info = await users_db.find_one({"_id": user_id})
    if not user_info:
        return None

    # 1. Real Federation Check
    fed_admin = await feds_db.find_one({"owner_id": user_id})
    fed_bans = await feds_db.find({"banned_users": user_id}).to_list(length=100)
    
    # 2. Saved Filters & Notes
    user_filters = await filters_db.find({"user_id": user_id}).to_list(length=100)
    user_notes = await notes_db.find({"user_id": user_id}).to_list(length=100)
    
    # 3. Active Warnings Across Groups
    user_warns = await warns_db.find({"user_id": user_id}).to_list(length=100)

    # Building Dynamic JSON payload
    return {
        "approval": user_info.get("approvals", None),
        "captchas": user_info.get("captcha_passed", None),
        "connection": user_info.get("connected_chats", []),
        "federations": {
            "fed_admin_in": fed_admin["fed_id"] if fed_admin else None,
            "fed_banned_id": [f["fed_id"] for f in fed_bans] if fed_bans else None
        },
        "settings": {
            "filters": {
                "filters": [f["filter_name"] for f in user_filters] if user_filters else None
            },
            "notes": {
                "notes": [n["note_name"] for n in user_notes] if user_notes else None
            },
            "translations": {
                "lang": user_info.get("lang", "en-GB")
            }
        },
        "user": {
            "First": user_info.get("first_name", ""),
            "Last": "",
            "Username": user_info.get("username", ""),
            "UserID": user_id,
            "StartedBot": user_info.get("started_bot", True),
            "InChats": user_info.get("chats", [])
        },
        "warnings": [w["chat_id"] for w in user_warns] if user_warns else None
    }

async def delete_user_data(user_id: int):
    """Sare MongoDB collections se user record permanent wipe karta hai"""
    await users_db.delete_one({"_id": user_id})
    await filters_db.delete_many({"user_id": user_id})
    await notes_db.delete_many({"user_id": user_id})
    await warns_db.delete_many({"user_id": user_id})
    return True
