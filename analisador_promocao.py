import re
from urllib.parse import urlparse

from gerador_link_mercadolivre import link_afiliado_valido


TITULO_COM_PRECO = re.compile(r"(?i)(?:R\$\s*\d|\d+\s*%\s*OFF)")


def numero(valor, padrao=0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


LIMITE_FILA = 65
LIMITE_REVISAO = 45
LIMITE_PROMOCAO_FORTE = 85


def calcular_desconto(preco_atual, preco_anterior=None, desconto=None):
    desconto_informado = numero(desconto)

    if desconto_informado > 0:
        return max(0, min(100, desconto_informado))

    preco_atual = numero(preco_atual)
    preco_anterior = numero(preco_anterior)

    if preco_atual <= 0 or preco_anterior <= preco_atual:
        return 0

    return round(((preco_anterior - preco_atual) / preco_anterior) * 100, 2)


def analisar_produto(produto):
    preco = numero(produto.get("preco_atual") or produto.get("preco"))
    desconto = calcular_desconto(
        preco,
        produto.get("preco_anterior"),
        produto.get("desconto"),
    )
    titulo_original = str(produto.get("titulo", "")).strip()
    titulo = titulo_original.lower()
    economia = numero(produto.get("economia_valor"))
    menor_preco = numero(produto.get("menor_preco"))
    variacao = numero(produto.get("variacao_preco"))
    verificacoes = int(numero(produto.get("vezes_verificado")))
    categoria = str(produto.get("categoria_nome") or produto.get("categoria") or "").strip()
    status_produto = str(produto.get("status_produto") or produto.get("status") or "").lower()
    imagem = str(produto.get("imagem") or produto.get("imagem_url") or "").strip()
    imagem_url = urlparse(imagem)

    score = 0
    motivos = []

    if preco > 0:
        score += 10
    else:
        motivos.append("preço inválido")

    if link_afiliado_valido(produto.get("link_afiliado")):
        score += 10
    else:
        motivos.append("link afiliado inválido")

    if imagem_url.scheme == "https" and imagem_url.netloc:
        score += 5
    else:
        motivos.append("imagem pública ausente")

    if titulo_original and not TITULO_COM_PRECO.search(titulo_original):
        score += 5
    else:
        motivos.append("título ausente ou com preço embutido")

    if categoria and categoria.lower() not in {"ofertas", "oferta", "sem categoria"}:
        score += 5
    else:
        motivos.append("categoria real ausente")

    if status_produto not in {"indisponivel", "erro", "inactive", "paused", "closed"}:
        score += 5
    else:
        motivos.append("produto indisponível")

    if desconto >= 50:
        score += 25
    elif desconto >= 35:
        score += 20
    elif desconto >= 25:
        score += 15
    elif desconto >= 15:
        score += 8

    if economia > 0:
        score += 5

    if verificacoes:
        if menor_preco > 0 and preco <= menor_preco + 0.01:
            score += 15
        elif variacao < 0:
            score += 10
    else:
        motivos.append("histórico ainda insuficiente")

    # Sinais comerciais são capturados da página pública e não substituem a
    # evidência de preço exigida para aprovação automática.
    if str(produto.get("categoria_caminho") or "").count(">") >= 1:
        score += 5
    if bool(produto.get("selo_mais_vendido")):
        score += 8
    if bool(produto.get("selo_loja_oficial")):
        score += 7
    avaliacao = numero(produto.get("avaliacao"))
    if avaliacao >= 4.5:
        score += 6
    elif avaliacao >= 4:
        score += 3
    vendidos = numero(produto.get("quantidade_vendida"))
    if vendidos >= 100:
        score += 5
    elif vendidos >= 20:
        score += 3
    if bool(produto.get("melhor_preco")):
        score += 5

    if "internacional" in titulo:
        score -= 20
        motivos.append("produto internacional")

    score = max(0, min(100, round(score, 2)))
    evidencia_preco = (
        (desconto >= 25 and economia > 0)
        or (menor_preco > 0 and preco <= menor_preco + 0.01)
        or variacao < 0
    )
    aprovado = score >= LIMITE_FILA and evidencia_preco

    if aprovado:
        if score >= LIMITE_PROMOCAO_FORTE:
            motivos.insert(0, "promoção forte")
        else:
            motivos.insert(0, "aprovado para fila pendente")
    elif score < LIMITE_REVISAO:
        motivos.insert(0, f"score insuficiente: {score:g} < {LIMITE_REVISAO}")
    elif not evidencia_preco:
        motivos.insert(0, "revisão recomendada: falta evidência verificável de preço")
    else:
        motivos.insert(0, f"revisão recomendada: {score:g} < {LIMITE_FILA}")

    return {
        "score": score,
        "desconto": desconto,
        "aprovado": aprovado,
        "revisao_recomendada": score >= LIMITE_REVISAO and not aprovado,
        "evidencia_preco": evidencia_preco,
        "promocao_forte": score >= LIMITE_PROMOCAO_FORTE,
        "motivo": "; ".join(motivos),
    }
