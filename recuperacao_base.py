"""Reconstrução conservadora da base ativa, com proteção do catálogo público."""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from banco import DB_PATH, conectar, inicializar_banco, registrar_evento_sistema, registrar_log, semear_historico_existente
from catalogo_integridade import avaliar_catalogo, carregar_referencia_aprovada, resumo_catalogo


RELATORIO = Path("RELATORIO_RECUPERACAO_BASE.md")
BACKUPS_DIR = Path("backups") / "reconstrucao_base"
ARTEFATOS_CATALOGO = (Path("site"), Path("dist_site"))
ARQUIVOS_AUXILIARES = (Path("posts_prontos.csv"), Path("whatsapp_posts.txt"))


def auditar_base():
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


def _contagem_site(diretorio=Path("site")):
    resumo = resumo_catalogo(diretorio)
    return resumo["ofertas"], resumo["paginas"]


def criar_backup_reconstrucao():
    """Cria cópia consistente do banco e do catálogo antes de qualquer mutação."""
    destino = BACKUPS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    destino.mkdir(parents=True, exist_ok=False)

    banco_destino = destino / "banco.db"
    origem = sqlite3.connect(DB_PATH)
    try:
        copia = sqlite3.connect(banco_destino)
        try:
            origem.backup(copia)
        finally:
            copia.close()
    finally:
        origem.close()

    for origem_artefato in ARTEFATOS_CATALOGO:
        if origem_artefato.exists():
            shutil.copytree(origem_artefato, destino / origem_artefato.name)
    for origem_arquivo in ARQUIVOS_AUXILIARES:
        if origem_arquivo.is_file():
            shutil.copy2(origem_arquivo, destino / origem_arquivo.name)
    return destino


def restaurar_catalogo(backup):
    """Restaura somente os artefatos públicos, mantendo novos dados históricos."""
    backup = Path(backup)
    restaurados = []
    for artefato in ARTEFATOS_CATALOGO:
        origem = backup / artefato.name
        if not origem.exists():
            continue
        if artefato.exists():
            shutil.rmtree(artefato)
        shutil.copytree(origem, artefato)
        restaurados.append(str(artefato))
    return restaurados


def gerar_relatorio_recuperacao(resultado):
    antes = resultado.get("antes", {})
    depois = resultado.get("depois", {})
    integridade = resultado.get("integridade", {})
    linhas = [
        "# Relatório de Recuperação da Base - Promogg", "",
        f"- Data/hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Resultado: {resultado.get('resultado', 'incompleto')}",
        f"- Modo: {'simulação' if resultado.get('dry_run') else 'execução'}",
        f"- Backup: {resultado.get('backup') or 'não criado (simulação)'}", "",
        "## Proteções aplicadas",
        "- A fila global de postagens não é executada durante a reconstrução.",
        "- O monitoramento completo não é forçado durante a reconstrução.",
        "- Falhas transitórias de API preservam o status anterior.",
        "- O catálogo novo precisa respeitar mínimo, páginas, links e queda máxima.", "",
        "## Base antes/depois",
        f"- Produtos: {antes.get('produtos_total', 0)} -> {depois.get('produtos_total', 0)}",
        f"- Histórico de preços: {antes.get('historico', 0)} -> {depois.get('historico', 0)}",
        f"- Novas ofertas coletadas: {resultado.get('novos', 0)}",
        f"- Itens atualizados: {resultado.get('atualizados', 0)}",
        f"- Linhas-base de histórico criadas: {resultado.get('historico_semeado', 0)}",
        f"- Fila global executada: não", "",
        "## Catálogo",
        f"- Referência: {integridade.get('referencia', {}).get('ofertas', 0)} ofertas",
        f"- Candidato: {integridade.get('atual', {}).get('ofertas', resultado.get('ofertas_site', 0))} ofertas",
        f"- Páginas candidatas: {integridade.get('atual', {}).get('paginas', resultado.get('paginas_produto', 0))}",
        f"- Queda: {integridade.get('queda_percentual', 0):.2f}%",
        f"- Bloqueios: {'; '.join(integridade.get('erros', [])) or 'nenhum'}", "",
        "## Situação final",
        resultado.get("situacao_final", ""),
    ]
    if resultado.get("erro"):
        linhas += ["", "## Erro", f"- {resultado['erro']}"]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return RELATORIO


