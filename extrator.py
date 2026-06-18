import re
import requests
from urllib.parse import urlparse, parse_qs

def extrair_id_item(link):
    url = urlparse(link)

    texto_parametros = url.query + "&" + url.fragment
    parametros = parse_qs(texto_parametros)

    if "item_id" in parametros:
        return parametros["item_id"][0]

    if "wid" in parametros:
        return parametros["wid"][0]

    resultado = re.search(r"MLB\d+", link)

    if resultado:
        return resultado.group(0)

    return None


def extrair_dados_produto(link):
    item_id = extrair_id_item(link)

    if not item_id:
        return {
            "titulo": "Produto sem ID",
            "preco": 0.0,
            "link": link,
            "item_id": "",
            "erro": "item_id_nao_encontrado"
        }

    url_api = f"https://api.mercadolibre.com/items/{item_id}"

    try:
        resposta = requests.get(url_api, timeout=15)
    except requests.RequestException as erro:
        return {
            "titulo": f"Produto {item_id}",
            "preco": 0.0,
            "link": link,
            "item_id": item_id,
            "erro": str(erro)
        }

    if resposta.status_code != 200:
        return {
            "titulo": f"Produto {item_id}",
            "preco": 0.0,
            "link": link,
            "item_id": item_id,
            "erro": resposta.status_code
        }

    dados = resposta.json()

    return {
        "titulo": dados.get("title"),
        "preco": dados.get("price"),
        "link": link,
        "item_id": item_id
    }
