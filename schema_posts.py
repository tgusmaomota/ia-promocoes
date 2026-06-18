import os

import pandas as pd
from csv_utils import backup_arquivo


ARQUIVO_POSTS = "posts_prontos.csv"

COLUNAS_POSTS = [
    "titulo",
    "item_id",
    "score",
    "preco",
    "link",
    "categoria",
    "imagem",
    "post",
    "status",
    "data_criacao",
    "log_aprovacao",
    "status_telegram",
]

VALORES_PADRAO = {
    "titulo": "",
    "item_id": "",
    "score": 0,
    "preco": 0,
    "link": "",
    "categoria": "outros",
    "imagem": "",
    "post": "",
    "status": "pendente",
    "data_criacao": "",
    "log_aprovacao": "",
    "status_telegram": "",
}


def normalizar_posts(df):
    df = df.copy()

    for coluna in COLUNAS_POSTS:
        if coluna not in df.columns:
            df[coluna] = VALORES_PADRAO[coluna]

    df = df[COLUNAS_POSTS]
    df = df.fillna("")

    return df


def ler_posts(caminho=ARQUIVO_POSTS):
    if not os.path.exists(caminho):
        return pd.DataFrame(columns=COLUNAS_POSTS)

    df = pd.read_csv(caminho, engine="python", on_bad_lines="skip")
    return normalizar_posts(df)


def salvar_posts(df, caminho=ARQUIVO_POSTS, criar_backup=True):
    if criar_backup:
        backup = backup_arquivo(caminho)
        if backup:
            print(f"Backup criado: {backup}")

    normalizar_posts(df).to_csv(caminho, index=False, encoding="utf-8-sig")


def garantir_arquivo_posts(caminho=ARQUIVO_POSTS):
    if not os.path.exists(caminho):
        salvar_posts(pd.DataFrame(columns=COLUNAS_POSTS), caminho, criar_backup=False)
