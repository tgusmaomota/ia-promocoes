"""Comandos locais de operação: relatório, backup e listagem segura de recuperação."""

import json
import os
import shutil
import sqlite3
import tempfile
from datetime import date, datetime
from pathlib import Path

from banco import DB_PATH, conectar, inicializar_banco, registrar_evento_sistema
from saude_sistema import obter_relatorio_saude


BACKUP_DIR = Path("backups") / "operacao"
ARQUIVOS_AUXILIARES = ("posts_prontos.csv", "produtos.csv", "historico_precos.csv", ".env.example")
CONFIGURACOES_PUBLICAS = (
    "IA_PROMOCOES_DOMINIO", "INTERVALO_COLETA_MINUTOS", "INTERVALO_POSTAGEM_MINUTOS",
    "LIMITE_POSTS_DIA", "OLLAMA_MODEL", "PROMOGG_ANALYTICS_URL", "PROMOGG_ANALYTICS_ORIGINS",
)


def criar_backup_emergencia():
    """Cria ZIP local com snapshot SQLite e configurações sem tokens ou segredos."""
    inicializar_banco()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    momento = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = BACKUP_DIR / f"promogg_backup_{momento}.zip"
    with tempfile.TemporaryDirectory(prefix="promogg_backup_") as temporario:
        pasta = Path(temporario)
        banco_destino = pasta / "banco.db"
        origem = sqlite3.connect(DB_PATH)
        copia = sqlite3.connect(banco_destino)
        try:
            origem.backup(copia)
        finally:
            copia.close()
            origem.close()
        for nome in ARQUIVOS_AUXILIARES:
            arquivo = Path(nome)
            if arquivo.is_file():
                shutil.copy2(arquivo, pasta / arquivo.name)
        configuracoes = "\n".join(f"{nome}={os.getenv(nome, '')}" for nome in CONFIGURACOES_PUBLICAS) + "\n"
        (pasta / "configuracoes_publicas.env").write_text(configuracoes, encoding="utf-8")
        (pasta / "manifesto.json").write_text(json.dumps({
            "criado_em": datetime.now().isoformat(timespec="seconds"),
            "conteudo": ["banco.db", "historico de preços no SQLite", "CSVs existentes", "configurações sem segredos"],
            "nao_incluido": [".env", "tokens", "cookies", "segredos"],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.make_archive(str(destino.with_suffix("")), "zip", pasta)
    registrar_evento_sistema("backup", "operacao", "sucesso", "Backup de emergência criado", destino.name)
    return destino


def listar_backups():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(BACKUP_DIR.glob("promogg_backup_*.zip"), key=lambda caminho: caminho.stat().st_mtime, reverse=True)


def imprimir_backups_disponiveis():
    backups = listar_backups()
    if not backups:
        print("Nenhum backup operacional disponível.")
        return backups
    print("Backups disponíveis (a restauração é manual e não sobrescreve dados automaticamente):")
    for backup in backups:
        data = datetime.fromtimestamp(backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"- {backup} | {backup.stat().st_size / 1024:.1f} KB | {data}")
    return backups


def imprimir_relatorio_operacional():
    inicializar_banco()
    hoje = date.today().isoformat()
    with conectar() as conn:
        dados = {
            "ofertas_coletadas": conn.execute("SELECT COUNT(*) FROM produtos WHERE substr(COALESCE(data_coleta, ''), 1, 10) = ?", (hoje,)).fetchone()[0],
            "ofertas_aprovadas": conn.execute("SELECT COUNT(*) FROM postagens WHERE status IN ('aprovado_auto', 'aprovado_manual')").fetchone()[0],
            "ofertas_rejeitadas": conn.execute("SELECT COUNT(*) FROM postagens WHERE status = 'rejeitado'").fetchone()[0],
            "ofertas_publicadas": conn.execute("SELECT COUNT(*) FROM postagens WHERE status = 'publicado'").fetchone()[0],
            "produtos_monitorados": conn.execute("SELECT COUNT(DISTINCT produto_id) FROM historico_precos WHERE substr(data_verificacao, 1, 10) = ?", (hoje,)).fetchone()[0],
            "atualizacoes_preco": conn.execute("SELECT COUNT(*) FROM historico_precos WHERE substr(data_verificacao, 1, 10) = ?", (hoje,)).fetchone()[0],
        }
    saude = obter_relatorio_saude()
    print("Relatório Operacional Promogg")
    for chave, valor in dados.items():
        print(f"{chave.replace('_', ' ').capitalize()}: {valor}")
    print(f"Erros nas últimas 24h: {len(saude['erros_24h'])}")
    print(f"Status geral: {saude['status_geral']}")
    return {**dados, "erros_24h": len(saude["erros_24h"]), "status_geral": saude["status_geral"]}


def validar_operacao_sistema():
    erros = []
    try:
        with conectar() as conn:
            if str(conn.execute("PRAGMA integrity_check").fetchone()[0]).lower() != "ok":
                erros.append("Integridade do banco SQLite falhou")
        if not BACKUP_DIR.exists():
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as erro:
        erros.append(f"Falha operacional: {erro}")
    return erros
