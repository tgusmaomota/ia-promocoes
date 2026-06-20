import os
from datetime import date, datetime
from html import escape
from pathlib import Path

import requests
from dotenv import load_dotenv

from banco import (
    atualizar_status_postagem,
    conectar,
    listar_postagens,
    proxima_postagem_pendente,
    registrar_log,
    registrar_evento_sistema,
    status_aprovado,
)
from fila_postagens import link_afiliado_valido, pode_publicar_texto, respeita_intervalo_minimo
from gerar_site import gerar_site
from estado_sistema import automacao_ativa


load_dotenv()

ARQUIVO_SITE = "site_promocoes.html"
PASTA_SITE = Path("site")
ARQUIVO_SITE_PUBLICO = PASTA_SITE / "index.html"
ARQUIVO_WHATSAPP_TXT = "whatsapp_posts.txt"
ARQUIVO_WHATSAPP_HTML = PASTA_SITE / "whatsapp.html"
ARQUIVO_POSTS = "posts_prontos.csv"


def intervalo_postagem():
    try:
        return int(os.getenv("INTERVALO_POSTAGEM_MINUTOS", "20"))
    except ValueError:
        return 20


def limite_posts_dia():
    try:
        return int(os.getenv("LIMITE_POSTS_DIA", "10"))
    except ValueError:
        return 10


def posts_publicados_hoje():
    hoje = date.today().strftime("%Y-%m-%d")

    with conectar() as conn:
        return conn.execute(
            """
            SELECT COUNT(*)
            FROM postagens
            WHERE status = 'publicado'
              AND substr(COALESCE(data_publicacao, ''), 1, 10) = ?
            """,
            (hoje,),
        ).fetchone()[0]


def link_ou_texto_ja_publicado(postagem):
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT id
            FROM postagens
            WHERE status = 'publicado'
              AND id != ?
              AND (link_afiliado = ? OR texto_post = ?)
            LIMIT 1
            """,
            (
                postagem["id"],
                postagem["link_afiliado"],
                postagem["texto_post"],
            ),
        ).fetchone()

    return row is not None


def sincronizar_posts_csv(postagem, data_publicacao):
    from schema_posts import ler_posts, salvar_posts

    df = ler_posts(ARQUIVO_POSTS)

    if df.empty:
        registrar_log("publicador", "posts_prontos.csv vazio ao sincronizar publicação", nivel="warning")
        return False

    link = str(postagem.get("link_afiliado", "")).strip()
    mascara = df["link"].astype(str).str.strip() == link

    if not mascara.any():
        registrar_log(
            "publicador",
            f"Post publicado no SQLite não encontrado no CSV: {postagem.get('titulo', '')}",
            nivel="warning",
        )
        return False

    df.loc[mascara, "status"] = "publicado"
    df.loc[mascara, "status_telegram"] = "enviado"
    salvar_posts(df, ARQUIVO_POSTS)
    registrar_log(
        "publicador",
        f"CSV sincronizado para publicação: {postagem.get('titulo', '')}",
        dados=data_publicacao,
    )
    return True


def validar_postagem(postagem, forcar_intervalo=False):
    if not postagem:
        return False, "Nenhuma postagem pendente"

    if not status_aprovado(postagem.get("status")):
        return False, "oferta não possui aprovação válida"

    if not link_afiliado_valido(postagem):
        return False, "link afiliado ausente ou inválido"

    if link_ou_texto_ja_publicado(postagem):
        return False, "link ou texto já publicado anteriormente"

    publicados_hoje = posts_publicados_hoje()
    limite = limite_posts_dia()

    if publicados_hoje >= limite:
        return False, f"limite diário atingido: {publicados_hoje}/{limite}"

    if not forcar_intervalo and not respeita_intervalo_minimo(intervalo_postagem()):
        return False, f"intervalo mínimo ainda não respeitado: {intervalo_postagem()} minutos"

    ok_texto, motivo_texto = pode_publicar_texto(postagem["texto_post"])

    if not ok_texto:
        return False, f"anti-spam: {motivo_texto}"

    return True, "ok"


def publicar_telegram(postagem):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        return False, "Telegram não configurado no .env"

    resposta = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": postagem["texto_post"],
        },
        timeout=30,
    )

    if resposta.status_code != 200:
        return False, f"Erro Telegram {resposta.status_code}: {resposta.text}"

    return True, "publicado"


def gerar_site_local():
    resultado = gerar_site()
    if ARQUIVO_SITE_PUBLICO.exists():
        with open(ARQUIVO_SITE_PUBLICO, encoding="utf-8") as origem:
            with open(ARQUIVO_SITE, "w", encoding="utf-8") as destino:
                destino.write(origem.read())

    gerar_whatsapp_manual()
    registrar_log("site", f"Site local atualizado: {resultado['ofertas']} ofertas")


def gerar_whatsapp_manual(postagens=None):
    if postagens is None:
        postagens = [
            p for p in listar_postagens()
            if status_aprovado(p.get("status")) and link_afiliado_valido(p)
        ]

    blocos = []
    for postagem in postagens[:30]:
        titulo = str(postagem["titulo"]).strip()
        preco = float(postagem["preco"])
        link = str(postagem["link_afiliado"]).strip()
        categoria = str(postagem.get("categoria") or "ofertas").strip()
        blocos.append(
            "\n".join([
                "Oferta Mercado Livre",
                titulo,
                f"Preço: R$ {preco:.2f}",
                f"Categoria: {categoria}",
                f"Link: {link}",
            ])
        )

    texto = "\n\n---\n\n".join(blocos)
    if not texto:
        texto = "Nenhuma oferta pendente com link afiliado válido no momento."

    with open(ARQUIVO_WHATSAPP_TXT, "w", encoding="utf-8") as arquivo:
        arquivo.write(texto + "\n")

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Copiar para WhatsApp</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 0; background: #f3f5f7; color: #1f2933; }}
header {{ background: #075e54; color: white; padding: 24px; }}
main {{ padding: 24px; }}
textarea {{ width: 100%; min-height: 70vh; padding: 16px; border: 1px solid #cbd5df; border-radius: 8px; font-size: 15px; line-height: 1.45; box-sizing: border-box; }}
</style>
</head>
<body>
<header><h1>Copiar para WhatsApp</h1></header>
<main><textarea readonly>{escape(texto)}</textarea></main>
</body>
</html>"""

    with open(ARQUIVO_WHATSAPP_HTML, "w", encoding="utf-8") as arquivo:
        arquivo.write(html)

    registrar_log("whatsapp", f"Texto manual atualizado: {ARQUIVO_WHATSAPP_TXT}")


