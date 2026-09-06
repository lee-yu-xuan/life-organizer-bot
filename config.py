import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1004400076187"))

TOPICS = {
    "food": int(os.getenv("TOPIC_FOOD", "2")),
    "dates": int(os.getenv("TOPIC_DATES", "3")),
    "wedding": int(os.getenv("TOPIC_WEDDING", "4")),
    "renovation": int(os.getenv("TOPIC_RENOVATION", "5")),
}

DATABASE_PATH = os.getenv("DATABASE_PATH", "food_places.db")
