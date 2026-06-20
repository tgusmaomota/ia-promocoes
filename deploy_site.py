import argparse
import os
import shutil
import subprocess
from pathlib import Path

from banco import registrar_evento_sistema, registrar_log
from gerar_site import SITE_DIR, gerar_site


DIST_DIR = Path("dist_site")
DEFAULT_BRANCH = "main"
DOMAIN_ENV = "IA_PROMOCOES_DOMINIO"


def dominio_configurado(dominio=None):
    dominio = dominio or os.getenv(DOMAIN_ENV, "")
    return dominio.strip().removeprefix("https://").removeprefix("http://").strip("/")


def executar_git(args):
    resultado = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        detalhe = (resultado.stderr or resultado.stdout).strip()
        raise RuntimeError(f"git {' '.join(args)} falhou: {detalhe}")
    return resultado.stdout.strip()


def validar_repositorio_git():
    try:
        executar_git(["rev-parse", "--is-inside-work-tree"])
    except RuntimeError as erro:
        raise RuntimeError(
            "Esta pasta ainda não é um repositório Git. "
            "Crie o repositório, faça git init, adicione o remoto origin e rode novamente."
        ) from erro

    try:
        executar_git(["remote", "get-url", "origin"])
    except RuntimeError as erro:
        raise RuntimeError(
            "O remoto origin não está configurado. "
            "Use: git remote add origin https://github.com/USUARIO/REPOSITORIO.git"
        ) from erro


def branch_atual():
    branch = executar_git(["branch", "--show-current"])
    return branch or DEFAULT_BRANCH


def criar_cname(destino, dominio=None):
    dominio = dominio_configurado(dominio)
    cname = Path(destino) / "CNAME"

    if not dominio:
        if cname.exists():
            cname.unlink()
        return None

    cname.write_text(f"{dominio}\n", encoding="utf-8")
    return cname


def copiar_site(destino):
    gerar_site()
    origem = SITE_DIR.resolve()
    destino = Path(destino).expanduser().resolve()
    destino.mkdir(parents=True, exist_ok=True)

    for item in origem.iterdir():
        alvo = destino / item.name
        if item.is_dir():
            if alvo.exists():
                shutil.rmtree(alvo)
            shutil.copytree(item, alvo)
        else:
            shutil.copy2(item, alvo)

    registrar_log("deploy_site", f"Site preparado em {destino}")
    return destino


def preparar_dist_site(dominio=None):
    destino = copiar_site(DIST_DIR)
    cname = criar_cname(destino, dominio)
    if cname:
        registrar_log("deploy_site", f"CNAME configurado para {dominio_configurado(dominio)}")
    return destino


def publicar_no_github(dominio=None, mensagem="Atualiza site publico"):
    destino = preparar_dist_site(dominio)
    validar_repositorio_git()

    executar_git(["add", str(DIST_DIR), ".github/workflows/pages.yml", "README_SITE_PUBLICO.md"])
    status = executar_git(["status", "--short"])

    if status:
        executar_git(["commit", "-m", mensagem])
    else:
        print("Nenhuma alteração nova para commit.")

    branch = branch_atual()
    executar_git(["push", "origin", branch])
    registrar_log("deploy_site", f"Site enviado para GitHub na branch {branch}")
    registrar_evento_sistema("deploy_github", "github_pages", "concluido", "Deploy enviado ao GitHub Pages", f"branch={branch}")
    return destino, branch, bool(status)


def publicar_local(args):
    destino = copiar_site(args.destino)
    cname = criar_cname(destino, args.dominio)
    print(f"Site preparado em: {destino}")
    if cname:
        print(f"Domínio configurado em CNAME: {dominio_configurado(args.dominio)}")
    print("Publique essa pasta no provedor estático ou sirva com um servidor web.")


def publicar_github_pages(args):
    destino = copiar_site(args.destino)
    cname = criar_cname(destino, args.dominio)
    print(f"Arquivos copiados para GitHub Pages em: {destino}")
    if cname:
        print(f"Domínio configurado em CNAME: {dominio_configurado(args.dominio)}")
    print("Próximos comandos sugeridos dentro do repositório de Pages:")
    print("git status")
    print("git add .")
    print('git commit -m "Atualiza ofertas"')
    print("git push")


def publicar_github_actions(args):
    try:
        destino, branch, commit_criado = publicar_no_github(
            dominio=args.dominio,
            mensagem=args.mensagem,
        )
    except RuntimeError as erro:
        print(f"Erro no deploy: {erro}")
        return 1

    print(f"Site gerado e preparado em: {destino}")
    print(f"Arquivos enviados para o GitHub na branch: {branch}")
    if commit_criado:
        print("Um novo commit foi criado e enviado.")
    print("O GitHub Actions publicará dist_site/ no GitHub Pages.")
    return 0


def publicar_vps(_args):
    print("Deploy para VPS ainda não está ativo.")
    print("Use por enquanto: python3 deploy_site.py local --destino /caminho/publico")
    print("Depois a VPS pode receber rsync/scp, Nginx e systemd.")


def main():
    parser = argparse.ArgumentParser(description="Prepara publicação do site público")
    sub = parser.add_subparsers(dest="modo", required=True)

    local = sub.add_parser("local", help="Copia site/ para uma pasta local")
    local.add_argument("--destino", default="dist_site")
    local.add_argument("--dominio", help=f"Domínio próprio. Também aceita {DOMAIN_ENV} no .env")
    local.set_defaults(func=publicar_local)

    pages = sub.add_parser("github-pages", help="Copia site/ para um repositório/pasta do GitHub Pages")
    pages.add_argument("--destino", required=True)
    pages.add_argument("--dominio", help=f"Domínio próprio. Também aceita {DOMAIN_ENV} no .env")
    pages.set_defaults(func=publicar_github_pages)

    actions = sub.add_parser("github-actions", help="Gera dist_site/, cria CNAME, commita e envia ao GitHub")
    actions.add_argument("--dominio", help=f"Domínio próprio. Também aceita {DOMAIN_ENV} no .env")
    actions.add_argument("--mensagem", default="Atualiza site publico")
    actions.set_defaults(func=publicar_github_actions)

    vps = sub.add_parser("vps", help="Reserva para publicação futura em VPS")
    vps.set_defaults(func=publicar_vps)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