def reconstruir_base(dry_run=False):
    """Atualiza a base sem permitir que uma coleta degradada substitua o catálogo."""
    antes = auditar_base()
    referencia_local = resumo_catalogo(Path("site"))
    referencia_aprovada = carregar_referencia_aprovada()
    referencia = referencia_local if referencia_local["ofertas"] >= referencia_aprovada.get("ofertas", 0) else referencia_aprovada
    resultado = {
        "resultado": "simulação" if dry_run else "incompleto",
        "dry_run": dry_run,
        "antes": antes,
        "depois": antes,
        "ofertas_site": referencia_local["ofertas"],
        "paginas_produto": referencia_local["paginas"],
        "integridade": avaliar_catalogo(Path("site"), referencia=referencia),
        "situacao_final": "Nenhuma coleta, curadoria, monitoramento ou arquivo público foi alterado." if dry_run else "",
    }
    if dry_run:
        gerar_relatorio_recuperacao(resultado)
        return resultado

    if not Path(DB_PATH).is_file():
        resultado.update({"resultado": "bloqueado", "erro": "banco.db não encontrado", "situacao_final": "Reconstrução não iniciada."})
        gerar_relatorio_recuperacao(resultado)
        return resultado
    backup = criar_backup_reconstrucao()
    resultado["backup"] = str(backup)
    try:
        inicializar_banco()
        from coletor_mercadolivre import coletar
        from gerador_afiliados_oficial import gerar_links_afiliados
        from gerar_site import gerar_site, validar_site_publico

        modo_confiavel = os.getenv("COLETA_MODO_CONFIAVEL", "").strip().lower() in {"1", "true", "sim", "yes"}
        if modo_confiavel:
            from coleta_confiavel import coletar_confiavel
            coleta = coletar_confiavel()
            produtos = [{"item_id": "coleta_confiavel"}] * int(coleta.get("salvos", 0))
        else:
            produtos = coletar()
        if not produtos:
            raise RuntimeError("A coleta não retornou ofertas; catálogo anterior foi preservado.")

        afiliados = {"gerados": 0, "falhas": 0} if modo_confiavel else gerar_links_afiliados()
        historico_semeado = semear_historico_existente()

        # Não executar gerar_fila_de_produtos nem monitorar_precos aqui. Ambos
        # percorrem a base inteira e não fazem parte de uma reconstrução segura.
        gerar_site()
        erros_site = validar_site_publico(escrever_relatorio=False)
        integridade = avaliar_catalogo(Path("site"), referencia=referencia)
        resultado.update({
            "novos": max(0, auditar_base()["produtos_total"] - antes["produtos_total"]),
            "atualizados": max(0, len(produtos) - max(0, auditar_base()["produtos_total"] - antes["produtos_total"])),
            "afiliados": afiliados,
            "historico_semeado": historico_semeado,
            "integridade": integridade,
        })
        if erros_site or not integridade["aprovado"]:
            restaurados = restaurar_catalogo(backup)
            resultado.update({
                "resultado": "bloqueado e restaurado",
                "erro": "; ".join((erros_site + integridade["erros"])[:8]),
                "restaurados": restaurados,
                "situacao_final": "O catálogo candidato não passou na proteção; site e dist_site anteriores foram restaurados. Nenhum deploy foi executado.",
            })
            registrar_evento_sistema("reconstrucao_base", "operacao", "alerta", "Reconstrução bloqueada; catálogo anterior restaurado", resultado["erro"])
        else:
            atual = integridade["atual"]
            resultado.update({
                "resultado": "homologado localmente",
                "homologado": True,
                "ofertas_site": atual["ofertas"],
                "paginas_produto": atual["paginas"],
                "situacao_final": "Base atualizada e catálogo local preservado/validado. Deploy permanece uma ação manual.",
            })
            registrar_evento_sistema("reconstrucao_base", "operacao", "sucesso", "Reconstrução local homologada", f"ofertas={atual['ofertas']}")
        resultado["depois"] = auditar_base()
        resultado["ofertas_site"], resultado["paginas_produto"] = _contagem_site()
    except Exception as erro:
        restaurados = restaurar_catalogo(backup)
        resultado.update({
            "resultado": "interrompido e restaurado",
            "erro": str(erro),
            "restaurados": restaurados,
            "depois": auditar_base(),
            "ofertas_site": _contagem_site()[0],
            "paginas_produto": _contagem_site()[1],
            "situacao_final": "Reconstrução interrompida; catálogo anterior foi restaurado e nenhum deploy foi executado.",
        })
        registrar_log("reconstrucao_base", f"Reconstrução interrompida: {erro}", nivel="error")
        registrar_evento_sistema("reconstrucao_base", "operacao", "erro", "Reconstrução interrompida", str(erro))
    gerar_relatorio_recuperacao(resultado)
    return resultado
