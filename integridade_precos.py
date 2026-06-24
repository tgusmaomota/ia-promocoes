"""Auditoria somente de leitura do histórico e da qualidade dos preços."""

from datetime import datetime
from pathlib import Path

from banco import conectar


RELATORIO = Path("RELATORIO_INTEGRIDADE_PRECOS.md")


def auditar_precos(escrever_relatorio=True):
    with conectar() as conn:
        colunas_historico = {linha[1] for linha in conn.execute("PRAGMA table_info(historico_precos)")}
        campo_fonte = "COALESCE(fonte_preco, 'não informado')" if "fonte_preco" in colunas_historico else "'não informado'"
        metricas = {
            "produtos_com_historico": conn.execute("SELECT COUNT(DISTINCT produto_id) FROM historico_precos WHERE preco IS NOT NULL").fetchone()[0],
            "produtos_sem_historico": conn.execute("SELECT COUNT(*) FROM produtos p WHERE NOT EXISTS (SELECT 1 FROM historico_precos h WHERE h.produto_id = p.id AND h.preco IS NOT NULL)").fetchone()[0],
            "precos_invalidos": conn.execute("SELECT COUNT(*) FROM produtos WHERE preco_atual IS NULL OR preco_atual <= 0").fetchone()[0],
            "subiram": conn.execute("SELECT COUNT(*) FROM produtos WHERE variacao_preco > 0").fetchone()[0],
            "cairam": conn.execute("SELECT COUNT(*) FROM produtos WHERE variacao_preco < 0").fetchone()[0],
            "menor_preco_historico": conn.execute("SELECT COUNT(*) FROM produtos WHERE destaque_menor_preco = 1").fetchone()[0],
            "indisponiveis_evidencia_real": conn.execute("SELECT COUNT(*) FROM produtos WHERE status = 'indisponivel' AND lower(COALESCE(motivo_indisponivel, '')) LIKE '%não encontrado%'").fetchone()[0],
            "verificacoes_inconclusivas": conn.execute("SELECT COUNT(*) FROM produtos WHERE status_verificacao IN ('erro_api', 'verificacao_inconclusiva')").fetchone()[0],
        }
        fontes = [dict(linha) for linha in conn.execute(
            f"SELECT {campo_fonte} AS fonte, COUNT(*) AS total FROM historico_precos GROUP BY fonte ORDER BY total DESC"
        ).fetchall()]

    resultado = {"metricas": metricas, "fontes": fontes}
    if escrever_relatorio:
        linhas = ["# Relatório de Integridade de Preços - Promogg", "", f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "", "## Métricas"]
        linhas.extend(f"- {chave.replace('_', ' ')}: {valor}" for chave, valor in metricas.items())
        linhas += ["", "## Fontes registradas"]
        if fontes:
            linhas.extend(f"- {item['fonte']}: {item['total']}" for item in fontes)
        else:
            linhas.append("- sem observações")
        RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return resultado
