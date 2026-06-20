"""Reaplica a curadoria automática somente às ofertas pendentes elegíveis."""

import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from analisador_promocao import LIMITE_REVISAO, analisar_produto
from banco import conectar, inicializar_banco, registrar_log, salvar_promocao
from gerador_link_mercadolivre import link_afiliado_valido
from operacao_sistema import criar_backup_emergencia


RELATORIO = Path("RELATORIO_REPROCESSAMENTO_PENDENTES.md")
TITULO_COM_PRECO = re.compile(r"(?i)(?:R\$\s*\d|\d+\s*%\s*OFF)")


def _pendentes_elegiveis():
    inicializar_banco()
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT postagens.*, produtos.preco_atual, produtos.preco_original,
                   produtos.desconto_percentual, produtos.economia_valor,
                   produtos.status AS status_produto, produtos.item_id, produtos.imagem,
                   produtos.categoria_id, produtos.categoria_nome, produtos.menor_preco,
                   produtos.variacao_preco, produtos.vezes_verificado,
                   produtos.categoria_caminho, produtos.selo_mais_vendido,
                   produtos.selo_loja_oficial, produtos.avaliacao, produtos.quantidade_vendida,
                   produtos.melhor_preco
            FROM postagens
            JOIN produtos ON produtos.id = postagens.produto_id
            WHERE postagens.status = 'pendente_revisao'
              AND postagens.plataforma = 'mercado_livre'
              AND produtos.plataforma = 'mercado_livre'
              AND produtos.status NOT IN ('indisponivel', 'erro')
              AND produtos.preco_atual > 0
              AND postagens.link_afiliado LIKE 'https://meli.la/%'
            ORDER BY postagens.id
            """
        ).fetchall()
    return [dict(row) for row in rows if not TITULO_COM_PRECO.search(str(row["titulo"] or "")) and link_afiliado_valido(row["link_afiliado"])]


def _decisao(oferta):
    produto = dict(oferta)
    produto["preco_atual"] = oferta["preco_atual"] or oferta["preco"]
    produto["preco_original"] = oferta.get("preco_original")
    produto["desconto"] = oferta.get("desconto_percentual") or 0
    analise = analisar_produto(produto)
    if analise["aprovado"]:
        return "aprovado_auto", analise
    if (
        float(produto.get("preco_atual") or 0) <= 0
        or not link_afiliado_valido(oferta["link_afiliado"])
        or float(analise["score"]) < LIMITE_REVISAO
    ):
        return "rejeitado", analise
    return "pendente_revisao", analise


def _gerar_relatorio(resultado):
    motivos = Counter(item["motivo"] for item in resultado["itens"])
    linhas = [
        "# Relatório de Reprocessamento de Pendentes", "",
        f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Modo: {'simulação' if resultado['dry_run'] else 'execução real'}",
        f"- Backup: {resultado.get('backup') or 'não aplicável'}",
        f"- Total analisado: {resultado['total']}",
        f"- Aprovados automaticamente: {resultado['aprovados_auto']}",
        f"- Mantidos pendentes: {resultado['pendentes']}",
        f"- Rejeitados: {resultado['rejeitados']}",
        f"- Impacto esperado no site: até {resultado['aprovados_auto']} oferta(s) adicional(is), sujeitas ao filtro público.",
        "", "## Motivos principais",
    ]
    linhas += [f"- {motivo}: {total}" for motivo, total in motivos.most_common(10)] or ["- nenhum"]
    linhas += ["", "## Exemplos"]
    for item in resultado["itens"][:10]:
        linhas.append(f"- #{item['postagem_id']}: {item['antes']} -> {item['depois']} | score={item['score']:.1f} | {item['motivo']}")
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def reprocessar_pendentes(dry_run=False, backup_existente=None):
    ofertas = _pendentes_elegiveis()
    resultado = {
        "dry_run": dry_run, "total": len(ofertas), "aprovados_auto": 0,
        "pendentes": 0, "rejeitados": 0, "itens": [], "backup": "",
    }
    if not dry_run:
        resultado["backup"] = str(backup_existente or criar_backup_emergencia())

    for oferta in ofertas:
        depois, analise = _decisao(oferta)
        resultado[{"aprovado_auto": "aprovados_auto", "pendente_revisao": "pendentes", "rejeitado": "rejeitados"}[depois]] += 1
        resultado["itens"].append({
            "postagem_id": oferta["id"], "antes": oferta["status"], "depois": depois,
            "score": float(analise["score"]), "motivo": analise["motivo"], "titulo": oferta["titulo"],
        })
        if dry_run:
            continue
        promocao_id = salvar_promocao(
            oferta["produto_id"], analise["desconto"], analise["score"], depois,
            f"Reprocessamento após saneamento de título: {analise['motivo']}",
        )
        with conectar() as conn:
            conn.execute(
                """
                UPDATE postagens
                SET status=?, motivo=?, promocao_id=?, aprovado_por=?,
                    aprovado_em=CASE WHEN ?='aprovado_auto' THEN ? ELSE aprovado_em END,
                    atualizado_em=?
                WHERE id=?
                """,
                (depois, analise["motivo"], promocao_id,
                 "curadoria_reprocessada" if depois == "aprovado_auto" else "",
                 depois, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), oferta["id"]),
            )
        registrar_log("reprocessar_pendentes", f"Postagem={oferta['id']} {oferta['status']}->{depois}", dados=analise["motivo"])

    _gerar_relatorio(resultado)
    return resultado
