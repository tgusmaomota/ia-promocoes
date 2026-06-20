"""Saneamento seguro de títulos já persistidos."""

import shutil
from datetime import datetime
from pathlib import Path

from banco import DB_PATH, conectar, inicializar_banco, registrar_log
from saneamento_ofertas import PADRAO_OFF, PADRAO_PRECO, sanear_titulo


PASTA_BACKUP = Path("backups") / "saneamento_titulos"
RELATORIO = Path("RELATORIO_LIMPEZA_TITULOS.md")


def limpar_titulos_existentes():
    inicializar_banco()
    PASTA_BACKUP.mkdir(parents=True, exist_ok=True)
    instante = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = PASTA_BACKUP / f"banco_antes_titulos_{instante}.db"
    shutil.copy2(DB_PATH, backup)
    corrigidos = []
    with conectar() as conn:
        produtos = conn.execute(
            "SELECT id, titulo, preco_atual, preco_original, desconto_percentual FROM produtos"
        ).fetchall()
        for produto in produtos:
            titulo = str(produto["titulo"] or "")
            if not (PADRAO_PRECO.search(titulo) or PADRAO_OFF.search(titulo)):
                continue
            dados = sanear_titulo(
                titulo, produto["preco_atual"], produto["preco_original"], produto["desconto_percentual"]
            )
            if not dados["corrigido"]:
                continue
            conn.execute(
                """
                UPDATE produtos
                SET titulo=?, preco_original=COALESCE(?, preco_original),
                    desconto_percentual=COALESCE(?, desconto_percentual),
                    economia_valor=COALESCE(?, economia_valor), atualizado_em=?
                WHERE id=?
                """,
                (dados["titulo"], dados["preco_original"], dados["desconto_percentual"], dados["economia_valor"],
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), produto["id"]),
            )
            conn.execute("UPDATE postagens SET titulo=? WHERE produto_id=?", (dados["titulo"], produto["id"]))
            corrigidos.append((titulo, dados["titulo"]))
    linhas = [
        "# Relatório de Limpeza de Títulos", "",
        f"- Data/hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Backup: {backup}",
        f"- Títulos corrigidos: {len(corrigidos)}", "", "## Exemplos",
    ]
    linhas += [f"- Antes: {antes}\n  Depois: {depois}" for antes, depois in corrigidos[:20]] or ["- Nenhum título exigiu correção."]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    registrar_log("saneamento_titulos", f"Títulos saneados: {len(corrigidos)}; backup={backup}")
    return {"corrigidos": len(corrigidos), "backup": str(backup), "exemplos": corrigidos[:5]}
