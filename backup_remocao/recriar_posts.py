import pandas as pd
import shutil
from schema_posts import ler_posts, salvar_posts

ARQUIVO = "posts_prontos.csv"
BACKUP = "posts_prontos_backup_antes_recriar.csv"

shutil.copy(ARQUIVO, BACKUP)

df = ler_posts(ARQUIVO)
salvar_posts(df, ARQUIVO)

print("posts_prontos.csv recriado com 11 colunas.")
print("Backup criado em:", BACKUP)
