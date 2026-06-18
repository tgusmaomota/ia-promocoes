import json
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

from banco import conectar, inicializar_banco, registrar_log
from gerador_link_mercadolivre import link_afiliado_valido


SITE_DIR = Path("site")
INDEX_PATH = SITE_DIR / "index.html"
STYLE_PATH = SITE_DIR / "style.css"
OFERTAS_PATH = SITE_DIR / "ofertas.json"


def formatar_preco(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def listar_ofertas():
    inicializar_banco()
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                titulo,
                preco,
                link_afiliado,
                plataforma,
                categoria,
                status,
                data_criacao,
                data_publicacao
            FROM postagens
            WHERE plataforma = 'mercado_livre'
              AND status IN ('pendente', 'publicado')
            ORDER BY
                CASE status WHEN 'pendente' THEN 0 ELSE 1 END,
                data_criacao DESC
            """
        ).fetchall()

    ofertas = []
    links_usados = set()

    for row in rows:
        oferta = dict(row)
        link = str(oferta.get("link_afiliado") or "").strip()

        if not link_afiliado_valido(link) or link in links_usados:
            continue

        links_usados.add(link)
        categoria = str(oferta.get("categoria") or "ofertas").strip() or "ofertas"
        ofertas.append({
            "id": oferta["id"],
            "titulo": str(oferta["titulo"]).strip(),
            "preco": float(oferta.get("preco") or 0),
            "preco_formatado": formatar_preco(oferta.get("preco")),
            "categoria": categoria,
            "link": link,
            "plataforma": "Mercado Livre",
            "status": str(oferta.get("status") or "pendente"),
            "data_criacao": oferta.get("data_criacao"),
            "data_publicacao": oferta.get("data_publicacao"),
        })

    return ofertas


def escrever_css():
    css = """* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    color: #1f2933;
    background: #f4f6f8;
}

header {
    background: #263238;
    color: #fff;
    padding: 28px 24px;
}

.topo {
    max-width: 1120px;
    margin: 0 auto;
}

h1 {
    margin: 0 0 8px;
    font-size: 32px;
    line-height: 1.15;
}

.subtitulo {
    margin: 0;
    color: #d7e0e6;
    line-height: 1.45;
}

nav {
    background: #fff;
    border-bottom: 1px solid #d9e1e8;
}

.categorias {
    max-width: 1120px;
    margin: 0 auto;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    padding: 14px 24px;
}

.categorias a {
    color: #263238;
    background: #edf2f7;
    border: 1px solid #d9e1e8;
    border-radius: 6px;
    padding: 8px 11px;
    text-decoration: none;
    font-size: 14px;
}

main {
    max-width: 1120px;
    margin: 0 auto;
    padding: 24px;
}

.secao-categoria {
    margin-bottom: 34px;
}

.secao-categoria h2 {
    font-size: 22px;
    margin: 0 0 14px;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 16px;
}

.card {
    background: #fff;
    border: 1px solid #d9e1e8;
    border-radius: 8px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    min-height: 220px;
}

.meta {
    color: #60717f;
    font-size: 13px;
    margin: 0 0 8px;
}

.card h3 {
    font-size: 17px;
    line-height: 1.35;
    margin: 0 0 14px;
}

.preco {
    color: #087443;
    font-size: 24px;
    font-weight: 700;
    margin: auto 0 14px;
}

.botao {
    align-self: flex-start;
    background: #3483fa;
    border-radius: 6px;
    color: #fff;
    padding: 10px 14px;
    text-decoration: none;
    font-weight: 700;
}

.vazio {
    background: #fff;
    border: 1px solid #d9e1e8;
    border-radius: 8px;
    padding: 18px;
}

footer {
    max-width: 1120px;
    margin: 0 auto;
    padding: 12px 24px 28px;
    color: #60717f;
    font-size: 13px;
}
"""
    STYLE_PATH.write_text(css, encoding="utf-8")


def montar_index(ofertas):
    categorias = defaultdict(list)
    for oferta in ofertas:
        categorias[oferta["categoria"]].append(oferta)

    links_categoria = "".join(
        f'<a href="#categoria-{escape(categoria, quote=True)}">{escape(categoria)}</a>'
        for categoria in sorted(categorias)
    )

    secoes = []
    for categoria in sorted(categorias):
        cards = []
        for oferta in categorias[categoria]:
            cards.append(f"""
            <article class="card">
                <p class="meta">{escape(oferta['plataforma'])} · {escape(oferta['status'])}</p>
                <h3>{escape(oferta['titulo'])}</h3>
                <p class="preco">{escape(oferta['preco_formatado'])}</p>
                <a class="botao" href="{escape(oferta['link'], quote=True)}" target="_blank" rel="noopener sponsored">Ver oferta</a>
            </article>
            """)

        secoes.append(f"""
        <section class="secao-categoria" id="categoria-{escape(categoria, quote=True)}">
            <h2>{escape(categoria)}</h2>
            <div class="grid">{''.join(cards)}</div>
        </section>
        """)

    conteudo = "".join(secoes) if secoes else '<p class="vazio">Nenhuma oferta disponível agora.</p>'
    atualizado_em = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="index, follow">
    <title>Minhas Ofertas Mercado Livre</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <div class="topo">
            <h1>Minhas Ofertas Mercado Livre</h1>
            <p class="subtitulo">Ofertas selecionadas automaticamente, sempre com link afiliado validado.</p>
        </div>
    </header>
    <nav>
        <div class="categorias">{links_categoria}</div>
    </nav>
    <main>{conteudo}</main>
    <footer>Atualizado em {escape(atualizado_em)}. Os preços podem mudar no Mercado Livre.</footer>
</body>
</html>
"""


def gerar_site():
    SITE_DIR.mkdir(exist_ok=True)
    ofertas = listar_ofertas()

    OFERTAS_PATH.write_text(
        json.dumps(
            {
                "gerado_em": datetime.now().isoformat(timespec="seconds"),
                "plataforma": "mercado_livre",
                "total": len(ofertas),
                "ofertas": ofertas,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    escrever_css()
    INDEX_PATH.write_text(montar_index(ofertas), encoding="utf-8")

    registrar_log("site", f"Site público gerado com {len(ofertas)} ofertas em {SITE_DIR}/")
    return {"ofertas": len(ofertas), "pasta": str(SITE_DIR)}


if __name__ == "__main__":
    resultado = gerar_site()
    print(f"Site gerado: {resultado['ofertas']} ofertas em {resultado['pasta']}")
