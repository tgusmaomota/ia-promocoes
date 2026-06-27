import argparse
import json
import re
from pathlib import Path


DESTINO_PADRAO = Path("catalogo_publico") / "ofertas.json"
FONTE_PADRAO = Path("dist_site") / "ofertas.json"

CAMPOS_PUBLICOS = (
    "oferta_id",
    "item_id",
    "titulo",
    "preco",
    "preco_formatado",
    "preco_original",
    "desconto_percentual",
    "economia_valor",
    "menor_preco",
    "menor_preco_formatado",
    "variacao_preco",
    "destaque_menor_preco",
    "categoria",
    "categoria_caminho",
    "link",
    "imagem_url",
    "plataforma",
    "produto_url",
    "data_publicacao",
    "ultima_verificacao",
    "maior_preco",
    "preco_medio",
    "selo_mais_vendido",
    "selo_loja_oficial",
)

CAMPOS_OBRIGATORIOS = (
    "oferta_id",
    "item_id",
    "titulo",
    "preco",
    "preco_formatado",
    "categoria",
    "link",
    "imagem_url",
    "plataforma",
    "produto_url",
)

PADRAO_SENSIVEL = re.compile(
    r"(token|cookie|senha|password|secret|api[_-]?key|authorization|session)",
    re.IGNORECASE,
)
PADRAO_VALOR_SENSIVEL = re.compile(
    r"(bearer\s+[a-z0-9._-]+|(?:token|cookie|senha|password|secret|api[_-]?key|authorization|session)\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


class ErroCatalogoPublico(ValueError):
    pass


def _carregar_json(caminho):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise ErroCatalogoPublico(f"JSON inválido ou indisponível em {caminho}: {erro}") from erro


def _validar_sem_sensivel(valor, caminho="raiz"):
    if isinstance(valor, dict):
        for chave, item in valor.items():
            if PADRAO_SENSIVEL.search(str(chave)):
                raise ErroCatalogoPublico(f"campo sensível detectado em {caminho}.{chave}")
            _validar_sem_sensivel(item, f"{caminho}.{chave}")
    elif isinstance(valor, list):
        for indice, item in enumerate(valor):
            _validar_sem_sensivel(item, f"{caminho}[{indice}]")
    elif isinstance(valor, str) and PADRAO_VALOR_SENSIVEL.search(valor):
        raise ErroCatalogoPublico(f"valor sensível detectado em {caminho}")


def sanitizar_catalogo(fonte=FONTE_PADRAO, destino=DESTINO_PADRAO):
    dados = _carregar_json(fonte)
    ofertas = dados.get("ofertas")
    if not isinstance(ofertas, list) or not ofertas:
        raise ErroCatalogoPublico("fonte não possui lista de ofertas pública e não vazia")

    ofertas_publicas = []
    for indice, oferta in enumerate(ofertas, start=1):
        if not isinstance(oferta, dict):
            raise ErroCatalogoPublico(f"oferta {indice}: item não é objeto JSON")
        publica = {campo: oferta.get(campo) for campo in CAMPOS_PUBLICOS if campo in oferta}
        ofertas_publicas.append(publica)

    catalogo = {
        "gerado_em": dados.get("gerado_em"),
        "plataforma": dados.get("plataforma", "mercado_livre"),
        "total": len(ofertas_publicas),
        "ofertas": ofertas_publicas,
    }
    validar_catalogo(catalogo=catalogo)

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino, len(ofertas_publicas)


def validar_catalogo(caminho=DESTINO_PADRAO, catalogo=None):
    dados = catalogo if catalogo is not None else _carregar_json(caminho)
    _validar_sem_sensivel(dados)

    ofertas = dados.get("ofertas")
    if not isinstance(ofertas, list):
        raise ErroCatalogoPublico("campo ofertas não é uma lista")
    if not ofertas:
        raise ErroCatalogoPublico("catálogo público não possui ofertas")

    for indice, oferta in enumerate(ofertas, start=1):
        if not isinstance(oferta, dict):
            raise ErroCatalogoPublico(f"oferta {indice}: item não é objeto JSON")
        extras = sorted(set(oferta) - set(CAMPOS_PUBLICOS))
        if extras:
            raise ErroCatalogoPublico(f"oferta {indice}: campos não permitidos: {', '.join(extras)}")
        faltantes = [campo for campo in CAMPOS_OBRIGATORIOS if campo not in oferta or oferta.get(campo) in ("", None)]
        if faltantes:
            raise ErroCatalogoPublico(f"oferta {indice}: campos obrigatórios ausentes: {', '.join(faltantes)}")
        try:
            if float(oferta.get("preco")) <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ErroCatalogoPublico(f"oferta {indice}: preço inválido") from None
        link = str(oferta.get("link") or "")
        if not link.startswith("https://meli.la/"):
            raise ErroCatalogoPublico(f"oferta {indice}: link público inválido")
        imagem = str(oferta.get("imagem_url") or "")
        if not imagem.startswith(("https://", "http://")):
            raise ErroCatalogoPublico(f"oferta {indice}: imagem pública inválida")
        produto_url = str(oferta.get("produto_url") or "").strip("/")
        if not produto_url or ".." in produto_url:
            raise ErroCatalogoPublico(f"oferta {indice}: produto_url inválido")

    total = dados.get("total")
    if total is not None:
        try:
            total_int = int(total)
        except (TypeError, ValueError):
            raise ErroCatalogoPublico(f"total inválido: {total}") from None
        if total_int != len(ofertas):
            raise ErroCatalogoPublico(f"total inconsistente: total={total} ofertas={len(ofertas)}")
    return len(ofertas)


def main():
    parser = argparse.ArgumentParser(description="Gera e valida o catálogo público sanitizado do Promogg")
    parser.add_argument("--gerar", action="store_true", help="Gera catalogo_publico/ofertas.json a partir de dist_site/ofertas.json")
    parser.add_argument("--fonte", default=str(FONTE_PADRAO))
    parser.add_argument("--arquivo", default=str(DESTINO_PADRAO))
    args = parser.parse_args()

    try:
        if args.gerar:
            destino, total = sanitizar_catalogo(args.fonte, args.arquivo)
            print(f"Catálogo público gerado: {destino} ({total} ofertas)")
        total = validar_catalogo(args.arquivo)
    except ErroCatalogoPublico as erro:
        print(f"Catálogo público inválido: {erro}")
        return 1

    print(f"Catálogo público válido: {total} ofertas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
