"""Auditoria de consistência entre catálogo público e páginas estáticas."""

import json
from datetime import datetime
from pathlib import Path

from gerar_site import OFERTAS_PATH, PRODUTOS_DIR, SITE_DIR, listar_ofertas


RELATORIO = Path("RELATORIO_INTEGRIDADE_SITE.md")


def auditar_paginas_produto():
    try:
        dados = json.loads(OFERTAS_PATH.read_text(encoding="utf-8"))
        ofertas = dados.get("ofertas", [])
    except (OSError, json.JSONDecodeError) as erro:
        return {"erros": [f"ofertas.json inválido: {erro}"], "ofertas": [], "paginas": []}
    esperadas = {str(oferta.get("produto_url") or "").strip("/") for oferta in ofertas}
    esperadas.discard("")
    paginas = {str(caminho.relative_to(SITE_DIR).parent) for caminho in PRODUTOS_DIR.glob("*/*/index.html")}
    sem_pagina = sorted(esperadas - paginas)
    orfas = sorted(paginas - esperadas)
    brutas = listar_ofertas(deduplicar=False)
    por_item = {}
    por_slug = {}
    for oferta in brutas:
        por_item.setdefault(oferta["_item_id"], []).append(oferta)
        por_slug.setdefault(oferta["produto_url"], []).append(oferta)
    duplicados_item = {chave: itens for chave, itens in por_item.items() if len(itens) > 1}
    duplicados_slug = {chave: itens for chave, itens in por_slug.items() if len(itens) > 1}
    resultado = {
        "ofertas": ofertas, "paginas": sorted(paginas), "sem_pagina": sem_pagina, "orfas": orfas,
        "duplicados_item": duplicados_item, "duplicados_slug": duplicados_slug,
        "erros": [],
    }
    if sem_pagina:
        resultado["erros"].append(f"{len(sem_pagina)} oferta(s) pública(s) sem página individual")
    if orfas:
        resultado["erros"].append(f"{len(orfas)} página(s) órfã(s)")
    _escrever_relatorio(resultado)
    return resultado


def _escrever_relatorio(resultado, acao="auditoria"):
    linhas = [
        "# Relatório de Integridade do Site", "",
        f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Operação: {acao}",
        f"- Total de ofertas públicas: {len(resultado['ofertas'])}",
        f"- Total de páginas individuais: {len(resultado['paginas'])}",
        f"- Ofertas sem página: {len(resultado['sem_pagina'])}",
        f"- Páginas órfãs: {len(resultado['orfas'])}",
        f"- Item_id duplicados na fonte: {len(resultado['duplicados_item'])}",
        f"- Slugs duplicados na fonte: {len(resultado['duplicados_slug'])}", "",
        "## Causa provável", "",
        "- Ofertas repetidas por item_id eram incluídas no catálogo, enquanto a geração criava uma única pasta por item.",
        "- A geração atual deduplica por item_id e só inclui no catálogo ofertas cuja página index.html foi escrita e validada.", "",
        "## Ofertas sem página",
    ]
    linhas.extend(f"- {caminho}" for caminho in resultado["sem_pagina"]) or linhas.append("- nenhuma")
    linhas += ["", "## Páginas órfãs"]
    linhas.extend(f"- {caminho}" for caminho in resultado["orfas"]) or linhas.append("- nenhuma")
    linhas += ["", "## Duplicidades por item_id"]
    for item_id, itens in list(resultado["duplicados_item"].items())[:50]:
        linhas.append(f"- {item_id}: {len(itens)} ocorrência(s); mantida a primeira conforme ordenação pública")
    if not resultado["duplicados_item"]:
        linhas.append("- nenhuma")
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def corrigir_paginas_produto():
    from gerar_site import gerar_site

    geracao = gerar_site()
    resultado = auditar_paginas_produto()
    _escrever_relatorio(resultado, acao="correção e regeneração")
    return {"geracao": geracao, "auditoria": resultado}
