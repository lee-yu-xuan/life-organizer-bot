import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8948364460:AAGXEs9tdGVv0WfEsEIBX6YRkf--AF-JCoc")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1004400076187"))

TOPICS = {
    "food": int(os.getenv("TOPIC_FOOD", "2")),
    "dates": int(os.getenv("TOPIC_DATES", "3")),
    "wedding": int(os.getenv("TOPIC_WEDDING", "4")),
    "renovation": int(os.getenv("TOPIC_RENOVATION", "5")),
}

DATABASE_PATH = os.getenv("DATABASE_PATH", "food_places.db")
