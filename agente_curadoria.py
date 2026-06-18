import pandas as pd
import os
from datetime import datetime

from analisador_promocao import LIMITE_FILA, analisar_produto
from banco import registrar_log
from csv_utils import COLUNAS_PRODUTOS_BUSCA, ler_csv, salvar_csv
from schema_posts import ler_posts

ARQUIVO_ENTRADA = "produtos_busca.csv"
ARQUIVO_SAIDA = "produtos_filtrados.csv"
ARQUIVO_HISTORICO = "historico_precos.csv"
ARQUIVO_HISTORICO_PRODUTOS = "historico_produtos.csv"
TIPOS_PROMOCAO_VALIDOS = {"oferta_do_dia", "oferta_relampago"}
COLUNAS_HISTORICO = ["item_id", "titulo", "menor_preco", "ultima_data"]
COLUNAS_HISTORICO_PRODUTOS = ["item_id", "preco", "desconto", "data", "score"]


def calcular_score(produto):
    return analisar_produto(produto)["score"]


def log_curadoria(mensagem, nivel="info", dados=""):
    print(mensagem)
    try:
        registrar_log("curadoria", mensagem, nivel=nivel, dados=dados)
    except Exception as erro:
        print("Erro ao registrar log de curadoria:", erro)


df = ler_csv(ARQUIVO_ENTRADA, COLUNAS_PRODUTOS_BUSCA)

if df.empty:
    salvar_csv(df, ARQUIVO_SAIDA, COLUNAS_PRODUTOS_BUSCA + ["score"])
    print("Nenhuma oferta encontrada para curadoria.")
    exit()

df["preco"] = pd.to_numeric(df["preco"], errors="coerce").fillna(0)
df["desconto"] = pd.to_numeric(df["desconto"], errors="coerce").fillna(0)

if os.path.exists(ARQUIVO_HISTORICO):
    historico = pd.read_csv(ARQUIVO_HISTORICO)
else:
    historico = pd.DataFrame(
        columns=COLUNAS_HISTORICO
    )

historico_produtos = ler_csv(
    ARQUIVO_HISTORICO_PRODUTOS,
    COLUNAS_HISTORICO_PRODUTOS,
)
historico_produtos["preco"] = pd.to_numeric(
    historico_produtos["preco"],
    errors="coerce",
).fillna(0)

df = df[df["preco"] > 0]
df = df[df["tipo_promocao"].isin(TIPOS_PROMOCAO_VALIDOS)]

if "preco_confiavel" in df.columns:
    df["preco_confiavel"] = df["preco_confiavel"].fillna("").astype(str).str.lower()

duplicados_item_id = df[df.duplicated(subset=["item_id"], keep="first")]

for _, produto_duplicado in duplicados_item_id.iterrows():
    log_curadoria(
        f"Rejeitado item_id duplicado na coleta: {produto_duplicado.get('titulo', '')}",
        dados=str(produto_duplicado.get("item_id", "")),
    )

df = df.drop_duplicates(subset=["item_id"])
posts = ler_posts("posts_prontos.csv")
posts["preco"] = pd.to_numeric(posts["preco"], errors="coerce").fillna(0)
posts_pendentes = posts[posts["status"] == "pendente"]
posts_publicados = posts[
    (posts["status"] == "aprovado")
    | (posts["status_telegram"] == "enviado")
]

produtos_aprovados = []
historico_produtos_registros = []

