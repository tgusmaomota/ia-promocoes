from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    navegador = p.chromium.launch(headless=False)
    pagina = navegador.new_page()

    pagina.goto("https://www.mercadolivre.com.br")
    print("Título da página:", pagina.title())

    pagina.screenshot(path="teste_mercadolivre.png", full_page=True)

    print("Navegador ficará aberto por 30 segundos...")
    time.sleep(30)

    navegador.close()