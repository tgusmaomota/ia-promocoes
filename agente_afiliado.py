from playwright.sync_api import sync_playwright
import pandas as pd

from csv_utils import (
    COLUNAS_PRODUTOS_AFILIADOS,
    backup_arquivo,
    ler_csv,
    salvar_csv,
)

ARQUIVO_BUSCA = "produtos_filtrados.csv"
ARQUIVO_SAIDA = "produtos_afiliados.csv"


def salvar_resultados(resultados):
    salvar_csv(
        pd.DataFrame(resultados, columns=COLUNAS_PRODUTOS_AFILIADOS),
        ARQUIVO_SAIDA,
        COLUNAS_PRODUTOS_AFILIADOS,
        criar_backup=False,
    )


def abrir_pagina_com_tentativas(pagina, link, tentativas=2):
    for tentativa in range(1, tentativas + 1):
        try:
            pagina.goto(link, wait_until="domcontentloaded", timeout=30000)
            pagina.wait_for_timeout(5000)
            return True
        except Exception as erro:
            print(f"Erro ao abrir produto. Tentativa {tentativa}/{tentativas}")
            print(erro)
            pagina.wait_for_timeout(3000)
    return False


def gerar_link_afiliado(pagina):
    # Mantido para compatibilidade com o script legado; usa o seletor oficial.
    from gerador_afiliados_oficial import _gerar_em_pagina

    return _gerar_em_pagina(pagina, pagina.url)


df = ler_csv(ARQUIVO_BUSCA)

if df.empty:
    backup_arquivo(ARQUIVO_SAIDA)
    salvar_resultados([])
    print("Nenhum produto filtrado para gerar link afiliado.")
    print("Arquivo produtos_afiliados.csv limpo.")
    exit()

resultados = []

backup = backup_arquivo(ARQUIVO_SAIDA)
if backup:
    print(f"Backup criado: {backup}")

try:
    playwright = sync_playwright().start()
except Exception as erro:
    print("Erro ao iniciar Playwright:", erro)
    salvar_resultados(resultados)
    raise SystemExit(0)

navegador = None

try:
    navegador = playwright.chromium.launch_persistent_context(
        user_data_dir="perfil_mercadolivre",
        headless=False
    )

    pagina = navegador.new_page()

    for _, produto in df.iterrows():
        titulo = str(produto.get("titulo", "")).strip()
        link_original = str(produto.get("link", "")).strip()

        if not titulo or not link_original:
            print("Produto ignorado sem título ou link.")
            continue

        print("Abrindo:", titulo)

        abriu = abrir_pagina_com_tentativas(pagina, link_original)

        if not abriu:
            print("Ignorado por erro ao abrir:", titulo)
            salvar_resultados(resultados)
            continue

        link_afiliado = gerar_link_afiliado(pagina)

        if not link_afiliado:
            print("Sem link afiliado gerado:", titulo)
            salvar_resultados(resultados)
            continue

        print("Link afiliado:", link_afiliado)

        resultados.append({
            "titulo": titulo,
            "item_id": produto.get("item_id", ""),
            "score": produto.get("score", 0),
            "preco": produto.get("preco", 0),
            "preco_confiavel": produto.get("preco_confiavel", "sim"),
            "desconto": produto.get("desconto", 0),
            "tipo_promocao": produto.get("tipo_promocao", ""),
            "link_original": link_original,
            "link_afiliado": link_afiliado,
            "imagem": produto.get("imagem", ""),
            "categoria": produto.get("categoria", "")
        })

        salvar_resultados(resultados)

except Exception as erro:
    print("Erro geral no agente afiliado:", erro)
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

salvar_resultados(resultados)

print("Arquivo produtos_afiliados.csv criado.")
print(f"Total processados: {len(resultados)}")
