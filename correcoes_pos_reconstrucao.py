"""Correções seguras pós-reconstrução do Promogg."""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from requests import RequestException

from banco import conectar, inicializar_banco, registrar_evento_sistema, registrar_log
from gerador_link_mercadolivre import link_afiliado_valido
from mercadolivre_api import ErroMercadoLivre, consultar_categoria, consultar_item, item_id_valido


RELATORIO = Path("RELATORIO_CORRECOES_POS_RECONSTRUCAO.md")
STATUS_PUBLICOS = {"aprovado_auto", "aprovado_manual", "publicado"}


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _categoria_util(valor):
    valor = str(valor or "").strip()
    return valor and valor.lower() != "ofertas"


def _carregar_catalogo(caminho):
    path = Path(caminho)
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    ofertas = dados.get("ofertas", []) if isinstance(dados, dict) else []
    retorno = {}
    for oferta in ofertas:
        item_id = str(oferta.get("item_id") or "").strip().upper()
        categoria = str(oferta.get("categoria") or oferta.get("categoria_nome") or "").strip()
        caminho_categoria = str(oferta.get("categoria_caminho") or "").strip()
        if item_id and (_categoria_util(categoria) or _categoria_util(caminho_categoria)):
            retorno[item_id] = {
                "categoria": categoria if _categoria_util(categoria) else caminho_categoria,
                "categoria_caminho": caminho_categoria,
            }
    return retorno


def _metricas_catalogo():
    def resumo(pasta):
        try:
            dados = json.loads((Path(pasta) / "ofertas.json").read_text(encoding="utf-8"))
            ofertas = dados.get("ofertas", [])
        except Exception:
            ofertas = []
        paginas = len(list((Path(pasta) / "produto").glob("*/*/index.html")))
        links_invalidos = sum(1 for o in ofertas if not str(o.get("link") or "").startswith("https://meli.la/"))
        imagens_invalidas = sum(1 for o in ofertas if not str(o.get("imagem_url") or "").startswith(("http://", "https://")))
        precos_invalidos = 0
        for o in ofertas:
            try:
                if float(o.get("preco") or 0) <= 0:
                    precos_invalidos += 1
            except (TypeError, ValueError):
                precos_invalidos += 1
        return {
            "ofertas": len(ofertas), "paginas": paginas, "links_invalidos": links_invalidos,
            "imagens_invalidas": imagens_invalidas, "precos_invalidos": precos_invalidos,
        }
    return {"site": resumo("site"), "dist_site": resumo("dist_site")}


def metricas_pendencias():
    inicializar_banco()
    with conectar() as conn:
        categorias_vazias = conn.execute(
            """
            SELECT COUNT(*) FROM produtos
            WHERE plataforma='mercado_livre'
              AND status NOT IN ('duplicado_oculto')
              AND (
                TRIM(COALESCE(categoria_nome, '')) = ''
                OR TRIM(COALESCE(categoria, '')) = ''
              )
            """
        ).fetchone()[0]
        categorias_genericas = conn.execute(
            """
            SELECT COUNT(*) FROM produtos
            WHERE plataforma='mercado_livre'
              AND status NOT IN ('duplicado_oculto')
              AND lower(TRIM(COALESCE(categoria, ''))) = 'ofertas'
              AND TRIM(COALESCE(categoria_caminho, '')) = ''
            """
        ).fetchone()[0]
        duplicados = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT item_id FROM produtos
                WHERE TRIM(COALESCE(item_id,'')) <> ''
                  AND status != 'duplicado_oculto'
                GROUP BY item_id HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        afiliados_falhos = conn.execute(
            """
            SELECT COUNT(DISTINCT p.id)
            FROM produtos p
            LEFT JOIN logs l ON l.etapa='afiliados'
             AND l.mensagem LIKE '%' || p.item_id || '%'
             AND l.mensagem LIKE '%Falha ao gerar meli.la%'
            WHERE p.plataforma='mercado_livre'
              AND p.status NOT IN ('indisponivel','erro','duplicado_oculto')
              AND TRIM(COALESCE(p.link_original,'')) <> ''
              AND (
                TRIM(COALESCE(p.link_afiliado,'')) = ''
                OR l.id IS NOT NULL
              )
            """
        ).fetchone()[0]
        erros_401 = conn.execute(
            """
            SELECT COUNT(*) FROM logs
            WHERE (mensagem LIKE '%HTTP 401%' OR dados LIKE '%HTTP 401%')
              AND lower(etapa) NOT LIKE '%shopee%'
            """
        ).fetchone()[0]
    return {
        "categorias_vazias": categorias_vazias,
        "categorias_genericas": categorias_genericas,
        "duplicados": duplicados,
        "afiliados_falhos": afiliados_falhos,
        "erros_401_logs": erros_401,
        "catalogo": _metricas_catalogo(),
    }


