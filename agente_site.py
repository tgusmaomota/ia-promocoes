from html import escape

from schema_posts import ler_posts

ARQUIVO_POSTS = "posts_prontos.csv"
ARQUIVO_SITE = "site_promocoes.html"

df = ler_posts(ARQUIVO_POSTS)

aprovados = df[df["status"] == "aprovado"]

html = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Promoções do Thiago</title>
<style>
body { font-family: Arial; background: #f3f3f3; padding: 20px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; }
.card { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px #ccc; }
.card img { max-width: 100%; height: 180px; object-fit: contain; }
.preco { font-size: 22px; font-weight: bold; color: #00a650; }
.botao { display: block; background: #3483fa; color: white; padding: 12px; text-align: center; border-radius: 8px; text-decoration: none; }
</style>
</head>
<body>
<h1>🔥 Promoções do Thiago</h1>
<div class="grid">
"""

for _, linha in aprovados.iterrows():
    imagem = str(linha.get("imagem", "")).strip()
    titulo = escape(str(linha.get("titulo", "")).strip())
    preco = escape(str(linha.get("preco", "")).strip())
    link = escape(str(linha.get("link", "")).strip(), quote=True)
    imagem = escape(imagem, quote=True)

    html += f"""
    <div class="card">
        <img src="{imagem}">
        <h2>{titulo}</h2>
        <p class="preco">R$ {preco}</p>
        <a class="botao" href="{link}" target="_blank">Comprar agora</a>
    </div>
    """

html += """
</div>
</body>
</html>
"""

with open(ARQUIVO_SITE, "w", encoding="utf-8") as f:
    f.write(html)

print("Site criado:", ARQUIVO_SITE)
print("Produtos publicados:", len(aprovados))
