from dotenv import load_dotenv
import requests
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

dados = {
    "chat_id": CHAT_ID,
    "text": "🚀 TESTE DA IA DE PROMOÇÕES"
}

r = requests.post(url, data=dados)

print(r.status_code)
print(r.text)