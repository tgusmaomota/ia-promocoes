"""Homologação segura da publicação automática do Promogg."""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from catalogo_integridade import resumo_catalogo, validar_catalogo_estatico
from qualidade_catalogo import auditar_qualidade_catalogo


SITE = Path("site")
DIST = Path("dist_site")
RELATORIO = Path("RELATORIO_HOMOLOGACAO_PUBLICACAO_AUTOMATICA.md")

ARTEFATOS_GIT_PERMITIDOS = (
    "site/",
    "dist_site/",
    "site_promocoes.html",
    "posts_prontos.csv",
    "whatsapp_posts.txt",
    "RELATORIO_",
    "GUIA_COMPLETO_COMANDOS_PROMOGG.md",
)
SENSIVEIS_GIT = (".env", "banco.db", "promocoes.db", "perfil_mercadolivre", ".coleta_confiavel_checkpoint.json")


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _git_status_classificado():
    proc = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
    linhas = [linha for linha in proc.stdout.splitlines() if linha.strip()] if proc.returncode == 0 else []
    permitidas = []
    bloqueantes = []
    sensiveis = []
    for linha in linhas:
        caminho = linha[3:] if len(linha) > 3 else linha
        if any(caminho == s or caminho.startswith(s.rstrip("/") + "/") for s in SENSIVEIS_GIT):
            sensiveis.append(linha)
            bloqueantes.append(linha)
        elif any(caminho == p.rstrip("/") or caminho.startswith(p) for p in ARTEFATOS_GIT_PERMITIDOS):
            permitidas.append(linha)
        else:
            bloqueantes.append(linha)
    return {"permitidas": permitidas, "bloqueantes": bloqueantes, "sensiveis": sensiveis, "erro": proc.returncode != 0}


def _copiar_site_para_dist_preservando_cname():
    cname_atual = DIST / "CNAME"
    cname_texto = cname_atual.read_text(encoding="utf-8") if cname_atual.exists() else None
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SITE, DIST)
    if cname_texto and not (DIST / "CNAME").exists():
        (DIST / "CNAME").write_text(cname_texto, encoding="utf-8")


def _classificar_bloqueios(qualidade, site, dist, git):
    bloqueios = []
    if site.get("erro"):
        bloqueios.append(f"site inválido: {site['erro']}")
    if site["ofertas"] != site["paginas"]:
        bloqueios.append("site tem páginas != ofertas")
    if dist["ofertas"] != site["ofertas"] or dist["paginas"] != site["paginas"]:
        bloqueios.append("dist_site diverge de site")
    for chave, valor in qualidade.get("ressalvas_bloqueantes", {}).items():
        if valor:
            bloqueios.append(f"qualidade bloqueante: {chave}={valor}")
    if git["bloqueantes"]:
        bloqueios.append("Git possui alterações bloqueantes")
    return bloqueios


def _escrever_relatorio(resultado):
    def linhas_dict(dados):
        return [f"- {k}: {v}" for k, v in dados.items()] or ["- nenhuma"]

    def linhas_lista(itens):
        return [f"- {item}" for item in itens] or ["- nenhum"]

    linhas = [
        "# Relatório de Homologação da Publicação Automática",
        "",
        f"- Gerado em: {agora()}",
        f"- Modo: {'dry-run' if resultado['dry_run'] else 'execução real'}",
        "- Telegram real, deploy real, ONLINE, exclusão de banco/histórico/backups e limpeza de perfil não foram executados.",
        "",
        "## Bloqueios antes",
        *linhas_lista(resultado["bloqueios_antes"]),
        "",
        "## Site/dist_site antes",
        f"- site/: {resultado['antes']['site']['ofertas']} ofertas, {resultado['antes']['site']['paginas']} páginas",
        f"- dist_site/: {resultado['antes']['dist_site']['ofertas']} ofertas, {resultado['antes']['dist_site']['paginas']} páginas",
        "",
        "## Correções feitas",
        f"- dist_site reconstruído a partir de site validado: {resultado['dist_reconstruido']}",
        f"- CNAME preservado: {resultado['cname_preservado']}",
        "",
        "## Site/dist_site depois",
        f"- site/: {resultado['depois']['site']['ofertas']} ofertas, {resultado['depois']['site']['paginas']} páginas",
        f"- dist_site/: {resultado['depois']['dist_site']['ofertas']} ofertas, {resultado['depois']['dist_site']['paginas']} páginas",
        "",
        "## Ressalvas bloqueantes",
        *linhas_dict(resultado["qualidade"].get("ressalvas_bloqueantes", {})),
        "",
        "## Ressalvas informativas",
        *linhas_dict(resultado["qualidade"].get("ressalvas_informativas", {})),
        "",
        "## Git permitido",
        *linhas_lista(resultado["git"]["permitidas"][:80]),
        "",
        "## Git bloqueante",
        *linhas_lista(resultado["git"]["bloqueantes"][:80]),
        "",
        "## Resultado final",
        f"- Preparação aprovada: {resultado['aprovado']}",
        f"- `ciclo-automatico --publicar` liberado tecnicamente: {resultado['liberado_publicar']}",
    ]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def preparar_publicacao(dry_run=True):
    antes = {"site": resumo_catalogo(SITE), "dist_site": resumo_catalogo(DIST)}
    qualidade_antes = auditar_qualidade_catalogo()
    git_antes = _git_status_classificado()
    bloqueios_antes = _classificar_bloqueios(qualidade_antes, antes["site"], antes["dist_site"], git_antes)
    erros_site = validar_catalogo_estatico(SITE)
    dist_reconstruido = False
    cname_preservado = False
    if not dry_run:
        if erros_site:
            raise RuntimeError("site/ não passou na validação estática: " + "; ".join(erros_site[:5]))
        cname_preservado = (DIST / "CNAME").exists()
        _copiar_site_para_dist_preservando_cname()
        dist_reconstruido = True
    depois = {"site": resumo_catalogo(SITE), "dist_site": resumo_catalogo(DIST)}
    qualidade = auditar_qualidade_catalogo()
    git = _git_status_classificado()
    bloqueios = _classificar_bloqueios(qualidade, depois["site"], depois["dist_site"], git)
    resultado = {
        "dry_run": dry_run,
        "antes": antes,
        "depois": depois,
        "qualidade": qualidade,
        "git": git,
        "bloqueios_antes": bloqueios_antes,
        "bloqueios": bloqueios,
        "dist_reconstruido": dist_reconstruido,
        "cname_preservado": cname_preservado,
        "aprovado": not bloqueios,
        "liberado_publicar": not bloqueios,
    }
    _escrever_relatorio(resultado)
    return resultado
