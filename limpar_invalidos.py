from schema_posts import ler_posts, salvar_posts

ARQUIVO = "posts_prontos.csv"

df = ler_posts(ARQUIVO)

df["titulo"] = df["titulo"].astype(str)
df["post"] = df["post"].astype(str)

df = df[df["titulo"].str.strip() != ""]
df = df[df["titulo"].str.strip() != "0"]
df = df[df["post"].str.strip() != ""]
df = df[df["post"].str.strip() != "0"]
df = df[df["post"].str.len() > 20]

salvar_posts(df, ARQUIVO)

print("Registros inválidos removidos.")
print("Total restante:", len(df))
