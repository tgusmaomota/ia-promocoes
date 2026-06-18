def numero(valor, padrao=0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


LIMITE_FILA = 70
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
    titulo = str(produto.get("titulo", "")).lower()
    tipo_promocao = str(produto.get("tipo_promocao", ""))

    score = 0
    motivos = []

    if preco > 0:
        score += 25
    else:
        motivos.append("preço inválido")

    if 30 <= preco <= 500:
        score += 20
    elif preco > 0:
        score += 10

    if tipo_promocao in {"oferta_do_dia", "oferta_relampago"}:
        score += 20

    if desconto >= 50:
        score += 20
    elif desconto >= 35:
        score += 17
    elif desconto >= 25:
        score += 14
    elif desconto >= 15:
        score += 8

    if "frete grátis" in titulo or "frete gratis" in titulo:
        score += 5

    if "promoção" in titulo or "promocao" in titulo or "oferta" in titulo:
        score += 5

    if "kit" in titulo or "combo" in titulo or "conjunto" in titulo:
        score += 5

    if "internacional" in titulo:
        score -= 20
        motivos.append("produto internacional")

    score = max(0, min(100, round(score, 2)))
    aprovado = score >= LIMITE_FILA

    if aprovado:
        if score >= LIMITE_PROMOCAO_FORTE:
            motivos.insert(0, "promoção forte")
        else:
            motivos.insert(0, "aprovado para fila pendente")
    else:
        motivos.insert(0, f"score insuficiente: {score:g} < {LIMITE_FILA}")

    return {
        "score": score,
        "desconto": desconto,
        "aprovado": aprovado,
        "promocao_forte": score >= LIMITE_PROMOCAO_FORTE,
        "motivo": "; ".join(motivos),
    }
