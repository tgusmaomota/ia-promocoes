from dotenv import load_dotenv
import requests
import os

load_dotenv()

def buscar_produtos(termo, limite=5):
    token = os.getenv("MELI_ACCESS_TOKEN")

    url = "https://api.mercadolibre.com/sites/MLB/search"

    parametros = {
        "q": termo,
        "limit": limite
    }

    headers = {"Accept": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    resposta = requests.get(
        url,
        params=parametros,
        headers=headers,
        timeout=15
    )

    if resposta.status_code != 200:
        print("Erro:", resposta.status_code)
        print(resposta.text)
        return []

    dados = resposta.json()

    produtos = []

    for item in dados.get("results", []):
        produtos.append({
            "titulo": item.get("title"),
            "preco": item.get("price"),
            "link": item.get("permalink"),
            "categoria": "outros"
        })

    return produtos
