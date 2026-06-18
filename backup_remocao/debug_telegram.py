from dotenv import load_dotenv
import requests
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

print("BOT:")
r1 = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe")
print(r1.text)

print("\nUPDATES:")
r2 = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates")
print(r2.text)