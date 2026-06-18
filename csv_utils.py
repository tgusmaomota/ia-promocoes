from datetime import datetime
from pathlib import Path
import shutil

import pandas as pd


COLUNAS_PRODUTOS_BUSCA = [
    "titulo",
    "link",
    "item_id",
    "preco",
    "preco_confiavel",
    "desconto",
    "tipo_promocao",
    "imagem",
    "categoria",
]

COLUNAS_PRODUTOS_AFILIADOS = [
    "titulo",
    "item_id",
    "score",
    "preco",
    "preco_confiavel",
    "desconto",
    "tipo_promocao",
    "link_original",
    "link_afiliado",
    "imagem",
    "categoria",
]


def backup_arquivo(caminho):
    origem = Path(caminho)

    if not origem.exists() or origem.stat().st_size == 0:
        return None

    pasta_backup = origem.parent / "backups"
    pasta_backup.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = pasta_backup / f"{origem.stem}_{timestamp}{origem.suffix}"
    shutil.copy2(origem, destino)
    return destino


def normalizar_colunas(df, colunas, valores_padrao=None):
    valores_padrao = valores_padrao or {}
    df = df.copy()

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = valores_padrao.get(coluna, "")

    return df[colunas].fillna("")


def ler_csv(caminho, colunas=None, valores_padrao=None):
    if not Path(caminho).exists():
        if colunas is None:
            return pd.DataFrame()
        return pd.DataFrame(columns=colunas)

    df = pd.read_csv(caminho, engine="python", on_bad_lines="skip")

    if colunas is not None:
        df = normalizar_colunas(df, colunas, valores_padrao)

    return df


def salvar_csv(df, caminho, colunas, valores_padrao=None, criar_backup=True):
    if criar_backup:
        backup = backup_arquivo(caminho)
        if backup:
            print(f"Backup criado: {backup}")

    df = normalizar_colunas(df, colunas, valores_padrao)
    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    return df
