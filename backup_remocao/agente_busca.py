from playwright.sync_api import sync_playwright
import pandas as pd
import time
import re

from csv_utils import COLUNAS_PRODUTOS_BUSCA, salvar_csv


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

            contexto = " ".join(
                linhas[max(0, i - 3): min(len(linhas), i + 8)]
            ).lower()

            if "sem juros" in contexto:
                continue

            if "cartão mercado pago" in contexto:
                continue

            precos.append(preco)

        except:
            pass

    if not precos:
        return 0.0

    return min(precos)


def validar_preco(termo, titulo, preco):
    termo = termo.lower()
    titulo = titulo.lower()

    if preco <= 0:
        return "nao"

    if "air fryer" in termo or "air fryer" in titulo or "fritadeira" in titulo:
        if preco < 150:
            return "nao"
        if preco > 1500:
            return "nao"

    if "iphone" in titulo:
        if preco < 1000:
            return "nao"

    if "celular" in termo or "smartphone" in titulo:
        if preco < 300:
            return "nao"

    return "sim"


def extrair_item_id(link):
    resultado = re.search(r"MLB\d+", link)

    if resultado:
        return resultado.group(0)

    resultado = re.search(r"item_id%3A(MLB\d+)", link)

    if resultado:
        return resultado.group(1)

    resultado = re.search(r"wid=(MLB\d+)", link)

    if resultado:
        return resultado.group(1)

    return ""


def buscar_produtos(termo):
    resultados = []

    with sync_playwright() as p:
        navegador = p.chromium.launch_persistent_context(
            user_data_dir="perfil_mercadolivre",
            headless=False
        )

        pagina = navegador.new_page()
        pagina.goto("https://www.mercadolivre.com.br")
        pagina.wait_for_timeout(3000)

        try:
            pagina.fill('input[name="as_word"]', termo)
            pagina.keyboard.press("Enter")
        except:
            print("Não achei o campo de busca.")
            time.sleep(60)
            navegador.close()
            return []

        pagina.wait_for_timeout(10000)

        cards = pagina.locator("li.ui-search-layout__item").all()

        print("Cards encontrados:", len(cards))

        for card in cards[:30]:
            try:
                texto_card = card.inner_text()

                link_elemento = card.locator("a.poly-component__title").first
                titulo = link_elemento.inner_text().strip()
                link = link_elemento.get_attribute("href")

                item_id = extrair_item_id(link)

                if item_id == "":
                    print("Produto ignorado sem item_id:", titulo[:60])
                    continue

                preco = extrair_preco(texto_card)

                preco_confiavel = validar_preco(
                    termo,
                    titulo,
                    preco
                )

                imagem = ""

                try:
                    img = card.locator("img").first
                    imagem = img.get_attribute("src")
                except:
                    imagem = ""

                print(
                    f"{titulo[:50]}... -> R$ {preco} | item_id: {item_id} | confiável: {preco_confiavel}"
                )

                if titulo and link:
                    resultados.append({
                        "titulo": titulo,
                        "link": link,
                        "item_id": item_id,
                        "preco": preco,
                        "preco_confiavel": preco_confiavel,
                        "desconto": 0,
                        "tipo_promocao": "",
                        "imagem": imagem,
                        "categoria": "eletrônicos"
                    })

            except Exception as erro:
                print("Erro em um card:", erro)

        navegador.close()

    return resultados


if __name__ == "__main__":

    termos = [
        "Acessórios para Veículos",
        "Agro",
        "Alimentos e Bebidas",
        "Antiguidades e Coleções",
        "Arte, Papelaria e Armarinho",
        "Bebês",
        "Beleza e Cuidado Pessoal",
        "Brinquedos e Hobbies",
        "Calçados, Roupas e Bolsas",
        "Casa, Móveis e Decoração",
        "Celulares e Telefones",
        "Construção",
        "Câmeras e Acessórios",
        "Eletrodomésticos",
        "Eletrônicos",
        "Esportes e Fitness",
        "Ferramentas",
        "Festas e Lembrancinhas",
        "Games",
        "Indústria e Comércio",
        "Informática",
        "Instrumentos Musicais",
        "Joias e Relógios",
        "Livros",
        "Pet Shop",
        "Saúde"
    ]

    todos_produtos = []

    for termo in termos:
        print(f"\nBuscando: {termo}")

        produtos = buscar_produtos(termo)

        todos_produtos.extend(produtos)

    df = pd.DataFrame(todos_produtos)

    if not df.empty:
        df = df.drop_duplicates(subset=["item_id"])

    print(f"Total final encontrados: {len(df)}")
    print(df.head())

    salvar_csv(df, "produtos_busca.csv", COLUNAS_PRODUTOS_BUSCA)

    print("Produtos salvos em produtos_busca.csv")
