from dotenv import load_dotenv
import os

load_dotenv()

print("TOKEN:", os.getenv("TELEGRAM_BOT_TOKEN"))
print("CHAT_ID:", os.getenv("TELEGRAM_CHAT_ID"))