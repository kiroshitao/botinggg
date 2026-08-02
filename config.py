import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]
ADMIN_GROUP_ID: int = int(os.getenv("ADMIN_GROUP_ID", "0"))
DB_PATH: str = "mentors.db"
