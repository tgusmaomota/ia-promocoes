from schema_posts import ler_posts, salvar_posts

ARQUIVO = "posts_prontos.csv"

df_corrigido = ler_posts(ARQUIVO)
salvar_posts(df_corrigido, ARQUIVO)

print("posts_prontos.csv recriado com as colunas corretas.")
