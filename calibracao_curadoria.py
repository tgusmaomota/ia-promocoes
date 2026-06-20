"""Aplicação controlada da regra C, sem publicar ou fazer deploy."""

from datetime import datetime
from pathlib import Path

from atualizar_categorias import atualizar_categorias
from operacao_sistema import criar_backup_emergencia
from reprocessar_pendentes import reprocessar_pendentes


RELATORIO = Path("RELATORIO_CALIBRACAO_CURADORIA.md")


def aplicar_calibracao():
    backup = criar_backup_emergencia()
    categorias = atualizar_categorias()
    resultado = reprocessar_pendentes(dry_run=False, backup_existente=backup)
    linhas = [
        "# Relatório de Calibração da Curadoria", "",
        f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Backup antes da operação: {backup}",
        "- Regra aplicada: aprovação automática >= 65 com evidência de preço; revisão >= 45; rejeição abaixo de 45.",
        f"- Pendentes analisadas: {resultado['total']}",
        f"- Novas aprovadas automaticamente: {resultado['aprovados_auto']}",
        f"- Continuam pendentes: {resultado['pendentes']}",
        f"- Rejeitadas: {resultado['rejeitados']}",
        f"- Categorias reais atualizadas: {categorias['atualizadas']}",
        f"- Categorias já reais: {categorias['ja_reais']}",
        f"- Mantidas com fallback: {categorias['fallback']}",
        f"- Erros de API: {categorias['erros']}", "",
        "## Exemplos de reprocessamento",
    ]
    for item in resultado["itens"][:15]:
        linhas.append(f"- #{item['postagem_id']}: {item['antes']} -> {item['depois']} | score={item['score']:.0f} | {item['titulo']}")
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return {"backup": str(backup), "categorias": categorias, "curadoria": resultado, "relatorio": str(RELATORIO)}
