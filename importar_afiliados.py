import pandas as pd
from datetime import datetime
from analisador_promocao import LIMITE_FILA, LIMITE_PROMOCAO_FORTE
from banco import registrar_log
from gerador_texto import gerar_post
from csv_utils import COLUNAS_PRODUTOS_AFILIADOS, ler_csv
from schema_posts import COLUNAS_POSTS, ler_posts, salvar_posts

ARQUIVO_AFILIADOS = "produtos_afiliados.csv"
ARQUIVO_POSTS = "posts_prontos.csv"
TIPOS_PROMOCAO_VALIDOS = {"oferta_do_dia", "oferta_relampago"}
PRECO_CONFIAVEL_SIM = {"sim", "s", "true", "1"}


def preco_eh_confiavel(valor):
    return str(valor).lower().strip() in PRECO_CONFIAVEL_SIM


def avaliar_aprovacao(link, preco, preco_confiavel, desconto, score, tipo_promocao):
    motivos_pendencia = []
    motivos_aprovacao = []
    tipo_promocao = str(tipo_promocao).strip()
    promocao_especial = tipo_promocao in TIPOS_PROMOCAO_VALIDOS

    if not link:
        motivos_pendencia.append("item sem confiança suficiente: link afiliado ausente")

    if preco <= 0:
        motivos_pendencia.append("preço duvidoso: preço ausente ou menor/igual a zero")

    if not preco_eh_confiavel(preco_confiavel):
        motivos_pendencia.append(
            f"preço duvidoso: preco_confiavel={preco_confiavel or 'vazio'}"
        )

    if desconto < 0 or desconto > 100:
        motivos_pendencia.append(f"desconto inconsistente: {desconto:g}% fora de 0% a 100%")

    if not promocao_especial and desconto < 25:
        motivos_pendencia.append(
            f"desconto inconsistente: {desconto:g}% abaixo do mínimo de 25%"
        )

    if not promocao_especial and score < 50:
        motivos_pendencia.append(
            f"item sem confiança suficiente: score {score:g} abaixo de 50"
        )

    if score < LIMITE_FILA:
        motivos_pendencia.append(
            f"score insuficiente: {score:g} abaixo de {LIMITE_FILA}"
        )

    if motivos_pendencia:
        return "rejeitado", "Rejeitado: " + "; ".join(motivos_pendencia)

    if score >= LIMITE_PROMOCAO_FORTE:
        motivos_aprovacao.append(f"promoção forte: score {score:g} >= {LIMITE_PROMOCAO_FORTE}")
    else:
        motivos_aprovacao.append(f"score {score:g} >= {LIMITE_FILA}")

    motivos_aprovacao.append("link afiliado existe")
    motivos_aprovacao.append(f"preço válido R$ {preco:.2f}")
    motivos_aprovacao.append("preço confiável")

    if promocao_especial:
        motivos_aprovacao.append(f"tipo_promocao={tipo_promocao}")
    if desconto:
        motivos_aprovacao.append(f"desconto {desconto:g}%")

    return "aprovado_auto", "Aprovado automaticamente: " + "; ".join(motivos_aprovacao)


def log_importacao(mensagem, nivel="info", dados=""):
    print(mensagem)
    try:
        registrar_log("importar_afiliados", mensagem, nivel=nivel, dados=dados)
    except Exception as erro:
        print("Erro ao registrar log de importação:", erro)


df_afiliados = ler_csv(ARQUIVO_AFILIADOS, COLUNAS_PRODUTOS_AFILIADOS)

if df_afiliados.empty:
    print("Nenhum produto afiliado para importar.")
    exit()

df_posts = ler_posts(ARQUIVO_POSTS)
df_posts["preco"] = pd.to_numeric(df_posts["preco"], errors="coerce").fillna(0)

novos_posts = []

for _, produto in df_afiliados.iterrows():

    link = str(produto.get("link_afiliado", "")).strip()
    item_id = str(produto.get("item_id", "")).strip()

    if pd.isna(link) or link == "":
        log_importacao(f"Rejeitado link afiliado ausente: {produto.get('titulo', '')}")
        continue

    preco_confiavel = str(produto.get("preco_confiavel", "sim")).lower().strip()

    try:
        preco_novo = float(produto.get("preco", 0))
    except:
        preco_novo = 0

    if item_id and item_id in df_posts["item_id"].astype(str).values:

        posts_existentes = df_posts[
            df_posts["item_id"].astype(str) == item_id
        ]

        pendentes_existentes = posts_existentes[
            posts_existentes["status"].astype(str) == "pendente"
        ]

        if not pendentes_existentes.empty:
            log_importacao(f"Rejeitado já pendente na fila: {produto.get('titulo', '')}")
            continue

        post_existente = posts_existentes.iloc[-1]

        try:
            preco_antigo = float(post_existente["preco"])
        except:
            preco_antigo = 0

        if preco_novo >= preco_antigo:
            log_importacao(
                f"Rejeitado já publicado sem queda real de preço: "
                f"{produto.get('titulo', '')} "
                f"(R$ {preco_antigo} -> R$ {preco_novo})"
            )
            continue

        log_importacao(
            f"Preço caiu! Republicando: "
            f"{produto.get('titulo', '')} "
            f"(R$ {preco_antigo} -> R$ {preco_novo})"
        )

    try:
        score = float(produto.get("score", 0))
    except:
        score = 0

    try:
        desconto = float(produto.get("desconto", 0))
    except:
        desconto = 0

    tipo_promocao = str(produto.get("tipo_promocao", "")).strip()
    categoria = produto.get("categoria", "ofertas")

    dados_produto = {
        "titulo": produto.get("titulo", ""),
        "preco": preco_novo,
        "link": link,
        "categoria": categoria,
        "desconto": desconto,
        "tipo_promocao": tipo_promocao
    }

    post = gerar_post(dados_produto)

    status, log_aprovacao = avaliar_aprovacao(
        link,
        preco_novo,
        preco_confiavel,
        desconto,
        score,
        tipo_promocao,
    )

    log_importacao(f"{status.upper()}: {produto.get('titulo', '')} | {log_aprovacao}")

    novos_posts.append({
        "titulo": produto.get("titulo", ""),
        "item_id": item_id,
        "score": score,
        "preco": preco_novo,
        "link": link,
        "categoria": categoria,
        "imagem": produto.get("imagem", ""),
        "post": post,
        "status": status,
        "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "log_aprovacao": log_aprovacao,
        "status_telegram": ""
    })

if novos_posts:
    df_novos = pd.DataFrame(novos_posts, columns=COLUNAS_POSTS)

    df_final = pd.concat(
        [df_posts, df_novos],
        ignore_index=True
    )

    salvar_posts(df_final, ARQUIVO_POSTS)

    aprovados = len(df_novos[df_novos["status"] == "aprovado_auto"])
    pendentes = len(df_novos[df_novos["status"] == "pendente_revisao"])

    print(f"{len(novos_posts)} produtos importados para o painel.")
    print(f"Aprovados automaticamente: {aprovados}")
    print(f"Pendentes para revisão: {pendentes}")
else:
    print("Nenhum produto novo para importar.")
