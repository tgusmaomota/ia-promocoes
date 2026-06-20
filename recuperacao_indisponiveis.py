"""Audita e recupera indisponibilidades técnicas sem publicar ofertas."""

import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from banco import conectar, inicializar_banco, registrar_evento_sistema, registrar_log
from gerador_link_mercadolivre import link_afiliado_valido
from mercadolivre_api import item_id_valido
from operacao_sistema import criar_backup_emergencia


RELATORIO = Path("RELATORIO_RECUPERACAO_INDISPONIVEIS.md")


def _linhas():
    inicializar_banco()
    with conectar() as conn:
        return [dict(row) for row in conn.execute(
            """
            SELECT p.*, EXISTS(
                SELECT 1 FROM postagens x WHERE x.produto_id=p.id
                AND x.status IN ('aprovado_auto','aprovado_manual','publicado')
            ) AS possui_aprovacao
            FROM produtos p WHERE p.status='indisponivel' AND p.plataforma='mercado_livre'
            ORDER BY p.id
            """
        ).fetchall()]


def _classificar(produto):
    motivo = str(produto.get("motivo_indisponivel") or "").lower()
    item_id = str(produto.get("item_id") or "")
    if not item_id_valido(item_id):
        return "manter_item_id_invalido", "item_id inválido"
    if any(texto in motivo for texto in ("404", "não encontrado", "not found", "paused", "closed", "finalizado")):
        return "manter_indisponivel_confirmado", "motivo confiável de indisponibilidade"
    completo = (
        link_afiliado_valido(produto.get("link_afiliado"))
        and float(produto.get("preco_atual") or 0) > 0
        and bool(str(produto.get("imagem") or "").strip())
    )
    if completo and produto.get("possui_aprovacao"):
        return "recuperar_seguro", "postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado"
    return "manter_sem_evidencia", "sem evidência suficiente para recuperação"


def auditar_indisponiveis():
    itens = []
    for produto in _linhas():
        classe, motivo = _classificar(produto)
        itens.append({"produto": produto, "classe": classe, "motivo": motivo})
    totais = Counter(item["classe"] for item in itens)
    resultado = {"itens": itens, "totais": totais}
    _relatorio(resultado, dry_run=True, backup="")
    return resultado


def recuperar_indisponiveis(dry_run=False):
    resultado = auditar_indisponiveis()
    backup = "" if dry_run else str(criar_backup_emergencia())
    recuperados = 0
    for item in resultado["itens"]:
        if item["classe"] != "recuperar_seguro":
            continue
        produto = item["produto"]
        if not dry_run:
            with conectar() as conn:
                conn.execute(
                    """UPDATE produtos SET status='coletado', status_verificacao='recuperado_tecnico',
                       motivo_indisponivel='', atualizado_em=? WHERE id=?""",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), produto["id"]),
                )
            registrar_log("recuperacao_indisponiveis", f"Produto recuperado de indisponibilidade técnica: {produto['item_id']}", dados=item["motivo"])
        recuperados += 1
    resultado["recuperados"] = recuperados
    resultado["backup"] = backup
    _relatorio(resultado, dry_run=dry_run, backup=backup)
    registrar_evento_sistema(
        "recuperacao_indisponiveis", "operacao", "sucesso" if not dry_run else "aviso",
        "Auditoria/recuperação de indisponíveis concluída", f"recuperados={recuperados} dry_run={dry_run}",
    )
    return resultado


def _relatorio(resultado, dry_run, backup):
    totais = resultado["totais"]
    linhas = [
        "# Relatório de Recuperação de Indisponíveis", "",
        f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Modo: {'dry-run' if dry_run else 'execução real'}",
        f"- Backup: {backup or 'não aplicável'}",
        f"- Total indisponíveis: {len(resultado['itens'])}",
        f"- Recuperáveis com segurança: {totais['recuperar_seguro']}",
        f"- Mantidos por item_id inválido: {totais['manter_item_id_invalido']}",
        f"- Mantidos por 404/finalização: {totais['manter_indisponivel_confirmado']}",
        f"- Mantidos sem evidência: {totais['manter_sem_evidencia']}",
        f"- Recuperados nesta execução: {resultado.get('recuperados', 0)}", "",
        "## Causa raiz", "",
        "- Falhas HTTP 403 são inconclusivas e não representam indisponibilidade. O monitoramento foi ajustado para registrar erro_api/verificacao_inconclusiva e preservar o status anterior.",
        "- Registros antigos sem motivo confiável só são recuperados quando possuem postagem aprovada, link meli.la, preço e imagem.", "",
        "## Exemplos",
    ]
    for item in resultado["itens"][:20]:
        linhas.append(f"- {item['classe']} | {item['produto']['item_id']} | {item['motivo']}")
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
