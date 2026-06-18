from dotenv import load_dotenv
import requests
import os

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")

url = f"https://api.telegram.org/bot{token}/getUpdates"

resposta = requests.get(url)

print(resposta.text)