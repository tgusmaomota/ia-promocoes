import random
from datetime import datetime, timedelta

from analisador_promocao import LIMITE_FILA, LIMITE_PROMOCAO_FORTE, analisar_produto
from banco import (
    conectar,
    criar_postagem,
    inicializar_banco,
    registrar_log,
    salvar_promocao,
    ultima_postagem_publicada,
)
from gerador_link_mercadolivre import link_afiliado_valido as ml_link_valido


EMOJIS = ["🔥", "💥", "✅", "🛒", "⚡"]
CHAMADAS = [
    "Oferta encontrada",
    "Preço interessante",
    "Promoção monitorada",
    "Achado do dia",
    "Oferta com link afiliado",
]


def link_afiliado_valido(produto):
    plataforma = str(produto.get("plataforma", "")).lower()
    link = produto.get("link_afiliado", "")

    if plataforma == "mercado_livre":
        return ml_link_valido(link)

    return False


def gerar_texto_post(produto, analise):
    emoji = random.choice(EMOJIS)
    chamada = random.choice(CHAMADAS)
    titulo = produto["titulo"]
    preco = float(produto.get("preco_atual") or produto.get("preco") or 0)
    plataforma = produto.get("plataforma", "")
    link = produto["link_afiliado"]
    desconto = analise.get("desconto", 0)

    linhas = [
        f"{emoji} {chamada}",
        f"{titulo}",
        f"Preço: R$ {preco:.2f}",
    ]

    if desconto:
        linhas.append(f"Desconto informado: {desconto:g}%")

    linhas.extend([
        f"Loja: {plataforma.replace('_', ' ').title()}",
        f"Link: {link}",
        "#promocao",
    ])

    return "\n".join(linhas)


def texto_tem_excesso_hashtags(texto, limite=3):
    return str(texto).count("#") > limite


def ja_existe_postagem_link_ou_texto(link, texto):
    inicializar_banco()
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT id FROM postagens
            WHERE link_afiliado = ? OR texto_post = ?
            LIMIT 1
            """,
            (link, texto),
        ).fetchone()
        return row is not None


def respeita_intervalo_minimo(intervalo_minutos):
    ultima = ultima_postagem_publicada()

    if not ultima or not ultima.get("data_publicacao"):
        return True

    data_publicacao = ultima["data_publicacao"]

    try:
        publicada_em = datetime.strptime(data_publicacao, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        publicada_em = datetime.strptime(data_publicacao, "%Y-%m-%d %H:%M")

    return datetime.now() - publicada_em >= timedelta(minutes=intervalo_minutos)


def pode_publicar_texto(texto):
    texto_lower = str(texto).lower()
    proibidas = ["garantido", "menor preço da internet", "100% garantido", "última chance"]

    if texto_tem_excesso_hashtags(texto):
        return False, "excesso de hashtags"

    for palavra in proibidas:
        if palavra in texto_lower:
            return False, f"promessa falsa ou agressiva: {palavra}"

    return True, ""


def gerar_fila_de_produtos(produtos=None):
    inicializar_banco()

    if produtos is None:
        with conectar() as conn:
            produtos = [dict(row) for row in conn.execute(
                "SELECT * FROM produtos WHERE status IN ('coletado', 'migrado_csv')"
            ).fetchall()]

    aprovados = 0
    rejeitados = 0

    for produto in produtos:
        from curadoria_automatica import avaliar_oferta

        analise_curadoria = avaliar_oferta(produto)
        analise = {
            "score": analise_curadoria["score"],
            "desconto": analise_curadoria["desconto"],
            "motivo": analise_curadoria["motivo"],
            "aprovado": analise_curadoria["decisao"] == "aprovado_auto",
        }
        status_promocao = analise_curadoria["decisao"]
        promocao_id = salvar_promocao(
            produto["id"],
            analise["desconto"],
            analise["score"],
            status_promocao,
            f"curadoria_automatica_v2: {analise['motivo']}",
        )

        texto = gerar_texto_post(produto, analise)

        if status_promocao == "pendente_revisao":
            criar_postagem(
                produto["id"], promocao_id, produto, texto,
                status="pendente_revisao", motivo=analise["motivo"],
            )
            rejeitados += 1
            registrar_log("fila", f"Pendente para revisão score={analise['score']}: {produto['titulo']}", dados=analise["motivo"])
            continue

        if status_promocao == "rejeitado":
            criar_postagem(
                produto["id"], promocao_id, produto, texto,
                status="rejeitado", motivo=analise["motivo"],
            )
            rejeitados += 1
            registrar_log("fila", f"Rejeitado por curadoria automática score={analise['score']}: {produto['titulo']}", dados=analise["motivo"])
            continue

        if not link_afiliado_valido(produto):
            criar_postagem(
                produto["id"], promocao_id, produto, texto,
                status="rejeitado", motivo="link afiliado ausente ou inválido",
            )
            rejeitados += 1
            registrar_log("fila", f"Rejeitado sem link afiliado válido: {produto['titulo']}")
            continue

        ok_texto, motivo_texto = pode_publicar_texto(texto)

        if not ok_texto:
            criar_postagem(
                produto["id"], promocao_id, produto, texto,
                status="rejeitado", motivo=f"anti-spam: {motivo_texto}",
            )
            rejeitados += 1
            registrar_log("fila", f"Rejeitado anti-spam: {produto['titulo']} ({motivo_texto})")
            continue

        if ja_existe_postagem_link_ou_texto(produto["link_afiliado"], texto):
            rejeitados += 1
            registrar_log("fila", f"Rejeitado por post/link repetido: {produto['titulo']}")
            continue

        criar_postagem(
            produto["id"], promocao_id, produto, texto,
            status="aprovado_auto", motivo=analise["motivo"],
        )
        registrar_log(
            "auditoria_aprovacao",
            f"Aprovação automática: produto={produto['id']}",
            dados=f"score={analise['score']} motivo={analise['motivo']}",
        )
        aprovados += 1
        if analise["score"] >= LIMITE_PROMOCAO_FORTE:
            registrar_log("fila", f"Postagem pendente criada como promoção forte: {produto['titulo']}")
        else:
            registrar_log("fila", f"Postagem pendente criada: {produto['titulo']}")

    registrar_log(
        "fila",
        (
            f"Fila atualizada. limite={LIMITE_FILA} "
            f"promocao_forte={LIMITE_PROMOCAO_FORTE} "
            f"aprovados={aprovados} rejeitados={rejeitados}"
        ),
    )
    return {"aprovados": aprovados, "rejeitados": rejeitados}


if __name__ == "__main__":
    gerar_fila_de_produtos()
