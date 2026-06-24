"""Login manual no Mercado Livre usando o perfil persistente do Playwright."""

from pathlib import Path

from playwright.sync_api import sync_playwright

from playwright_perfil import PERFIL_PRINCIPAL, diagnosticar_perfil


URL_INICIAL = "https://www.mercadolivre.com.br/"
URL_CONTA = "https://www.mercadolivre.com.br/my-account"


def _sessao_autenticada(pagina):
    """Confirma a sessão por sinais públicos da navegação, sem ler cookies."""
    try:
        pagina.goto(URL_CONTA, wait_until="domcontentloaded", timeout=30000)
        pagina.wait_for_timeout(1200)
    except Exception:
        return False, "Não foi possível confirmar a área da conta."

    url = pagina.url.lower()
    if any(trecho in url for trecho in ("login", "authorization", "identify")):
        return False, "O Mercado Livre redirecionou para a tela de login."

    try:
        texto = pagina.locator("body").inner_text(timeout=5000).lower()
    except Exception:
        texto = ""

    sinais_autenticado = ("minha conta", "minhas compras", "meus dados", "vender")
    sinais_deslogado = ("entre", "crie a sua conta", "crie sua conta")
    if any(sinal in texto for sinal in sinais_autenticado) and not all(
        sinal in texto for sinal in sinais_deslogado
    ):
        return True, "Área da conta acessível."
    return False, "Não foram encontrados sinais suficientes de uma sessão autenticada."


def login_manual_mercadolivre(perfil=PERFIL_PRINCIPAL, esperar=input):
    """Abre o navegador, aguarda o usuário e preserva a sessão ao fechar.

    Esta rotina não acessa banco, não coleta ofertas e não executa ações de publicação.
    """
    perfil = Path(perfil)
    diagnostico = diagnosticar_perfil(perfil)
    if diagnostico["processos"] or diagnostico["locks"]:
        raise RuntimeError(
            "O perfil Playwright está em uso ou bloqueado. Feche apenas o navegador desse perfil "
            "ou execute: python3 ia_promocoes.py reparar-playwright"
        )

    perfil.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch_persistent_context(
            user_data_dir=str(perfil),
            headless=False,
        )
        try:
            pagina = navegador.pages[0] if navegador.pages else navegador.new_page()
            pagina.goto(URL_INICIAL, wait_until="domcontentloaded", timeout=30000)
            print("\nFaça login manualmente no navegador aberto.")
            print("Quando a conta estiver conectada, volte a este terminal e pressione Enter.")
            esperar()
            autenticada, mensagem = _sessao_autenticada(pagina)
            return {"autenticada": autenticada, "mensagem": mensagem, "perfil": str(perfil)}
        finally:
            # Contexto persistente grava os cookies e o estado de sessão ao fechar.
            navegador.close()


def main():
    try:
        resultado = login_manual_mercadolivre()
    except Exception as erro:
        print(f"Login manual não concluído: {erro}")
        return 1
    print(resultado["mensagem"])
    print("Sessão preservada no perfil Playwright." if resultado["autenticada"] else "Sessão não confirmada.")
    return 0 if resultado["autenticada"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
