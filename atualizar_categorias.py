"""Sincroniza categorias reais do Mercado Livre por item_id, com fallback local."""

from collections import Counter
from datetime import datetime
from pathlib import Path

from banco import conectar, inicializar_banco, registrar_evento_sistema, registrar_log
from mercadolivre_api import ErroMercadoLivre, consultar_categoria, consultar_item, item_id_valido


RELATORIO = Path("RELATORIO_ATUALIZACAO_CATEGORIAS.md")
GENERICAS = {"", "ofertas", "oferta", "sem categoria"}


def _produtos():
    inicializar_banco()
    with conectar() as conn:
        return [dict(row) for row in conn.execute(
            """
            SELECT id, item_id, categoria, categoria_id, categoria_nome
            FROM produtos
            WHERE plataforma = 'mercado_livre' AND item_id IS NOT NULL AND item_id != ''
            ORDER BY id
            """
        ).fetchall()]


def _categoria_atualizada(produto_id, categoria_id, categoria_nome):
    with conectar() as conn:
        conn.execute(
            """
            UPDATE produtos
            SET categoria_id=?, categoria_nome=?, categoria=?, atualizado_em=datetime('now', 'localtime')
            WHERE id=?
            """,
            (categoria_id, categoria_nome, categoria_nome, produto_id),
        )
        conn.execute(
            "UPDATE postagens SET categoria=?, atualizado_em=datetime('now', 'localtime') WHERE produto_id=?",
            (categoria_nome, produto_id),
        )


def atualizar_categorias():
    """Busca categoria e nome oficiais; nunca substitui dado real por fallback genérico."""
    cache = {}
    resultado = {
        "total": 0, "atualizadas": 0, "ja_reais": 0, "fallback": 0,
        "erros": 0, "itens": [], "falhas": [],
    }
    for produto in _produtos():
        item_id = str(produto.get("item_id") or "").strip().upper()
        if not item_id_valido(item_id):
            resultado["fallback"] += 1
            resultado["falhas"].append(f"{item_id or produto['id']}: item_id inválido")
            continue
        resultado["total"] += 1
        try:
            dados_item = consultar_item(item_id)
            if not dados_item.get("disponivel"):
                resultado["fallback"] += 1
                resultado["falhas"].append(f"{item_id}: item indisponível")
                continue
            categoria_id = str(dados_item.get("categoria_id") or "").strip()
            if not categoria_id:
                resultado["fallback"] += 1
                resultado["falhas"].append(f"{item_id}: API não retornou category_id")
                continue
            if categoria_id not in cache:
                cache[categoria_id] = str(consultar_categoria(categoria_id).get("name") or "").strip()
            categoria_nome = cache[categoria_id]
            if not categoria_nome or categoria_nome.lower() in GENERICAS:
                resultado["fallback"] += 1
                resultado["falhas"].append(f"{item_id}: category_id sem nome confiável")
                continue
            mudou = categoria_id != str(produto.get("categoria_id") or "") or categoria_nome != str(produto.get("categoria_nome") or "")
            if mudou:
                _categoria_atualizada(produto["id"], categoria_id, categoria_nome)
                resultado["atualizadas"] += 1
            else:
                resultado["ja_reais"] += 1
            resultado["itens"].append({"item_id": item_id, "categoria": categoria_nome, "mudou": mudou})
        except ErroMercadoLivre as erro:
            resultado["erros"] += 1
            resultado["fallback"] += 1
            resultado["falhas"].append(f"{item_id}: {erro}")
            registrar_log("atualizar_categorias", f"Falha ao consultar {item_id}: {erro}", nivel="warning")
        except Exception as erro:
            resultado["erros"] += 1
            resultado["fallback"] += 1
            resultado["falhas"].append(f"{item_id}: erro inesperado")
            registrar_log("atualizar_categorias", f"Erro ao consultar categoria de {item_id}: {erro}", nivel="error")

    _escrever_relatorio(resultado)
    status = "sucesso" if not resultado["erros"] else "aviso"
    registrar_evento_sistema(
        "categorias", "mercado_livre", status, "Sincronização de categorias concluída",
        f"atualizadas={resultado['atualizadas']} fallback={resultado['fallback']} erros={resultado['erros']}",
    )
    return resultado


def _escrever_relatorio(resultado):
    categorias = Counter(item["categoria"] for item in resultado["itens"])
    linhas = [
        "# Relatório de Atualização de Categorias", "",
        f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Produtos consultados: {resultado['total']}",
        f"- Categorias reais atualizadas: {resultado['atualizadas']}",
        f"- Categorias reais já corretas: {resultado['ja_reais']}",
        f"- Mantidos com fallback local: {resultado['fallback']}",
        f"- Erros de API: {resultado['erros']}", "",
        "## Categorias encontradas",
    ]
    linhas.extend(f"- {nome}: {total}" for nome, total in categorias.most_common(20)) or linhas.append("- nenhuma")
    linhas += ["", "## Falhas e fallbacks"]
    linhas.extend(f"- {falha}" for falha in resultado["falhas"][:50]) or linhas.append("- nenhum")
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
