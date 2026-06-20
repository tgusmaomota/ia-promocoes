"""Reprocessa somente pendentes usando sinais públicos enriquecidos."""

from collections import Counter
from datetime import datetime
from pathlib import Path

from analisador_promocao import LIMITE_REVISAO, analisar_produto
from banco import conectar, registrar_log, salvar_promocao
from operacao_sistema import criar_backup_emergencia
from reprocessar_pendentes import _pendentes_elegiveis


RELATORIO = Path("RELATORIO_ENRIQUECIMENTO_OFERTAS.md")


def reprocessar_pendentes_enriquecido(dry_run=False):
    ofertas = _pendentes_elegiveis()
    resultado = {"total": len(ofertas), "aprovados": 0, "pendentes": 0, "rejeitados": 0, "itens": [], "backup": ""}
    if not dry_run:
        resultado["backup"] = str(criar_backup_emergencia())
    for oferta in ofertas:
        analise = analisar_produto({**oferta, "preco_atual": oferta.get("preco_atual") or oferta.get("preco"), "desconto": oferta.get("desconto_percentual") or 0})
        if analise["aprovado"]:
            destino = "aprovado_auto"
            resultado["aprovados"] += 1
        elif float(analise["score"]) < LIMITE_REVISAO:
            destino = "rejeitado"
            resultado["rejeitados"] += 1
        else:
            destino = "pendente_revisao"
            resultado["pendentes"] += 1
        resultado["itens"].append({"id": oferta["id"], "titulo": oferta["titulo"], "score": analise["score"], "destino": destino, "motivo": analise["motivo"]})
        if dry_run:
            continue
        promocao_id = salvar_promocao(oferta["produto_id"], analise["desconto"], analise["score"], destino, f"Curadoria enriquecida: {analise['motivo']}")
        with conectar() as conn:
            conn.execute("UPDATE postagens SET status=?, motivo=?, promocao_id=?, atualizado_em=? WHERE id=?", (destino, analise["motivo"], promocao_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), oferta["id"]))
        registrar_log("curadoria_enriquecida", f"Postagem={oferta['id']} -> {destino}", dados=analise["motivo"])
    _relatorio(resultado, dry_run)
    return resultado


def _relatorio(resultado, dry_run):
    motivos = Counter(item["motivo"] for item in resultado["itens"])
    sinais = Counter()
    with conectar() as conn:
        sinais["categorias_reais"] = conn.execute("SELECT COUNT(*) FROM produtos WHERE categoria_nome IS NOT NULL AND categoria_nome != '' AND categoria_nome != 'ofertas'").fetchone()[0]
        sinais["breadcrumbs"] = conn.execute("SELECT COUNT(*) FROM produtos WHERE categoria_caminho IS NOT NULL AND categoria_caminho != ''").fetchone()[0]
        sinais["mais_vendidos"] = conn.execute("SELECT COUNT(*) FROM produtos WHERE selo_mais_vendido=1").fetchone()[0]
        sinais["lojas_oficiais"] = conn.execute("SELECT COUNT(*) FROM produtos WHERE selo_loja_oficial=1").fetchone()[0]
    linhas = ["# Relatório de Enriquecimento de Ofertas", "", f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"- Modo: {'dry-run' if dry_run else 'execução real'}", f"- Backup: {resultado['backup'] or 'não aplicável'}", f"- Total analisado: {resultado['total']}", f"- Aprovadas: {resultado['aprovados']}", f"- Pendentes: {resultado['pendentes']}", f"- Rejeitadas: {resultado['rejeitados']}", "", "## Dados enriquecidos"]
    linhas += [f"- {chave.replace('_', ' ')}: {valor}" for chave, valor in sinais.items()]
    linhas += ["", "## Motivos principais"] + [f"- {motivo}: {total}" for motivo, total in motivos.most_common(10)]
    linhas += ["", "## Exemplos"] + [f"- {item['destino']} | score={item['score']:.0f} | {item['titulo']}" for item in resultado["itens"][:15]]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
