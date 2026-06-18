from dotenv import load_dotenv
import requests
import os

load_dotenv()

client_id = os.getenv("MELI_CLIENT_ID")
client_secret = os.getenv("MELI_CLIENT_SECRET")

code = "TG-6a2b3ac5c53380000103582e-689110189"
redirect_uri = "https://example.com/"

url = "https://api.mercadolibre.com/oauth/token"

dados = {
    "grant_type": "authorization_code",
    "client_id": client_id,
    "client_secret": client_secret,
    "code": code,
    "redirect_uri": redirect_uri
}

resposta = requests.post(url, data=dados)

print(resposta.status_code)
print(resposta.text)