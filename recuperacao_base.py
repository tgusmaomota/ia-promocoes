"""Auditoria e reconstrução controlada da base ativa do Promogg."""

import os
from datetime import datetime
from pathlib import Path

from banco import conectar, inicializar_banco, registrar_evento_sistema, registrar_log


RELATORIO = Path("RELATORIO_RECUPERACAO_BASE.md")


def auditar_base():
    inicializar_banco()
    with conectar() as conn:
        dados = {
            "produtos_total": conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0],
            "ativos": conn.execute("SELECT COUNT(*) FROM produtos WHERE status NOT IN ('indisponivel', 'erro')").fetchone()[0],
            "indisponiveis": conn.execute("SELECT COUNT(*) FROM produtos WHERE status = 'indisponivel'").fetchone()[0],
            "pendentes": conn.execute("SELECT COUNT(*) FROM postagens WHERE status = 'pendente_revisao'").fetchone()[0],
            "aprovados": conn.execute("SELECT COUNT(*) FROM postagens WHERE status IN ('aprovado_auto', 'aprovado_manual')").fetchone()[0],
            "publicados": conn.execute("SELECT COUNT(*) FROM postagens WHERE status = 'publicado'").fetchone()[0],
            "historico": conn.execute("SELECT COUNT(*) FROM historico_precos").fetchone()[0],
            "cliques": conn.execute("SELECT COUNT(*) FROM cliques").fetchone()[0],
            "com_link_afiliado": conn.execute("SELECT COUNT(*) FROM produtos WHERE TRIM(COALESCE(link_afiliado, '')) <> ''").fetchone()[0],
        }
    return dados


def imprimir_auditoria_base():
    dados = auditar_base()
    print("Auditoria da base Promogg")
    for chave, valor in dados.items():
        print(f"- {chave.replace('_', ' ')}: {valor}")
    return dados


def _contagem_site():
    ofertas = 0
    paginas = 0
    try:
        import json
        dados = json.loads(Path("site/ofertas.json").read_text(encoding="utf-8"))
        ofertas = len(dados.get("ofertas", []))
    except (OSError, ValueError, AttributeError):
        pass
    if Path("site/produto").exists():
        paginas = len(list(Path("site/produto").glob("*/index.html")))
    return ofertas, paginas


def gerar_relatorio_recuperacao(resultado):
    antes = resultado.get("antes", {})
    depois = resultado.get("depois", {})
    linhas = [
        "# Relatório de Recuperação da Base - Promogg",
        "",
        f"- Data/hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Resultado: {resultado.get('resultado', 'incompleto')}",
        "",
        "## Causa raiz",
        resultado.get("causa_raiz", "Não informada."),
        "",
        "## Correções aplicadas",
    ]
    linhas += [f"- {item}" for item in resultado.get("correcoes", [])] or ["- Nenhuma alteração aplicada."]
    linhas += [
        "",
        "## Base antes/depois",
        f"- Produtos: {antes.get('produtos_total', 0)} -> {depois.get('produtos_total', 0)}",
        f"- Ativos: {antes.get('ativos', 0)} -> {depois.get('ativos', 0)}",
        f"- Indisponíveis preservados no histórico: {antes.get('indisponiveis', 0)} -> {depois.get('indisponiveis', 0)}",
        f"- Novas ofertas coletadas: {resultado.get('novos', 0)}",
        f"- Ofertas recuperadas/atualizadas: {resultado.get('atualizados', 0)}",
        f"- Indisponíveis removidos do catálogo ativo: {resultado.get('indisponiveis_catalogo', 0)}",
        f"- Ofertas públicas: {resultado.get('ofertas_site', 0)}",
        f"- Páginas de produto: {resultado.get('paginas_produto', 0)}",
        f"- Meta mínima (30/30): {'atingida' if resultado.get('homologado') else 'não atingida'}",
        "",
        "## Situação final",
        resultado.get("situacao_final", ""),
    ]
    if resultado.get("erro"):
        linhas += ["", "## Bloqueio", f"- {resultado['erro']}"]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return RELATORIO


def reconstruir_base():
    """Coleta uma nova base sem apagar produtos, histórico, cliques ou postagens."""
    from coletor_mercadolivre import coletar
    from fila_postagens import gerar_fila_de_produtos
    from gerador_afiliados_oficial import gerar_links_afiliados
    from gerar_site import gerar_site, validar_site_publico
    from monitor_precos import monitorar_precos_diariamente

    antes = auditar_base()
    resultado = {
        "resultado": "incompleto",
        "causa_raiz": "Base ativa reduzida por itens indisponíveis e coleta Playwright bloqueada.",
        "correcoes": [
            "Produtos indisponíveis foram preservados no SQLite e continuam excluídos do catálogo ativo.",
            "Coleta manual usa API/item_id quando disponível e Playwright com perfil reserva como fallback.",
        ],
        "antes": antes,
        "indisponiveis_catalogo": antes["indisponiveis"],
    }
    try:
        modo_confiavel = os.getenv("COLETA_MODO_CONFIAVEL", "").strip().lower() in {"1", "true", "sim", "yes"}
        if modo_confiavel:
            from coleta_confiavel import coletar_confiavel

            coleta = coletar_confiavel()
            produtos = [{"item_id": "coleta_confiavel"}] * coleta["salvos"]
        else:
            produtos = coletar()
        if not produtos:
            raise RuntimeError("A coleta não retornou ofertas novas.")
        afiliados = {"gerados": 0, "falhas": 0} if modo_confiavel else gerar_links_afiliados()
        fila = {"aprovados": 0, "rejeitados": 0} if modo_confiavel else gerar_fila_de_produtos()
        monitoramento = monitorar_precos_diariamente(forcar=True)
        site = gerar_site()
        erros_site = validar_site_publico()
        depois = auditar_base()
        ofertas, paginas = _contagem_site()
        homologado = (
            not erros_site
            and depois["aprovados"] >= 30
            and ofertas >= 30
            and paginas >= 30
        )
        resultado.update({
            "resultado": "homologado" if homologado else "meta não atingida",
            "novos": max(0, depois["produtos_total"] - antes["produtos_total"]),
            "atualizados": max(0, len(produtos) - max(0, depois["produtos_total"] - antes["produtos_total"])),
            "fila": fila,
            "afiliados": afiliados,
            "monitoramento": monitoramento,
            "depois": depois,
            "ofertas_site": ofertas,
            "paginas_produto": paginas,
            "homologado": homologado,
            "situacao_final": "Base renovada e validada." if homologado else "Coleta concluída, mas a meta mínima de 30 ofertas/páginas não foi atingida.",
        })
        registrar_evento_sistema("reconstrucao_base", "operacao", "sucesso" if homologado else "aviso", resultado["situacao_final"])
    except Exception as erro:
        resultado.update({
            "erro": str(erro),
            "depois": auditar_base(),
            "ofertas_site": _contagem_site()[0],
            "paginas_produto": _contagem_site()[1],
            "homologado": False,
            "situacao_final": "Reconstrução interrompida sem apagar dados existentes.",
        })
        registrar_log("reconstrucao_base", f"Reconstrução interrompida: {erro}", nivel="error")
        registrar_evento_sistema("reconstrucao_base", "operacao", "erro", "Reconstrução interrompida", str(erro))
    gerar_relatorio_recuperacao(resultado)
    return resultado
