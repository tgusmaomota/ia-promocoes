"""Métricas reutilizáveis sobre histórico de preços do Promogg."""

from statistics import mean

from banco import conectar, inicializar_banco


STATUS_CONFIAVEIS = {"ok", "coletado", "baseline_local", "recuperacao_catalogo_estatico"}
FONTES_ALTA_CONFIANCA = {"api_item", "api", "coleta", "playwright", "recuperacao_catalogo_estatico"}


def classificar_tendencia(precos):
    """Classifica tendência a partir das últimas observações válidas."""
    valores = [float(preco) for preco in precos if preco is not None and float(preco) > 0]
    if len(valores) < 2:
        return "insuficiente"
    recente = valores[0]
    anterior = valores[1]
    delta = round(recente - anterior, 2)
    if delta < 0:
        return "queda"
    if delta > 0:
        return "alta"
    return "estável"


def calcular_confiabilidade(registros):
    """Retorna uma nota simples de confiabilidade de 0 a 100."""
    registros = list(registros or [])
    if not registros:
        return 0
    total = len(registros)
    validos = [r for r in registros if r.get("preco") is not None and float(r.get("preco") or 0) > 0]
    fontes_boas = [
        r for r in registros
        if str(r.get("fonte_preco") or "").strip() in FONTES_ALTA_CONFIANCA
        or str(r.get("status_verificacao") or "").strip() in STATUS_CONFIAVEIS
    ]
    cobertura = min(1.0, len(validos) / 5)
    qualidade = len(fontes_boas) / total
    return round((cobertura * 60) + (qualidade * 40), 1)


def metricas_item(item_id, limite=20):
    """Calcula métricas de histórico sem alterar banco."""
    inicializar_banco()
    item_id = str(item_id or "").strip().upper()
    with conectar() as conn:
        registros = [dict(row) for row in conn.execute(
            """
            SELECT preco, data_verificacao, status_verificacao, fonte_preco
            FROM historico_precos
            WHERE item_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (item_id, int(limite)),
        ).fetchall()]
    precos = [float(r["preco"]) for r in registros if r.get("preco") is not None and float(r["preco"]) > 0]
    return {
        "item_id": item_id,
        "observacoes": len(registros),
        "observacoes_validas": len(precos),
        "menor_preco": min(precos) if precos else None,
        "maior_preco": max(precos) if precos else None,
        "preco_medio": round(mean(precos), 2) if precos else None,
        "ultima_alteracao": registros[0]["data_verificacao"] if registros else "",
        "quantidade_alteracoes": max(0, len({round(preco, 2) for preco in precos}) - 1),
        "origem_preco": registros[0].get("fonte_preco") if registros else "",
        "status_ultima_verificacao": registros[0].get("status_verificacao") if registros else "",
        "confiabilidade": calcular_confiabilidade(registros),
        "tendencia": classificar_tendencia(precos),
    }


def resumo_historico_global():
    """Resumo operacional do histórico de preços, somente leitura."""
    inicializar_banco()
    with conectar() as conn:
        return {
            "registros": conn.execute("SELECT COUNT(*) FROM historico_precos").fetchone()[0],
            "produtos_com_historico": conn.execute(
                "SELECT COUNT(DISTINCT produto_id) FROM historico_precos WHERE preco IS NOT NULL"
            ).fetchone()[0],
            "fontes": [dict(row) for row in conn.execute(
                """
                SELECT COALESCE(NULLIF(fonte_preco, ''), status_verificacao, 'sem_fonte') AS fonte,
                       COUNT(*) AS total
                FROM historico_precos
                GROUP BY fonte
                ORDER BY total DESC
                LIMIT 12
                """
            ).fetchall()],
            "inconclusivos": conn.execute(
                """
                SELECT COUNT(*) FROM historico_precos
                WHERE status_verificacao IN ('erro_api', 'verificacao_inconclusiva')
                """
            ).fetchone()[0],
        }

