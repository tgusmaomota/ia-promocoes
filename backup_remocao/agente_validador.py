import pandas as pd
from csv_utils import COLUNAS_PRODUTOS_AFILIADOS, ler_csv, salvar_csv

df = ler_csv("produtos_afiliados.csv", COLUNAS_PRODUTOS_AFILIADOS)

df["preco"] = pd.to_numeric(df["preco"], errors="coerce").fillna(0)

df = df[df["preco"] > 50]
df = df[df["preco"] < 2000]

salvar_csv(
    df,
    "produtos_validados.csv",
    COLUNAS_PRODUTOS_AFILIADOS,
)

print("Promoções validadas:", len(df))
