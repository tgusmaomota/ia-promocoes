from dotenv import load_dotenv
import requests
import os

load_dotenv()

token = os.getenv("MELI_ACCESS_TOKEN")

item_id = "MLB5574851656"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}

url = f"https://api.mercadolibre.com/items/{item_id}"

resposta = requests.get(url, headers=headers)

print("Status:", resposta.status_code)
print(resposta.text)