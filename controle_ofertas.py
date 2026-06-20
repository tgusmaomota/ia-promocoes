from datetime import datetime

import pandas as pd

from banco import conectar, editar_postagem_manual, listar_postagens, obter_postagem, registrar_log
from gerador_link_mercadolivre import link_afiliado_valido
from schema_posts import ler_posts, salvar_posts


ARQUIVO_POSTS = "posts_prontos.csv"


def _dados_csv(postagem):
    with conectar() as conn:
        produto = conn.execute("SELECT item_id, imagem FROM produtos WHERE id = ?", (postagem.get("produto_id"),)).fetchone()
    item_id = str(produto["item_id"] if produto else "").strip()
    return {
        "titulo": postagem.get("titulo", ""),
        "item_id": item_id,
        "preco": postagem.get("preco", 0),
        "link": str(postagem.get("link_afiliado", "")).strip(),
        "categoria": postagem.get("categoria", "ofertas"),
        "imagem": produto["imagem"] if produto else "",
        "post": postagem.get("texto_post", ""),
        "status": postagem.get("status", "pendente_revisao"),
        "data_criacao": postagem.get("data_criacao", ""),
        "log_aprovacao": postagem.get("motivo", ""),
        "status_telegram": "enviado" if postagem.get("status") == "publicado" else "",
        "observacao_interna": postagem.get("observacao_interna", ""),
        "aprovado_por": postagem.get("aprovado_por", ""),
        "aprovado_em": postagem.get("aprovado_em", ""),
        "atualizado_em": postagem.get("atualizado_em", ""),
    }


def _aplicar_postagem_csv(df, postagem):
    dados = _dados_csv(postagem)
    mascara = df["link"].astype(str).str.strip() == dados["link"]
    if mascara.any():
        for coluna, valor in dados.items():
            df.loc[mascara, coluna] = valor
    else:
        df = pd.concat([df, pd.DataFrame([dados])], ignore_index=True)
    return df


def sincronizar_postagem_csv(postagem, caminho=ARQUIVO_POSTS):
    """Mantém o CSV legado alinhado ao SQLite sem torná-lo fonte de verdade."""
    df = _aplicar_postagem_csv(ler_posts(caminho), postagem)
    salvar_posts(df, caminho)


def sincronizar_todas_postagens_csv(caminho=ARQUIVO_POSTS):
    df = ler_posts(caminho)
    for postagem in listar_postagens():
        df = _aplicar_postagem_csv(df, postagem)
    salvar_posts(df, caminho)
    return len(df)


def editar_oferta(postagem_id, dados, ator="painel_manual"):
    if dados.get("status") in {"aprovado_auto", "aprovado_manual"} and not link_afiliado_valido(dados.get("link_afiliado")):
        raise ValueError("Uma oferta aprovada precisa de link afiliado válido")
    postagem = editar_postagem_manual(postagem_id, dados, ator=ator)
    sincronizar_postagem_csv(postagem)
    registrar_log(
        "auditoria_painel",
        f"CSV sincronizado após edição: postagem={postagem_id}",
    )
    return postagem


def aprovar_manual(postagem_id, observacao="", ator="painel_manual"):
    postagem = obter_postagem(postagem_id)
    if not postagem:
        raise ValueError("Oferta não encontrada")
    if not link_afiliado_valido(postagem.get("link_afiliado")):
        raise ValueError("Não é possível aprovar sem link afiliado válido")
    dados = {
        "titulo": postagem["titulo"],
        "preco": postagem["preco"],
        "categoria": postagem["categoria"],
        "texto_post": postagem["texto_post"],
        "link_afiliado": postagem["link_afiliado"],
        "imagem_url": postagem.get("imagem_url", ""),
        "status": "aprovado_manual",
        "observacao_interna": observacao or postagem.get("observacao_interna", ""),
    }
    resultado = editar_oferta(postagem_id, dados, ator)
    registrar_log(
        "auditoria_aprovacao",
        f"Aprovação manual: postagem={postagem_id}",
        dados=f"ator={ator} data={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )
    return resultado


def rejeitar_oferta(postagem_id, observacao="", ator="painel_manual"):
    postagem = obter_postagem(postagem_id)
    if not postagem:
        raise ValueError("Oferta não encontrada")
    dados = {
        "titulo": postagem["titulo"],
        "preco": postagem["preco"],
        "categoria": postagem["categoria"],
        "texto_post": postagem["texto_post"],
        "link_afiliado": postagem["link_afiliado"],
        "imagem_url": postagem.get("imagem_url", ""),
        "status": "rejeitado",
        "observacao_interna": observacao or postagem.get("observacao_interna", ""),
    }
    resultado = editar_oferta(postagem_id, dados, ator)
    registrar_log("auditoria_aprovacao", f"Rejeição manual: postagem={postagem_id}", dados=f"ator={ator}")
    return resultado
