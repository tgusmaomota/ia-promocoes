"""Auditoria somente leitura da qualidade do catálogo público Promogg."""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from banco import conectar
from gerador_link_mercadolivre import link_afiliado_valido


RELATORIO = Path("RELATORIO_QUALIDADE_CATALOGO.md")
SITE = Path("site")


def _imagem_valida(url):
    partes = urlparse(str(url or "").strip())
    return partes.scheme in {"http", "https"} and bool(partes.netloc)


def auditar_qualidade_catalogo():
    dados = json.loads((SITE / "ofertas.json").read_text(encoding="utf-8"))
    ofertas = dados.get("ofertas", [])
    links = [str(oferta.get("link") or "") for oferta in ofertas]
    imagens_validas = sum(_imagem_valida(oferta.get("imagem_url")) for oferta in ofertas)
    imagens_ausentes = sum(not str(oferta.get("imagem_url") or "").strip() for oferta in ofertas)
    links_validos = sum(link_afiliado_valido(link) for link in links)
    duplicados_link = sum(total - 1 for total in Counter(links).values() if total > 1 and links)
    paginas_sem_titulo = paginas_sem_descricao = paginas_sem_categoria = 0
    paginas_detalhe_quebradas = 0
    for oferta in ofertas:
        pagina = SITE / str(oferta.get("produto_url") or "") / "index.html"
        if not pagina.exists():
            paginas_detalhe_quebradas += 1
            continue
        html = pagina.read_text(encoding="utf-8").lower()
        if "<title>" not in html or "</title>" not in html:
            paginas_sem_titulo += 1
        if 'name="description"' not in html:
            paginas_sem_descricao += 1
        if not str(oferta.get("categoria") or "").strip():
            paginas_sem_categoria += 1
    with conectar() as conn:
        status = {row["status"]: row["total"] for row in conn.execute("SELECT status, COUNT(*) AS total FROM postagens GROUP BY status")}
        produtos_publicos = [dict(row) for row in conn.execute(
            """SELECT p.* FROM produtos p JOIN postagens x ON x.produto_id=p.id
               WHERE x.status IN ('aprovado_auto','aprovado_manual','publicado')"""
        ).fetchall()]
    por_item = Counter(str(produto.get("item_id") or "") for produto in produtos_publicos)
    item_duplicado = sum(total - 1 for item, total in por_item.items() if item and total > 1)
    item_ausente = sum(not str(produto.get("item_id") or "").strip() for produto in produtos_publicos)
    permalink_invalido = sum(not str(produto.get("link_original") or "").startswith("https://") for produto in produtos_publicos)
    origem = Counter()
    produtos_unicos = {}
    for produto in produtos_publicos:
        produtos_unicos.setdefault(str(produto.get("item_id") or ""), produto)
    for produto in produtos_unicos.values():
        if str(produto.get("categoria_nome") or "").strip() and str(produto.get("origem_categoria") or "") == "api_oficial":
            origem["api"] += 1
        elif str(produto.get("categoria_caminho") or "").strip():
            origem["breadcrumb"] += 1
        elif str(produto.get("categoria_nome") or produto.get("categoria") or "").strip().lower() not in {"", "ofertas", "oferta"}:
            origem["fallback"] += 1
        else:
            origem["vazia"] += 1
    metricas = {
        "total_ofertas": len(ofertas), "meli_la": links_validos, "sem_meli_la": len(ofertas) - links_validos,
        "links_quebrados": len(ofertas) - links_validos + paginas_detalhe_quebradas,
        "links_duplicados": duplicados_link, "imagens_validas": imagens_validas,
        "imagens_ausentes": imagens_ausentes, "imagens_quebradas": len(ofertas) - imagens_validas - imagens_ausentes,
        "categoria_api": origem["api"], "categoria_breadcrumb": origem["breadcrumb"],
        "categoria_fallback": origem["fallback"], "categoria_vazia": origem["vazia"],
        "preco_invalido": sum(not isinstance(oferta.get("preco"), (int, float)) or float(oferta.get("preco") or 0) <= 0 for oferta in ofertas),
        "preco_zero": sum(float(oferta.get("preco") or 0) == 0 for oferta in ofertas if isinstance(oferta.get("preco"), (int, float))),
        "preco_negativo": sum(float(oferta.get("preco") or 0) < 0 for oferta in ofertas if isinstance(oferta.get("preco"), (int, float))),
        "item_id_duplicado": item_duplicado, "item_id_ausente": item_ausente, "permalink_invalido": permalink_invalido,
        "seo_sem_titulo": paginas_sem_titulo, "seo_sem_descricao": paginas_sem_descricao,
        "seo_sem_categoria": paginas_sem_categoria, "paginas_quebradas": paginas_detalhe_quebradas,
        "status": status,
    }
    problemas_criticos = sum(metricas[chave] for chave in ("sem_meli_la", "preco_invalido", "paginas_quebradas", "seo_sem_titulo", "seo_sem_descricao"))
    ressalvas = sum(metricas[chave] for chave in ("links_duplicados", "imagens_ausentes", "categoria_vazia", "item_id_duplicado", "permalink_invalido"))
    indicador = "REPROVADO" if problemas_criticos else "APROVADO COM RESSALVAS" if ressalvas else "APROVADO"
    resultado = {"metricas": metricas, "indicador": indicador, "problemas_criticos": problemas_criticos, "ressalvas": ressalvas}
    _escrever(resultado)
    return resultado


def _escrever(resultado):
    m = resultado["metricas"]
    status = m["status"]
    linhas = ["# Relatório de Qualidade do Catálogo", "", f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"- Indicador final: **{resultado['indicador']}**", "", "## Links afiliados", f"- Total de ofertas: {m['total_ofertas']}", f"- Com meli.la válido: {m['meli_la']}", f"- Sem meli.la: {m['sem_meli_la']}", f"- Links quebrados/formato inválido: {m['links_quebrados']}", f"- Links duplicados: {m['links_duplicados']}", "", "## Imagens", f"- URLs válidas: {m['imagens_validas']}", f"- Ausentes: {m['imagens_ausentes']}", f"- Formato inválido: {m['imagens_quebradas']}", "", "## Categorias", f"- API oficial: {m['categoria_api']}", f"- Breadcrumb: {m['categoria_breadcrumb']}", f"- Fallback local: {m['categoria_fallback']}", f"- Vazias: {m['categoria_vazia']}", "", "## Preços", f"- Inválidos/ausentes: {m['preco_invalido']}", f"- Zero: {m['preco_zero']}", f"- Negativos: {m['preco_negativo']}", "", "## Produtos e SEO", f"- Item_id duplicado na fonte: {m['item_id_duplicado']}", f"- Item_id ausente: {m['item_id_ausente']}", f"- Permalink inválido: {m['permalink_invalido']}", f"- Páginas de detalhe quebradas: {m['paginas_quebradas']}", f"- Sem título: {m['seo_sem_titulo']}", f"- Sem descrição: {m['seo_sem_descricao']}", f"- Sem categoria pública: {m['seo_sem_categoria']}", "", "## Curadoria", f"- Aprovados automaticamente: {status.get('aprovado_auto', 0)}", f"- Aprovados manualmente: {status.get('aprovado_manual', 0)}", f"- Publicados: {status.get('publicado', 0)}", f"- Pendentes: {status.get('pendente_revisao', 0)}", f"- Rejeitados: {status.get('rejeitado', 0)}", "", "## Recomendação", "- Não houve consulta externa a links afiliados; a auditoria valida formato, unicidade e páginas estáticas sem gerar tráfego adicional."]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
