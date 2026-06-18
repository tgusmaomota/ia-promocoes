import requests

def chamar_ia(prompt):
    try:
        resposta = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0}
            },
            timeout=60
        )
        resposta.raise_for_status()
        return resposta.json()["response"].strip()
    except (requests.RequestException, KeyError, ValueError) as erro:
        print(f"IA local indisponivel, usando modelo simples: {erro}")
        return ""


def gerar_post(produto):
    titulo = produto["titulo"]
    preco = float(produto["preco"])
    link = produto["link"]

    prompt = f"""
Gere 3 versões de post para promoção.

DADOS:
Produto: {titulo}
Preço: R$ {preco:.2f}
Link: {link}

REGRAS:
- Não invente desconto.
- Não invente preço anterior.
- Não invente estoque.
- Não use "imperdível".
- Não use "compre agora".

FORMATO OBRIGATÓRIO:

WHATSAPP:
🔥 Produto
💰 Preço
🔗 Link

PROMOBIT:
Produto por Preço
Link

INSTAGRAM:
🔥 Produto
💰 Preço
🔗 Link
"""

    resposta = chamar_ia(prompt)

    if resposta:
        return resposta

    return f"""WHATSAPP:
Produto: {titulo}
Preco: R$ {preco:.2f}
Link: {link}

PROMOBIT:
{titulo} por R$ {preco:.2f}
{link}

INSTAGRAM:
Produto: {titulo}
Preco: R$ {preco:.2f}
Link: {link}"""
