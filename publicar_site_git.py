import argparse
import shutil
import subprocess
from pathlib import Path

from gerar_site import SITE_DIR, gerar_site


DOMINIO = "promogg.com.br"
DIST_DIR = Path("dist_site")
WORKFLOW_PATH = Path(".github/workflows/pages.yml")
README_PATH = Path("README_GITHUB_PAGES.md")
CNAME_PATH = DIST_DIR / "CNAME"


def executar(comando):
    resultado = subprocess.run(
        comando,
        check=False,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        saida = (resultado.stderr or resultado.stdout).strip()
        raise RuntimeError(f"{' '.join(comando)} falhou: {saida}")
    return resultado.stdout.strip()


def validar_git():
    try:
        executar(["git", "rev-parse", "--is-inside-work-tree"])
    except RuntimeError as erro:
        raise RuntimeError(
            "Esta pasta ainda não é um repositório Git. Rode git init e configure o remoto origin."
        ) from erro

    try:
        executar(["git", "remote", "get-url", "origin"])
    except RuntimeError as erro:
        raise RuntimeError(
            "O remoto origin não está configurado. Use git remote add origin URL_DO_REPOSITORIO."
        ) from erro


def branch_atual():
    branch = executar(["git", "branch", "--show-current"])
    return branch or "main"


def copiar_site_para_dist():
    gerar_site()
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    for item in SITE_DIR.iterdir():
        destino = DIST_DIR / item.name
        if item.is_dir():
            if destino.exists():
                shutil.rmtree(destino)
            shutil.copytree(item, destino)
        else:
            shutil.copy2(item, destino)

    CNAME_PATH.write_text(f"{DOMINIO}\n", encoding="utf-8")
    return DIST_DIR.resolve()


def subir_site(mensagem="Atualiza site IA-Promocoes"):
    destino = copiar_site_para_dist()
    validar_git()

    arquivos = [
        str(DIST_DIR),
        str(WORKFLOW_PATH),
        str(README_PATH),
        "publicar_site_git.py",
        "ia_promocoes.py",
    ]
    executar(["git", "add", *arquivos])

    status = executar(["git", "status", "--short"])
    commit_criado = bool(status)
    if commit_criado:
        executar(["git", "commit", "-m", mensagem])
    else:
        print("Nenhuma alteração nova para commit.")

    branch = branch_atual()
    executar(["git", "push", "origin", branch])
    return {
        "destino": str(destino),
        "dominio": DOMINIO,
        "branch": branch,
        "commit_criado": commit_criado,
    }


def main():
    parser = argparse.ArgumentParser(description="Publica dist_site/ no GitHub Pages")
    parser.add_argument("--mensagem", default="Atualiza site IA-Promocoes")
    args = parser.parse_args()

    try:
        resultado = subir_site(args.mensagem)
    except RuntimeError as erro:
        print(f"Erro ao publicar site: {erro}")
        return 1

    print(f"Site gerado em: {resultado['destino']}")
    print(f"CNAME: {resultado['dominio']}")
    print(f"Push enviado para origin/{resultado['branch']}")
    print("O GitHub Pages será atualizado pelo GitHub Actions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
