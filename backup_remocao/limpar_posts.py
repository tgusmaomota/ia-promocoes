# limpar_posts.py

import pandas as pd
from schema_posts import ler_posts, salvar_posts

df = ler_posts("posts_prontos.csv")
salvar_posts(df, "posts_prontos.csv")

print("Arquivo corrigido.")
