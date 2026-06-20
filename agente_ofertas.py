from playwright.sync_api import sync_playwright
import pandas as pd
import re

from csv_utils import COLUNAS_PRODUTOS_BUSCA, salvar_csv


ARQUIVO_SAIDA = "produtos_busca.csv"
TOTAL_PAGINAS = 20
DESCONTO_MINIMO = 0
TIPOS_PROMOCAO_VALIDOS = {"oferta_do_dia", "oferta_relampago"}


def extrair_preco(texto):
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    precos = []

    for i in range(len(linhas)):
        if linhas[i] != "R$":
            continue

        if i + 1 >= len(linhas):
            continue

        inteiro = linhas[i + 1].replace(".", "").strip()

        if not inteiro.isdigit():
            continue

        preco_texto = inteiro

        if i + 3 < len(linhas) and linhas[i + 2] == ",":
            centavos = linhas[i + 3].strip()

            if centavos.isdigit():
                preco_texto = f"{inteiro}.{centavos}"

        try:
            preco = float(preco_texto)
        except:
            continue

        contexto_antes = " ".join(linhas[max(0, i - 6):i]).lower()
        contexto_depois = " ".join(linhas[i:min(len(linhas), i + 10)]).lower()
        contexto = contexto_antes + " " + contexto_depois

        if "sem juros" in contexto:
            continue

        if "cartão mercado pago" in contexto:
            continue

        if "cartao mercado pago" in contexto:
            continue

        if "x" in contexto_antes:
            continue

        precos.append(preco)

    if not precos:
        return 0.0

    return precos[0]


def extrair_item_id(link):
    resultado = re.search(r"MLB\d+", str(link))

    if resultado:
        return resultado.group(0)

    resultado = re.search(r"item_id%3A(MLB\d+)", str(link))

    if resultado:
        return resultado.group(1)

    resultado = re.search(r"wid=(MLB\d+)", str(link))

    if resultado:
        return resultado.group(1)

    return ""


def extrair_item_id_pagina(pagina_produto):
    try:
        url_final = pagina_produto.url
        item_id = extrair_item_id(url_final)

        if item_id:
            return item_id
    except:
        pass

    try:
        html = pagina_produto.content()
        item_id = extrair_item_id(html)

        if item_id:
            return item_id
    except:
        pass

    return ""


def extrair_preco_pagina(navegador, link):
    pagina_produto = navegador.new_page()
    pagina_produto.set_default_timeout(12000)

    try:
        pagina_produto.goto(link, wait_until="domcontentloaded", timeout=30000)
        pagina_produto.wait_for_timeout(4000)

        item_id_pagina = extrair_item_id_pagina(pagina_produto)

        try:
            meta = pagina_produto.locator("meta[itemprop='price']").first
            valor = meta.get_attribute("content")

            if valor:
                preco = float(valor)
                pagina_produto.close()
                return preco, item_id_pagina
        except:
            pass

        try:
            meta = pagina_produto.locator("meta[property='product:price:amount']").first
            valor = meta.get_attribute("content")

            if valor:
                preco = float(valor)
                pagina_produto.close()
                return preco, item_id_pagina
        except:
            pass

        seletores = [
            "div.ui-pdp-price__second-line span.andes-money-amount__fraction",
            "div.ui-pdp-price__main-container span.andes-money-amount__fraction",
            "span.andes-money-amount__fraction"
        ]

        for seletor in seletores:
            try:
                elementos = pagina_produto.locator(seletor).all()

                for elemento in elementos:
                    texto = elemento.inner_text().strip()
                    texto = texto.replace(".", "").replace(",", ".")

                    if texto.isdigit():
                        valor = float(texto)

                        if valor > 0:
                            pagina_produto.close()
                            return valor, item_id_pagina
            except:
                pass

        texto_body = pagina_produto.inner_text("body", timeout=12000)
        preco = extrair_preco(texto_body)

        return preco, item_id_pagina

    except Exception as erro:
        print("Erro ao abrir página do produto:", erro)
        return 0.0, ""

    finally:
        try:
            pagina_produto.close()
        except:
            pass


def extrair_desconto(texto):
    resultado = re.search(r"(\d+)%\s*OFF", texto.upper())

    if resultado:
        return int(resultado.group(1))

    return 0


def identificar_tipo_promocao(texto):
    texto = texto.upper()

    if "OFERTA RELÂMPAGO" in texto or "OFERTA RELAMPAGO" in texto:
        return "oferta_relampago"

    if "OFERTA DO DIA" in texto:
        return "oferta_do_dia"

    return ""


def preco_suspeito(titulo, preco):
    titulo_lower = titulo.lower()

    produto_eletronico_caro = any(
        palavra in titulo_lower
        for palavra in [
            "monitor",
            "projetor",
            "smartwatch",
            "câmera",
            "camera",
            "webcam",
            "impressora",
            "furadeira",
            "solda",
            "serra",
            "inversora",
            "multimidia"
        ]
    )

    if produto_eletronico_caro and preco < 100:
        return True

    return False


