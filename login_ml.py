from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    navegador = p.chromium.launch_persistent_context(
        user_data_dir="perfil_mercadolivre",
        headless=False
    )

    pagina = navegador.new_page()

    pagina.goto("https://www.mercadolivre.com.br")

    print("Faça login manualmente.")
    print("Depois pressione ENTER aqui no terminal.")

    input()

    navegador.close()