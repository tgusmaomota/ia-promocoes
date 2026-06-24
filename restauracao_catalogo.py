"""Restauração segura de um catálogo estático válido, sem restaurar o banco."""

import io
import json
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from banco import DB_PATH
from catalogo_integridade import minimo_catalogo, resumo_catalogo, validar_catalogo_estatico


RELATORIO = Path("RELATORIO_RESTAURACAO_CATALOGO.md")
BACKUPS_DIR = Path("backups") / "restauracao_catalogo"
ARTEFATOS = ("site", "dist_site", "posts_prontos.csv", "whatsapp_posts.txt")


def _git(comando):
    resultado = subprocess.run(["git", *comando], capture_output=True, text=True, check=False)
    if resultado.returncode:
        raise RuntimeError((resultado.stderr or resultado.stdout).strip() or "comando Git falhou")
    return resultado.stdout


def _resumo_git(commit):
    try:
        dados = json.loads(_git(["show", f"{commit}:site/ofertas.json"]))
        ofertas = dados.get("ofertas", [])
        if not isinstance(ofertas, list):
            return None
        caminhos = set(_git(["ls-tree", "-r", "--name-only", commit, "--", "site"]).splitlines())
    except (RuntimeError, ValueError, json.JSONDecodeError):
        return None
    paginas_esperadas = set()
    links_invalidos = 0
    for oferta in ofertas:
        if not str(oferta.get("link") or "").startswith("https://meli.la/"):
            links_invalidos += 1
        pagina = "site/" + str(oferta.get("produto_url") or "").strip("/") + "/index.html"
        paginas_esperadas.add(pagina)
    paginas_ausentes = len(paginas_esperadas - caminhos)
    # O histórico pode conter uma página curta legado por item. Para a
    # restauração contam apenas as URLs declaradas no catálogo público.
    paginas = len(paginas_esperadas & caminhos)
    return {"ofertas": len(ofertas), "paginas": paginas, "links_invalidos": links_invalidos, "paginas_ausentes": paginas_ausentes, "erro": ""}


def listar_candidatos():
    candidatos = []
    for caminho in Path("backups").glob("**/site/ofertas.json"):
        raiz = caminho.parent.parent
        resumo = resumo_catalogo(raiz / "site")
        candidatos.append({"tipo": "backup", "origem": str(raiz), "site": str(raiz / "site"), "timestamp": caminho.stat().st_mtime, **resumo})

    vistos = set()
    try:
        linhas = _git(["log", "--all", "--format=%H|%ct", "--", "site/ofertas.json"]).splitlines()
    except RuntimeError:
        linhas = []
    for linha in linhas:
        try:
            commit, timestamp = linha.split("|", 1)
        except ValueError:
            continue
        if commit in vistos:
            continue
        vistos.add(commit)
        resumo = _resumo_git(commit)
        if resumo:
            candidatos.append({"tipo": "git", "origem": commit, "commit": commit, "timestamp": int(timestamp), **resumo})
    return sorted(candidatos, key=lambda item: (item["ofertas"], item["timestamp"]), reverse=True)


def _candidato_valido(candidato):
    return (
        not candidato.get("erro")
        and candidato.get("ofertas", 0) >= minimo_catalogo()
        and candidato.get("paginas") == candidato.get("ofertas")
        and not candidato.get("links_invalidos")
        and not candidato.get("paginas_ausentes")
    )


def _backup_estado_atual():
    destino = BACKUPS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    destino.mkdir(parents=True, exist_ok=False)
    if Path(DB_PATH).is_file():
        origem = sqlite3.connect(DB_PATH)
        try:
            copia = sqlite3.connect(destino / "banco.db")
            try:
                origem.backup(copia)
            finally:
                copia.close()
        finally:
            origem.close()
    for nome in ARTEFATOS:
        origem = Path(nome)
        if origem.is_dir():
            shutil.copytree(origem, destino / nome)
        elif origem.is_file():
            shutil.copy2(origem, destino / nome)
    return destino


