import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import gerar_site
from validar_catalogo_publico import ErroCatalogoPublico, validar_catalogo


class ErroGeracaoPublica(RuntimeError):
    pass


def _configurar_destino(destino):
    destino = Path(destino).expanduser().resolve()
    gerar_site.SITE_DIR = destino
    gerar_site.INDEX_PATH = destino / "index.html"
    gerar_site.STYLE_PATH = destino / "style.css"
    gerar_site.SCRIPT_PATH = destino / "app.js"
    gerar_site.FAVICON_PATH = destino / "favicon.svg"
    gerar_site.FAVICON_ICO_PATH = destino / "favicon.ico"
    gerar_site.LOGO_SVG_PATH = destino / "logo.svg"
    gerar_site.LOGO_PNG_PATH = destino / "logo.png"
    gerar_site.OFERTAS_PATH = destino / "ofertas.json"
    gerar_site.ASSISTENTE_DADOS_PATH = destino / "assistente_dados.json"
    gerar_site.ASSISTENTE_DIR = destino / "assistente"
    gerar_site.PRODUTOS_DIR = destino / "produto"
    gerar_site.CATEGORIAS_DIR = destino / "categoria"
    gerar_site.SITEMAP_PATH = destino / "sitemap.xml"
    gerar_site.ROBOTS_PATH = destino / "robots.txt"
    gerar_site.NOT_FOUND_PATH = destino / "404.html"
    gerar_site.OG_IMAGE_PATH = destino / "og-promogg.svg"
    gerar_site.SOBRE_DIR = destino / "sobre"
    gerar_site.SEGURANCA_DIR = destino / "seguranca"
    gerar_site.OAUTH_CALLBACK_DIR = destino / "oauth" / "callback"
    return destino


def _desativar_dependencias_operacionais():
    gerar_site.registrar_log = lambda *args, **kwargs: None
    gerar_site.registrar_evento_sistema = lambda *args, **kwargs: None
    gerar_site.obter_estado_sistema = lambda: {"estado": "ONLINE", "atualizado_em": "", "motivo": "geracao estatica"}


def _carregar_catalogo_publico(fonte):
    try:
        total = validar_catalogo(fonte)
    except ErroCatalogoPublico as erro:
        raise ErroGeracaoPublica(f"catálogo público inválido: {erro}") from erro
    if total <= 0:
        raise ErroGeracaoPublica("catálogo público não possui ofertas")

    try:
        dados = json.loads(Path(fonte).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise ErroGeracaoPublica(f"não foi possível ler {fonte}: {erro}") from erro
    return dados


def _oferta_para_renderizacao(oferta, indice):
    item_id = str(oferta.get("item_id") or "").strip().upper()
    if not item_id:
        raise ErroGeracaoPublica(f"oferta {indice}: item_id ausente")
    preparada = dict(oferta)
    preparada["_item_id"] = item_id
    preparada["_produto_id"] = indice
    preparada["item_id"] = item_id
    preparada.setdefault("menor_preco", preparada.get("preco"))
    preparada.setdefault("menor_preco_formatado", preparada.get("preco_formatado"))
    preparada.setdefault("variacao_preco", 0)
    preparada.setdefault("destaque_menor_preco", False)
    preparada.setdefault("categoria_caminho", preparada.get("categoria"))
    preparada.setdefault("plataforma", "Mercado Livre")
    return preparada


def _historico_estatico(oferta):
    registros = []
    data = oferta.get("ultima_verificacao") or oferta.get("data_publicacao") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    preco = oferta.get("preco")
    menor = oferta.get("menor_preco") or preco
    if preco:
        registros.append({"preco": preco, "data_verificacao": data})
    menor_historico = {"preco": menor, "data_verificacao": data} if menor else None
    return registros, menor_historico


def _instalar_historico_estatico(ofertas):
    por_produto = {oferta["_produto_id"]: oferta for oferta in ofertas}

    def historico_publico_produto(produto_id, limite=10):
        oferta = por_produto.get(produto_id)
        if not oferta:
            return [], None
        registros, menor = _historico_estatico(oferta)
        return registros[:limite], menor

    gerar_site.historico_publico_produto = historico_publico_produto


def _criar_cname(destino, dominio):
    cname = destino / "CNAME"
    dominio = str(dominio or "").strip().removeprefix("https://").removeprefix("http://").strip("/")
    if dominio:
        cname.write_text(f"{dominio}\n", encoding="utf-8")
    elif cname.exists():
        cname.unlink()


def gerar_site_publico(fonte, destino, dominio=""):
    dados = _carregar_catalogo_publico(fonte)
    ofertas = [_oferta_para_renderizacao(oferta, indice) for indice, oferta in enumerate(dados["ofertas"], start=1)]
    if not ofertas:
        raise ErroGeracaoPublica("catálogo público não possui ofertas")

    destino = _configurar_destino(destino)
    _desativar_dependencias_operacionais()
    _instalar_historico_estatico(ofertas)

    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True, exist_ok=True)

    ofertas_validas, falhas_paginas = gerar_site.gerar_paginas_produtos(ofertas)
    if falhas_paginas:
        amostra = "; ".join(f"{falha['item_id']}: {falha['motivo']}" for falha in falhas_paginas[:3])
        raise ErroGeracaoPublica(f"falha ao gerar páginas de produto: {amostra}")

    categorias = gerar_site.gerar_paginas_categorias(ofertas_validas)
    gerar_site.OFERTAS_PATH.write_text(json.dumps({
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "plataforma": dados.get("plataforma", "mercado_livre"),
        "total": len(ofertas_validas),
        "ofertas": [gerar_site.oferta_publica(oferta) for oferta in ofertas_validas],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gerar_site.escrever_dados_assistente(ofertas_validas)
    gerar_site.escrever_css()
    gerar_site.escrever_javascript()
    gerar_site.escrever_favicon()
    gerar_site.escrever_identidade()
    gerar_site.escrever_imagem_social()
    gerar_site.INDEX_PATH.write_text(gerar_site.montar_index(ofertas_validas), encoding="utf-8")
    gerar_site.gerar_paginas_institucionais()
    gerar_site.gerar_pagina_assistente()
    gerar_site.gerar_callback_oauth()
    gerar_site.gerar_sitemap(ofertas_validas, categorias)
    gerar_site.gerar_robots()
    gerar_site.gerar_404(categorias)
    _criar_cname(destino, dominio)

    try:
        total_validado = validar_catalogo(destino / "ofertas.json")
    except ErroCatalogoPublico as erro:
        raise ErroGeracaoPublica(f"site gerado contém catálogo inválido: {erro}") from erro
    return {"destino": destino, "ofertas": total_validado, "categorias": len(categorias)}


def main():
    parser = argparse.ArgumentParser(description="Gera o site público estático do Promogg a partir do catálogo sanitizado")
    parser.add_argument("--fonte", default="catalogo_publico/ofertas.json")
    parser.add_argument("--destino", default="dist_site")
    parser.add_argument("--dominio", default="")
    args = parser.parse_args()

    try:
        resultado = gerar_site_publico(args.fonte, args.destino, args.dominio)
    except ErroGeracaoPublica as erro:
        print(f"Erro na geração pública: {erro}")
        return 1

    print(f"Site público gerado em: {resultado['destino']}")
    print(f"Ofertas: {resultado['ofertas']}")
    print(f"Categorias: {resultado['categorias']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
