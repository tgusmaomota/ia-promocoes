from dotenv import load_dotenv
import requests
import os

load_dotenv()

token = os.getenv("MELI_ACCESS_TOKEN")

headers = {
    "Authorization": f"Bearer {token}"
}

url = "https://api.mercadolibre.com/users/me"

resposta = requests.get(url, headers=headers)

print("Status:", resposta.status_code)
print(resposta.text)