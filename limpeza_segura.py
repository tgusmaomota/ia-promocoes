"""Quarentena reversível para artefatos auditados, com backup completo prévio."""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from banco import DB_PATH, inicializar_banco, registrar_evento_sistema


CANDIDATOS_CONFIRMADOS = (
    Path("backup_remocao"),
    Path("relatorio_homologacao.txt"),
    Path("relatorio_limpeza.txt"),
)
PASTA_BACKUPS = Path("backups") / "limpeza_segura"
PASTA_QUARENTENA = Path("quarentena_remocao")


def _copiar(origem, destino):
    if origem.is_dir():
        shutil.copytree(origem, destino)
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)


def criar_backup_limpeza():
    """Preserva dados e fontes antes de qualquer movimentação local."""
    inicializar_banco()
    momento = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = PASTA_BACKUPS / momento
    destino.mkdir(parents=True, exist_ok=False)
    origem_db = sqlite3.connect(DB_PATH)
    copia_db = sqlite3.connect(destino / "banco.db")
    try:
        origem_db.backup(copia_db)
    finally:
        copia_db.close()
        origem_db.close()
    for arquivo in Path(".").glob("*.csv"):
        _copiar(arquivo, destino / "csv" / arquivo.name)
    for arquivo in Path(".").glob("*.py"):
        _copiar(arquivo, destino / "fontes" / arquivo.name)
    for arquivo in (Path(".env.example"), Path(".gitignore")):
        if arquivo.exists():
            _copiar(arquivo, destino / "config" / arquivo.name)
    for pasta in (Path("site"), Path("dist_site")):
        if pasta.exists():
            _copiar(pasta, destino / pasta.name)
    return destino


def executar_limpeza_segura():
    backup = criar_backup_limpeza()
    momento = datetime.now().strftime("%Y%m%d_%H%M%S")
    raiz_quarentena = PASTA_QUARENTENA / momento
    movidos = []
    for candidato in CANDIDATOS_CONFIRMADOS:
        if not candidato.exists():
            continue
        destino = raiz_quarentena / candidato
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(candidato), str(destino))
        movidos.append(str(candidato))
    registrar_evento_sistema("limpeza_segura", "manutencao", "sucesso", "Limpeza reversível concluída", f"movidos={len(movidos)} backup={backup.name}")
    return backup, raiz_quarentena, movidos
