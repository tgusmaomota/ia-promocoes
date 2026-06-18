import csv
import os
from datetime import datetime

from analisador import eh_promocao
from gerador_texto import gerar_post
from coletor import gerar_link_afiliado
from schema_posts import garantir_arquivo_posts, ler_posts, salvar_posts

def link_ja_salvo(link):
    garantir_arquivo_posts("posts_prontos.csv")

    if not os.path.exists("posts_prontos.csv"):
        return False

    with open("posts_prontos.csv", newline="", encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo)

        for linha in leitor:
            if linha["link"] == link:
                return True

    return False


if not os.path.exists("produtos.csv"):
    print("Arquivo produtos.csv nao encontrado. Adicione produtos pelo painel ou crie o arquivo antes de gerar posts.")
    raise SystemExit(0)

with open("produtos.csv", newline="", encoding="utf-8") as arquivo:
    leitor = csv.DictReader(arquivo)

    for produto in leitor:
        produto["preco"] = float(produto["preco"])
        produto["link"] = gerar_link_afiliado(produto["link"])

        if link_ja_salvo(produto["link"]):
            print("Já existe:", produto["titulo"])
            continue

        if eh_promocao(produto):
            texto = gerar_post(produto)
            df_posts = ler_posts("posts_prontos.csv")

            novo_post = {
                "titulo": produto["titulo"],
                "item_id": produto.get("item_id", ""),
                "score": produto.get("score", 0),
                "preco": produto["preco"],
                "link": produto["link"],
                "categoria": produto.get("categoria", "outros"),
                "imagem": produto.get("imagem", ""),
                "post": texto,
                "status": "pendente",
                "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "log_aprovacao": (
                    "Pendente: item sem confiança suficiente: "
                    "produto manual sem score, desconto e validação de preço"
                ),
                "status_telegram": "",
            }

            df_posts.loc[len(df_posts)] = novo_post
            salvar_posts(df_posts, "posts_prontos.csv")

            print("Post salvo:", produto["titulo"])
