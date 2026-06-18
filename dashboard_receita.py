import os

import pandas as pd
import streamlit as st

from schema_posts import ler_posts


ARQUIVO_POSTS = "posts_prontos.csv"
ARQUIVO_HISTORICO_PRODUTOS = "historico_produtos.csv"
COLUNAS_HISTORICO_PRODUTOS = ["item_id", "preco", "desconto", "data", "score"]


def ler_historico_produtos():
    if not os.path.exists(ARQUIVO_HISTORICO_PRODUTOS):
        return pd.DataFrame(columns=COLUNAS_HISTORICO_PRODUTOS)

    df = pd.read_csv(ARQUIVO_HISTORICO_PRODUTOS, engine="python", on_bad_lines="skip")

    for coluna in COLUNAS_HISTORICO_PRODUTOS:
        if coluna not in df.columns:
            df[coluna] = ""

    df = df[COLUNAS_HISTORICO_PRODUTOS].fillna("")
    df["preco"] = pd.to_numeric(df["preco"], errors="coerce").fillna(0)
    df["desconto"] = pd.to_numeric(df["desconto"], errors="coerce").fillna(0)
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    return df


def dinheiro(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.set_page_config(page_title="Dashboard de Receita", layout="wide")
st.title("Dashboard de Receita")

df_posts = ler_posts(ARQUIVO_POSTS)
df_historico = ler_historico_produtos()

df_posts["preco"] = pd.to_numeric(df_posts["preco"], errors="coerce").fillna(0)
df_posts["score"] = pd.to_numeric(df_posts["score"], errors="coerce").fillna(0)
df_posts["data_criacao"] = pd.to_datetime(
    df_posts["data_criacao"],
    errors="coerce",
)

aprovados = df_posts[df_posts["status"] == "aprovado"].copy()
enviados = aprovados[aprovados["status_telegram"] == "enviado"].copy()

taxa_comissao = st.sidebar.number_input(
    "Comissão estimada (%)",
    min_value=0.0,
    max_value=100.0,
    value=4.0,
    step=0.5,
)

base_receita = st.sidebar.selectbox(
    "Base de cálculo",
    ["Aprovados", "Enviados no Telegram"],
)

df_receita = enviados if base_receita == "Enviados no Telegram" else aprovados
valor_total = float(df_receita["preco"].sum())
receita_estimada = valor_total * (taxa_comissao / 100)
ticket_medio = float(df_receita["preco"].mean()) if not df_receita.empty else 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Posts aprovados", len(aprovados))

with col2:
    st.metric("Enviados no Telegram", len(enviados))

with col3:
    st.metric("Valor monitorado", dinheiro(valor_total))

with col4:
    st.metric("Receita estimada", dinheiro(receita_estimada))

st.metric("Ticket médio", dinheiro(ticket_medio))

st.subheader("Receita por dia")

if df_receita.empty:
    st.info("Ainda não há posts para calcular receita.")
else:
    receita_dia = df_receita.copy()
    receita_dia["dia"] = receita_dia["data_criacao"].dt.date
    receita_dia = (
        receita_dia.groupby("dia", dropna=False)
        .agg(produtos=("titulo", "count"), valor=("preco", "sum"))
        .reset_index()
    )
    receita_dia["receita_estimada"] = receita_dia["valor"] * (taxa_comissao / 100)

    st.bar_chart(receita_dia.set_index("dia")["receita_estimada"])
    st.dataframe(receita_dia, use_container_width=True)

st.subheader("Histórico de produtos")

if df_historico.empty:
    st.info("historico_produtos.csv ainda está vazio.")
else:
    menor_preco = (
        df_historico.groupby("item_id", as_index=False)
        .agg(
            menor_preco=("preco", "min"),
            ultimo_preco=("preco", "last"),
            ultimo_desconto=("desconto", "last"),
            ultimo_score=("score", "last"),
            ultima_data=("data", "last"),
        )
        .sort_values("ultima_data", ascending=False)
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Produtos no histórico", menor_preco["item_id"].nunique())

    with col2:
        st.metric("Registros de preço", len(df_historico))

    with col3:
        st.metric("Menor preço médio", dinheiro(float(menor_preco["menor_preco"].mean())))

    st.dataframe(menor_preco, use_container_width=True)

st.subheader("Produtos aprovados")

colunas = [
    "item_id",
    "titulo",
    "preco",
    "score",
    "status_telegram",
    "data_criacao",
    "log_aprovacao",
]

st.dataframe(aprovados[colunas], use_container_width=True)