def _candidatos_categoria():
    with conectar() as conn:
        return [dict(row) for row in conn.execute(
            """
            SELECT * FROM produtos
            WHERE plataforma='mercado_livre'
              AND status != 'duplicado_oculto'
              AND (
                TRIM(COALESCE(categoria_nome, '')) = ''
                OR TRIM(COALESCE(categoria, '')) = ''
                OR (lower(TRIM(COALESCE(categoria, ''))) = 'ofertas'
                    AND TRIM(COALESCE(categoria_caminho, '')) = '')
              )
            ORDER BY id
            """
        ).fetchall()]


def _categoria_de_breadcrumb(produto):
    caminho = str(produto.get("categoria_caminho") or "").strip()
    if _categoria_util(caminho):
        partes = [p.strip() for p in re.split(r"[>/|]", caminho) if p.strip()]
        return partes[-1] if partes else caminho
    for campo in ("categoria_nivel_4", "categoria_nivel_3", "categoria_nivel_2", "categoria_nivel_1"):
        if _categoria_util(produto.get(campo)):
            return str(produto.get(campo)).strip()
    return ""


def _categoria_de_historico(produto):
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT categoria_nome FROM historico_precos
            WHERE produto_id=? AND TRIM(COALESCE(categoria_nome,'')) <> ''
              AND lower(TRIM(categoria_nome)) <> 'ofertas'
            ORDER BY id DESC LIMIT 1
            """,
            (produto["id"],),
        ).fetchone()
    return str(row["categoria_nome"]).strip() if row else ""


def _resolver_categoria(produto, site, dist, usar_api=True):
    item_id = str(produto.get("item_id") or "").strip().upper()
    if usar_api and item_id_valido(item_id):
        try:
            item = consultar_item(item_id)
            if item.get("disponivel") and _categoria_util(item.get("categoria_nome")):
                return item["categoria_nome"], item.get("categoria_id", ""), "api"
            if item.get("categoria_id"):
                categoria = consultar_categoria(item["categoria_id"])
                nome = str(categoria.get("name") or "").strip()
                if _categoria_util(nome):
                    return nome, item["categoria_id"], "api"
        except ErroMercadoLivre as erro:
            registrar_log("categorias", f"API inconclusiva para {item_id}: {erro}", nivel="warning")

    breadcrumb = _categoria_de_breadcrumb(produto)
    if _categoria_util(breadcrumb):
        return breadcrumb, str(produto.get("categoria_id") or ""), "breadcrumb"
    if item_id in site and _categoria_util(site[item_id]["categoria"]):
        return site[item_id]["categoria"], str(produto.get("categoria_id") or ""), "site_restaurado"
    if item_id in dist and _categoria_util(dist[item_id]["categoria"]):
        return dist[item_id]["categoria"], str(produto.get("categoria_id") or ""), "dist_site_restaurado"
    historico = _categoria_de_historico(produto)
    if _categoria_util(historico):
        return historico, str(produto.get("categoria_id") or ""), "historico"
    if not _categoria_util(produto.get("categoria")) and not _categoria_util(produto.get("categoria_nome")):
        return "ofertas", str(produto.get("categoria_id") or ""), "fallback"
    return "", "", ""


def corrigir_categorias_vazias(dry_run=True, limite_api=80):
    inicializar_banco()
    antes = metricas_pendencias()
    site = _carregar_catalogo("site/ofertas.json")
    dist = _carregar_catalogo("dist_site/ofertas.json")
    candidatos = _candidatos_categoria()
    alteracoes = []
    api_usadas = 0
    for produto in candidatos:
        # Dry-run precisa ser puramente local: não consulta API, não força refresh
        # OAuth e não polui logs com falhas de rede transitórias.
        usar_api = (not dry_run) and api_usadas < limite_api
        categoria, categoria_id, origem = _resolver_categoria(produto, site, dist, usar_api=usar_api)
        if origem == "api":
            api_usadas += 1
        if not categoria:
            continue
        if origem == "fallback":
            continue
        atual = str(produto.get("categoria_nome") or produto.get("categoria") or "").strip()
        alteracoes.append({
            "id": produto["id"], "item_id": produto["item_id"], "antes": atual,
            "depois": categoria, "categoria_id": categoria_id, "origem": origem,
        })
    if not dry_run and alteracoes:
        with conectar() as conn:
            for item in alteracoes:
                conn.execute(
                    """
                    UPDATE produtos
                    SET categoria=?,
                        categoria_nome=?,
                        categoria_id=COALESCE(NULLIF(?, ''), categoria_id),
                        origem_categoria=?,
                        atualizado_em=?
                    WHERE id=?
                    """,
                    (item["depois"], item["depois"], item["categoria_id"], item["origem"], agora(), item["id"]),
                )
        registrar_evento_sistema("categorias", "pos_reconstrucao", "sucesso", "Categorias vazias corrigidas", f"total={len(alteracoes)}")
    depois = metricas_pendencias()
    escrever_relatorio({"acao": "corrigir_categorias", "dry_run": dry_run, "antes": antes, "depois": depois, "alteracoes": alteracoes})
    return {"antes": antes, "depois": depois, "alteracoes": alteracoes, "dry_run": dry_run}


def _status_postagem(produto_id):
    with conectar() as conn:
        row = conn.execute(
            "SELECT status FROM postagens WHERE produto_id=? ORDER BY id DESC LIMIT 1",
            (produto_id,),
        ).fetchone()
    return row["status"] if row else ""


def _score_duplicado(produto):
    score = 0
    if link_afiliado_valido(produto.get("link_afiliado")):
        score += 40
    try:
        if float(produto.get("preco_atual") or 0) > 0:
            score += 20
    except (TypeError, ValueError):
        pass
    if str(produto.get("imagem") or "").startswith(("http://", "https://")):
        score += 15
    if _status_postagem(produto["id"]) in STATUS_PUBLICOS:
        score += 15
    if produto.get("atualizado_em"):
        score += 5
    with conectar() as conn:
        historico = conn.execute("SELECT COUNT(*) FROM historico_precos WHERE produto_id=?", (produto["id"],)).fetchone()[0]
    score += min(10, historico)
    return score, historico


def auditar_duplicados():
    inicializar_banco()
    grupos = []
    with conectar() as conn:
        item_ids = [row["item_id"] for row in conn.execute(
            """
            SELECT item_id FROM produtos
            WHERE TRIM(COALESCE(item_id,'')) <> '' AND status != 'duplicado_oculto'
            GROUP BY item_id HAVING COUNT(*) > 1 ORDER BY item_id
            """
        ).fetchall()]
        for item_id in item_ids:
            produtos = [dict(row) for row in conn.execute(
                "SELECT * FROM produtos WHERE item_id=? AND status != 'duplicado_oculto' ORDER BY id",
                (item_id,),
            ).fetchall()]
            detalhes = []
            for produto in produtos:
                score, historico = _score_duplicado(produto)
                detalhes.append({**produto, "score_integridade": score, "historico_total": historico, "status_postagem": _status_postagem(produto["id"])})
            escolhido = max(detalhes, key=lambda p: (p["score_integridade"], str(p.get("atualizado_em") or ""), p["id"])) if detalhes else None
            grupos.append({"item_id": item_id, "produtos": detalhes, "escolhido": escolhido})
    escrever_relatorio({"acao": "auditar_duplicados", "dry_run": True, "antes": metricas_pendencias(), "depois": metricas_pendencias(), "duplicados": grupos})
    return {"total": len(grupos), "grupos": grupos}


def corrigir_duplicados(dry_run=True):
    antes = metricas_pendencias()
    auditoria = auditar_duplicados()
    ocultar = []
    for grupo in auditoria["grupos"]:
        escolhido_id = grupo["escolhido"]["id"] if grupo["escolhido"] else None
        for produto in grupo["produtos"]:
            if produto["id"] != escolhido_id:
                ocultar.append({"id": produto["id"], "item_id": produto["item_id"], "titulo": produto["titulo"], "escolhido_id": escolhido_id})
    if not dry_run and ocultar:
        with conectar() as conn:
            for item in ocultar:
                conn.execute(
                    "UPDATE produtos SET status='duplicado_oculto', atualizado_em=? WHERE id=?",
                    (agora(), item["id"]),
                )
        registrar_evento_sistema("duplicados", "pos_reconstrucao", "sucesso", "Duplicados ocultados", f"total={len(ocultar)}")
    depois = metricas_pendencias()
    escrever_relatorio({"acao": "corrigir_duplicados", "dry_run": dry_run, "antes": antes, "depois": depois, "ocultar": ocultar})
    return {"antes": antes, "depois": depois, "ocultar": ocultar, "dry_run": dry_run}


def afiliados_falhos():
    inicializar_banco()
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT p.id, p.item_id, p.titulo, p.link_original
            FROM produtos p
            LEFT JOIN logs l ON l.etapa='afiliados'
             AND l.mensagem LIKE '%' || p.item_id || '%'
             AND l.mensagem LIKE '%Falha ao gerar meli.la%'
            WHERE p.plataforma='mercado_livre'
              AND p.status NOT IN ('indisponivel','erro','duplicado_oculto')
              AND TRIM(COALESCE(p.link_original,'')) <> ''
              AND (
                TRIM(COALESCE(p.link_afiliado,'')) = ''
                OR l.id IS NOT NULL
              )
            ORDER BY p.id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def reprocessar_afiliados_falhos(dry_run=True, limite=None):
    antes = metricas_pendencias()
    pendentes = afiliados_falhos()
    if limite:
        pendentes = pendentes[: int(limite)]
    resultado = {"pendentes": len(pendentes), "gerados": 0, "falhas": 0, "itens": []}
    if not dry_run and pendentes:
        from gerador_afiliados_oficial import gerar_links_afiliados_para

        resultado = gerar_links_afiliados_para(pendentes)
    depois = metricas_pendencias()
    escrever_relatorio({"acao": "reprocessar_afiliados_falhos", "dry_run": dry_run, "antes": antes, "depois": depois, "resultado": resultado, "pendentes": pendentes[:50]})
    return {"antes": antes, "depois": depois, "resultado": resultado, "pendentes": pendentes, "dry_run": dry_run}


def meli_auditar_api():
    from meli_oauth import ErroOAuthMercadoLivre, status_oauth_local, testar_token

    resultado = {"oauth_local": status_oauth_local(), "users_me": {}, "item": {}, "categoria": {}, "refresh_automatico": "não necessário"}
    try:
        resultado["users_me"] = {"ok": True, **testar_token()}
    except ErroOAuthMercadoLivre as erro:
        resultado["users_me"] = {"ok": False, "erro": str(erro).splitlines()[0][:220]}
    except RequestException as erro:
        resultado["users_me"] = {"ok": False, "erro": f"falha de rede: {str(erro).splitlines()[0][:200]}"}
    item_id = ""
    with conectar() as conn:
        row = conn.execute("SELECT item_id FROM produtos WHERE item_id LIKE 'MLB%' ORDER BY id LIMIT 1").fetchone()
        item_id = row["item_id"] if row else ""
    try:
        item = consultar_item(item_id)
        resultado["item"] = {"ok": True, "item_id": item_id, "disponivel": item.get("disponivel"), "categoria_id": item.get("categoria_id", "")}
        categoria_id = item.get("categoria_id") or ""
        if categoria_id:
            categoria = consultar_categoria(categoria_id)
            resultado["categoria"] = {"ok": bool(categoria), "categoria_id": categoria_id, "nome": categoria.get("name", "") if categoria else ""}
    except ErroMercadoLivre as erro:
        resultado["item"] = {"ok": False, "item_id": item_id, "erro": str(erro)[:220]}
        if "401" in str(erro):
            resultado["refresh_automatico"] = "tentado; falhou ou token inválido"
    escrever_relatorio({"acao": "meli_auditar_api", "dry_run": True, "antes": metricas_pendencias(), "depois": metricas_pendencias(), "meli": resultado})
    return resultado


def escrever_relatorio(contexto=None):
    contexto = contexto or {}
    atual = metricas_pendencias()
    linhas = [
        "# Relatório de Correções Pós-Reconstrução",
        "",
        f"- Atualizado em: {agora()}",
        "- Nenhum deploy, Telegram real, ONLINE, coleta agressiva, exclusão de histórico ou limpeza de perfil foi executado.",
        "",
        "## Métricas atuais",
        f"- 401 registrados em logs: {atual['erros_401_logs']}",
        f"- Categorias vazias: {atual['categorias_vazias']}",
        f"- Categorias genéricas `ofertas` sem breadcrumb: {atual['categorias_genericas']}",
        f"- Grupos de item_id duplicados ativos: {atual['duplicados']}",
        f"- Afiliados falhos/pendentes: {atual['afiliados_falhos']}",
        f"- Catálogo site/: {atual['catalogo']['site']['ofertas']} ofertas, {atual['catalogo']['site']['paginas']} páginas, links inválidos={atual['catalogo']['site']['links_invalidos']}, imagens inválidas={atual['catalogo']['site']['imagens_invalidas']}, preços inválidos={atual['catalogo']['site']['precos_invalidos']}",
        f"- Catálogo dist_site/: {atual['catalogo']['dist_site']['ofertas']} ofertas, {atual['catalogo']['dist_site']['paginas']} páginas",
        "",
        "## Última ação",
        f"- Ação: {contexto.get('acao', 'relatorio')}",
        f"- Dry-run: {contexto.get('dry_run', False)}",
    ]
    antes = contexto.get("antes") or {}
    depois = contexto.get("depois") or {}
    if antes and depois:
        linhas += [
            "",
            "## Antes/depois da última ação",
            f"- 401: {antes.get('erros_401_logs')} -> {depois.get('erros_401_logs')}",
            f"- Categorias vazias: {antes.get('categorias_vazias')} -> {depois.get('categorias_vazias')}",
            f"- Categorias genéricas: {antes.get('categorias_genericas')} -> {depois.get('categorias_genericas')}",
            f"- Duplicados: {antes.get('duplicados')} -> {depois.get('duplicados')}",
            f"- Afiliados falhos: {antes.get('afiliados_falhos')} -> {depois.get('afiliados_falhos')}",
        ]
    if contexto.get("meli"):
        meli = contexto["meli"]
        linhas += [
            "",
            "## Auditoria Mercado Livre API",
            f"- OAuth local configurado: {'sim' if meli.get('oauth_local') else 'não'}",
            f"- `/users/me`: {'ok' if meli.get('users_me', {}).get('ok') else 'falhou'}",
            f"- Item: {'ok' if meli.get('item', {}).get('ok') else 'falhou'}",
            f"- Categoria: {'ok' if meli.get('categoria', {}).get('ok') else 'não testada/falhou'}",
            f"- Refresh automático: {meli.get('refresh_automatico')}",
        ]
    if contexto.get("alteracoes"):
        linhas += ["", "## Categorias propostas/aplicadas"]
        for item in contexto["alteracoes"][:50]:
            linhas.append(f"- {item['item_id']}: `{item['antes'] or '-'}` -> `{item['depois']}` ({item['origem']})")
    if contexto.get("ocultar"):
        linhas += ["", "## Duplicados para ocultar/aplicados"]
        for item in contexto["ocultar"][:50]:
            linhas.append(f"- {item['item_id']}: produto_id={item['id']} oculto; escolhido={item['escolhido_id']}")
    if contexto.get("resultado"):
        res = contexto["resultado"]
        linhas += ["", "## Afiliados falhos"]
        linhas.append(f"- Pendentes analisados: {res.get('pendentes', 0)}")
        linhas.append(f"- Gerados: {res.get('gerados', 0)}")
        linhas.append(f"- Falhas: {res.get('falhas', 0)}")
    linhas += [
        "",
        "## Arquivos alterados",
        "- `mercadolivre_api.py`",
        "- `meli_oauth.py`",
        "- `correcoes_pos_reconstrucao.py`",
        "- `gerador_afiliados_oficial.py`",
        "- `gerar_site.py`",
        "- `ia_promocoes.py`",
        "- filtros auxiliares que ocultam `duplicado_oculto`",
        "",
        "## Comandos criados",
        "- `python3 ia_promocoes.py meli-auditar-api`",
        "- `python3 ia_promocoes.py corrigir-categorias-vazias --dry-run`",
        "- `python3 ia_promocoes.py corrigir-categorias-vazias`",
        "- `python3 ia_promocoes.py auditar-duplicados`",
        "- `python3 ia_promocoes.py corrigir-duplicados --dry-run`",
        "- `python3 ia_promocoes.py corrigir-duplicados`",
        "- `python3 ia_promocoes.py reprocessar-afiliados-falhos --dry-run`",
        "- `python3 ia_promocoes.py reprocessar-afiliados-falhos`",
        "",
        "## Status",
        "- Seguro para commit: depende da validação final e revisão do worktree, que contém alterações pré-existentes.",
        "- Seguro para deploy: somente se `validar --somente-leitura`, qualidade do catálogo e estado MANUTENCAO/ONLINE planejado estiverem corretos.",
    ]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return RELATORIO
