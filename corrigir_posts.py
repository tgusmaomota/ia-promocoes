from schema_posts import ler_posts, salvar_posts


ARQUIVO = "posts_prontos.csv"

df = ler_posts(ARQUIVO)
salvar_posts(df, ARQUIVO)

print("Arquivo corrigido com sucesso.")
print("Colunas mantidas no padrão atual de posts_prontos.csv.")