def publicar_um(dry_run=False, forcar_intervalo=False):
    if not dry_run and not automacao_ativa():
        registrar_log("publicador", "Publicação Telegram pausada pelo estado mestre", nivel="warning")
        return False
    postagem = proxima_postagem_pendente()

    if not postagem:
        registrar_log("publicador", "Nenhuma postagem pendente")
        gerar_site_local()
        return False

    ok, motivo = validar_postagem(postagem, forcar_intervalo=forcar_intervalo)

    if not ok:
        registrar_log(
            "publicador",
            f"Publicação bloqueada: {motivo} | {postagem.get('titulo', '')}",
            nivel="warning",
        )
        gerar_site_local()
        return False

    if dry_run:
        registrar_log(
            "publicador",
            (
                "DRY-RUN: publicaria 1 post: "
                f"{postagem['titulo']} | R$ {float(postagem['preco']):.2f} | "
                f"{postagem['link_afiliado']}"
            ),
        )
        gerar_site_local()
        return True

    ok, motivo = publicar_telegram(postagem)

    if not ok:
        registrar_log("publicador", motivo, nivel="error")
        registrar_evento_sistema("telegram", "telegram", "erro", "Falha na publicação Telegram", motivo)
        gerar_site_local()
        return False

    data_publicacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    atualizar_status_postagem(
        postagem["id"],
        "publicado",
        "Publicado no Telegram",
        data_publicacao,
        ator="telegram",
    )
    sincronizar_posts_csv(postagem, data_publicacao)
    registrar_log("publicador", f"Post publicado: {postagem['titulo']}")
    registrar_log(
        "auditoria_telegram",
        f"Oferta publicada no Telegram: postagem={postagem['id']}",
        dados=f"aprovacao={postagem.get('status', '')}",
    )
    registrar_evento_sistema("telegram", "telegram", "concluido", "Oferta publicada no Telegram", f"postagem={postagem['id']}")
    gerar_site_local()
    return True


def publicar_proximo(forcar=False):
    return publicar_um(dry_run=False, forcar_intervalo=forcar)


if __name__ == "__main__":
    publicar_um()