def montar_urls_ofertas():
    urls = ["https://www.mercadolivre.com.br/ofertas"]

    for pagina in range(2, TOTAL_PAGINAS + 1):
        urls.append(f"https://www.mercadolivre.com.br/ofertas?page={pagina}")

    return urls


def coletar_ofertas(perfil="perfil_mercadolivre"):
    resultados = []
    item_ids_vistos = set()

    try:
        playwright = sync_playwright().start()
    except Exception as erro:
        print("Erro ao iniciar Playwright:", erro)
        return resultados

    navegador = None

    try:
        navegador = playwright.chromium.launch_persistent_context(
            user_data_dir=perfil,
            headless=False
        )

        pagina = navegador.new_page()
        pagina.set_default_timeout(12000)
        urls = montar_urls_ofertas()

        for numero, url in enumerate(urls, start=1):
            print("\n" + "=" * 60)
            print(f"Página {numero}/{TOTAL_PAGINAS}")
            print(url)
            print("=" * 60)

            try:
                # A página de ofertas pode manter conexões abertas; limite a navegação
                # para que uma coleta não permaneça presa indefinidamente.
                pagina.goto(url, wait_until="domcontentloaded", timeout=45000)
                pagina.wait_for_timeout(7000)

                for _ in range(4):
                    pagina.mouse.wheel(0, 2500)
                    pagina.wait_for_timeout(1500)

                cards = pagina.locator("div.andes-card").all()

                print("Cards encontrados:", len(cards))

                for card in cards:
                    try:
                        texto_card = card.inner_text()

                        tipo_promocao = identificar_tipo_promocao(texto_card)

                        if tipo_promocao not in TIPOS_PROMOCAO_VALIDOS:
                            continue

                        desconto = extrair_desconto(texto_card)

                        if desconto < DESCONTO_MINIMO:
                            continue

                        links = card.locator("a").all()

                        link = ""
                        titulo = ""

                        link_comum = ""
                        titulo_comum = ""
                        for elemento in links:
                            href = elemento.get_attribute("href")
                            texto_link = elemento.inner_text().strip()

                            if href and "meli.la/" in href:
                                link = href
                                titulo = texto_link
                                break
                            if href and "mercadolivre.com.br" in href and not link_comum:
                                link_comum = href
                                titulo_comum = texto_link

                        if not link and link_comum:
                            link = link_comum
                            titulo = titulo_comum

                        if not link:
                            continue

                        item_id = extrair_item_id(link)

                        print("Conferindo página:", titulo[:50])

                        preco, item_id_pagina = extrair_preco_pagina(
                            navegador,
                            link
                        )

                        if item_id == "" and item_id_pagina != "":
                            item_id = item_id_pagina

                        if item_id == "":
                            print("Ignorado sem item_id:", titulo[:50])
                            continue

                        if item_id in item_ids_vistos:
                            continue

                        if preco_suspeito(titulo, preco):
                            print("Ignorado preço suspeito:", titulo[:50], "R$", preco)
                            continue

                        if preco <= 0:
                            print("Ignorado sem preço:", titulo[:50])
                            continue

                        imagem = ""

                        try:
                            img = card.locator("img").first
                            imagem = img.get_attribute("src")
                        except:
                            imagem = ""

                        item_ids_vistos.add(item_id)

                        print(
                            f"{tipo_promocao} | {desconto}% OFF | "
                            f"R$ {preco} | {titulo[:60]}"
                        )

                        resultados.append({
                            "titulo": titulo,
                            "link": link,
                            "item_id": item_id,
                            "preco": preco,
                            "preco_confiavel": "sim",
                            "desconto": desconto,
                            "tipo_promocao": tipo_promocao,
                            "imagem": imagem,
                            "categoria": "ofertas"
                        })

                    except Exception as erro:
                        print("Erro em um card:", erro)

            except Exception as erro:
                print("Erro na página:", erro)

    except Exception as erro:
        print("Erro geral no coletor de ofertas:", erro)
    finally:
        if navegador:
            try:
                navegador.close()
            except Exception as erro:
                print("Erro ao fechar navegador:", erro)

        try:
            playwright.stop()
        except Exception as erro:
            print("Erro ao finalizar Playwright:", erro)

    return resultados


if __name__ == "__main__":
    produtos = coletar_ofertas()

    df = pd.DataFrame(produtos, columns=COLUNAS_PRODUTOS_BUSCA)

    if not df.empty:
        df = df.drop_duplicates(subset=["item_id"])

    df = salvar_csv(df, ARQUIVO_SAIDA, COLUNAS_PRODUTOS_BUSCA)

    print("\nFinalizado.")
    print("Total de ofertas salvas:", len(df))
    print("Arquivo criado:", ARQUIVO_SAIDA)