for _, produto in df.iterrows():
    item_id = produto.get("item_id", "")
    titulo = produto["titulo"]
    preco = float(produto["preco"])

    analise = analisar_produto(produto)
    score = analise["score"]

    historico_produtos_registros.append({
        "item_id": item_id,
        "preco": preco,
        "desconto": float(produto.get("desconto", 0)),
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "score": score,
    })

    if score < LIMITE_FILA:
        log_curadoria(
            f"Rejeitado por score insuficiente ({score}): {titulo}",
            dados=analise["motivo"],
        )
        continue

    if item_id:
        registros_pendentes = posts_pendentes[
            posts_pendentes["item_id"].astype(str) == str(item_id)
        ]

        if not registros_pendentes.empty:
            log_curadoria(
                f"Rejeitado já pendente na fila: {titulo}",
                dados=str(item_id),
            )
            continue

        registros_postados = posts_publicados[
            posts_publicados["item_id"].astype(str) == str(item_id)
        ]

        if not registros_postados.empty:
            menor_preco_postado = float(registros_postados["preco"].min())

            if preco >= menor_preco_postado:
                log_curadoria(
                    f"Rejeitado já publicado sem queda real de preço: "
                    f"{titulo} (R$ {menor_preco_postado} -> R$ {preco})"
                )
                continue

            log_curadoria(
                f"Preço caiu desde a publicação: "
                f"{titulo} (R$ {menor_preco_postado} -> R$ {preco})"
            )

    registros_historico_produto = historico_produtos[
        historico_produtos["item_id"].astype(str) == str(item_id)
    ]

    if item_id and not registros_historico_produto.empty:
        menor_preco_historico = float(registros_historico_produto["preco"].min())

        if preco >= menor_preco_historico:
            log_curadoria(
                f"Primeira publicação permitida sem queda no histórico de produtos: "
                f"{titulo} (R$ {menor_preco_historico} -> R$ {preco})"
            )
        else:
            log_curadoria(
            f"Preço caiu no histórico de produtos: "
            f"{titulo} (R$ {menor_preco_historico} -> R$ {preco})"
            )

    if item_id and item_id in historico["item_id"].values:
        registro = historico[historico["item_id"] == item_id].iloc[-1]
        menor_preco = float(registro["menor_preco"])

        if preco >= menor_preco:
            log_curadoria(
                f"Primeira publicação permitida sem queda histórica: "
                f"{titulo} (R$ {menor_preco} -> R$ {preco})"
            )
        else:
            log_curadoria(f"Preço caiu no histórico: {titulo} | R$ {menor_preco} -> R$ {preco}")

    produto = produto.copy()
    produto["score"] = score
    produtos_aprovados.append(produto)

df_saida = pd.DataFrame(produtos_aprovados)

colunas_saida = list(df.columns)

if "score" not in colunas_saida:
    colunas_saida.append("score")

df_saida = pd.DataFrame(produtos_aprovados)

if df_saida.empty:
    df_saida = pd.DataFrame(columns=colunas_saida)

df_saida = salvar_csv(df_saida, ARQUIVO_SAIDA, colunas_saida)

historico_atualizado = []

for _, produto in df.iterrows():
    item_id = produto.get("item_id", "")
    titulo = produto["titulo"]
    preco = float(produto["preco"])

    if item_id in historico["item_id"].values:
        registro = historico[historico["item_id"] == item_id].iloc[-1]
        menor_preco = min(float(registro["menor_preco"]), preco)
    else:
        menor_preco = preco

    historico_atualizado.append({
        "item_id": item_id,
        "titulo": titulo,
        "menor_preco": menor_preco,
        "ultima_data": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

salvar_csv(
    pd.DataFrame(historico_atualizado),
    ARQUIVO_HISTORICO,
    COLUNAS_HISTORICO,
)

if historico_produtos_registros:
    historico_produtos_atualizado = pd.concat(
        [
            historico_produtos,
            pd.DataFrame(
                historico_produtos_registros,
                columns=COLUNAS_HISTORICO_PRODUTOS,
            ),
        ],
        ignore_index=True,
    )
else:
    historico_produtos_atualizado = historico_produtos

salvar_csv(
    historico_produtos_atualizado,
    ARQUIVO_HISTORICO_PRODUTOS,
    COLUNAS_HISTORICO_PRODUTOS,
)

print(f"Produtos aprovados pela curadoria: {len(df_saida)}")
print("Arquivo criado:", ARQUIVO_SAIDA)
print("Histórico de produtos atualizado:", ARQUIVO_HISTORICO_PRODUTOS)