def _extrair_git(commit, destino):
    caminhos = []
    for nome in ARTEFATOS:
        if subprocess.run(["git", "cat-file", "-e", f"{commit}:{nome}"], capture_output=True, check=False).returncode == 0:
            caminhos.append(nome)
    if "site" not in caminhos or "dist_site" not in caminhos:
        raise RuntimeError("O commit escolhido não contém site/ e dist_site/ completos.")
    resultado = subprocess.run(["git", "archive", "--format=tar", commit, *caminhos], capture_output=True, check=False)
    if resultado.returncode:
        raise RuntimeError("Não foi possível extrair o catálogo do histórico Git.")
    with tarfile.open(fileobj=io.BytesIO(resultado.stdout)) as arquivo:
        arquivo.extractall(destino, filter="data")


def _copiar_artefatos(origem, destino_projeto=Path(".")):
    restaurados = []
    for nome in ARTEFATOS:
        fonte = Path(origem) / nome
        destino = destino_projeto / nome
        if fonte.is_dir():
            if destino.exists():
                shutil.rmtree(destino)
            shutil.copytree(fonte, destino)
            restaurados.append(nome)
        elif fonte.is_file():
            shutil.copy2(fonte, destino)
            restaurados.append(nome)
    return restaurados


def _escrever_relatorio(resultado):
    candidato = resultado.get("candidato") or {}
    linhas = [
        "# Relatório de Restauração de Catálogo - Promogg", "",
        f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Modo: {'simulação' if resultado.get('dry_run') else 'restauração'}",
        f"- Origem: {candidato.get('tipo', 'nenhuma')} {candidato.get('origem', 'não encontrada')}",
        f"- Ofertas da origem: {candidato.get('ofertas', 0)}",
        f"- Páginas da origem: {candidato.get('paginas', 0)}",
        f"- Backup do estado anterior: {resultado.get('backup') or 'não criado'}", "",
        "## Arquivos restaurados",
    ]
    if resultado.get("restaurados"):
        linhas.extend(f"- {nome}" for nome in resultado["restaurados"])
    else:
        linhas.append("- nenhum")
    linhas += ["", "## Validação estática"]
    if resultado.get("erros"):
        linhas.extend(f"- {erro}" for erro in resultado["erros"])
    else:
        linhas.append("- aprovada")
    linhas += ["", "## Segurança", "- O banco SQLite não foi restaurado automaticamente.", "- Nenhum deploy, Telegram, coleta ou monitoramento foi executado.", "", "## Situação final", resultado.get("situacao", "")]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def restaurar_catalogo_valido(dry_run=False):
    candidatos = listar_candidatos()
    candidato = next((item for item in candidatos if _candidato_valido(item)), None)
    resultado = {"dry_run": dry_run, "candidatos": candidatos, "candidato": candidato, "restaurados": [], "erros": []}
    if not candidato:
        resultado["erros"].append("Nenhum backup ou commit possui catálogo estático válido acima do mínimo.")
        resultado["situacao"] = "Restauração bloqueada; use reconstrução a partir do banco depois de recuperar os status dos produtos."
        _escrever_relatorio(resultado)
        return resultado

    if dry_run:
        resultado["situacao"] = "Simulação aprovada. A restauração substituiria somente artefatos estáticos e auxiliares; banco preservado."
        _escrever_relatorio(resultado)
        return resultado

    backup = _backup_estado_atual()
    resultado["backup"] = str(backup)
    try:
        with tempfile.TemporaryDirectory(prefix="promogg_restaurar_catalogo_") as temporario:
            temporario = Path(temporario)
            if candidato["tipo"] == "git":
                _extrair_git(candidato["commit"], temporario)
            else:
                origem = Path(candidato["origem"])
                for nome in ARTEFATOS:
                    fonte = origem / nome
                    if fonte.is_dir():
                        shutil.copytree(fonte, temporario / nome)
                    elif fonte.is_file():
                        shutil.copy2(fonte, temporario / nome)
            resultado["restaurados"] = _copiar_artefatos(temporario)
        resultado["erros"] = validar_catalogo_estatico(Path("site"))
        resultado["situacao"] = (
            "Catálogo estático restaurado e validado; deploy permanece manual."
            if not resultado["erros"] else "Restauração concluída, mas a validação estática encontrou pendências."
        )
    except Exception as erro:
        resultado["erros"].append(str(erro))
        resultado["situacao"] = "Restauração interrompida; consulte o backup criado antes da operação."
    _escrever_relatorio(resultado)
    return resultado
