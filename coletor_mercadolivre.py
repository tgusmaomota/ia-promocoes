from datetime import datetime

from agente_ofertas import coletar_ofertas
from banco import registrar_evento_sistema, registrar_log, salvar_ou_atualizar_produto_api
from gerador_link_mercadolivre import gerar_link_afiliado
from mercadolivre_api import ErroMercadoLivre, consultar_item
from saneamento_ofertas import sanear_titulo


def enriquecer_categoria_mercado_livre(produto):
    item_id = str(produto.get("item_id", "")).strip()
    dados = {"categoria_id": "", "categoria_nome": ""}
    if not item_id:
        return dados

    try:
        item = consultar_item(item_id)
    except ErroMercadoLivre as erro:
        registrar_log(
            "coletor_mercadolivre",
            f"Categoria não consultada para {item_id}: {erro}",
            nivel="warning",
        )
        return dados

    if not item.get("disponivel"):
        return dados

    return {
        "categoria_id": item.get("categoria_id", ""),
        "categoria_nome": item.get("categoria_nome", ""),
    }


def normalizar_produto(produto):
    link_original = str(produto.get("link", "")).strip()
    link_afiliado = gerar_link_afiliado(link_original)
    categoria = enriquecer_categoria_mercado_livre(produto)
    categoria_nome = categoria["categoria_nome"] or produto.get("categoria", "ofertas")

    preco_atual = produto.get("preco", 0)
    saneado = sanear_titulo(
        produto.get("titulo", ""), preco_atual,
        produto.get("preco_original") or produto.get("preco_anterior"),
        produto.get("desconto"),
    )
    return {
        "titulo": saneado["titulo"],
        "preco_atual": preco_atual,
        "preco_anterior": produto.get("preco_anterior"),
        "link_original": link_original,
        "link_afiliado": link_afiliado,
        "item_id": produto.get("item_id", ""),
        "plataforma": "mercado_livre",
        "categoria": categoria_nome,
        "categoria_id": categoria["categoria_id"],
        "categoria_nome": categoria["categoria_nome"],
        "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "coletado",
        "desconto": saneado["desconto_percentual"] or produto.get("desconto", 0),
        "preco_original": saneado["preco_original"],
        "desconto_percentual": saneado["desconto_percentual"],
        "economia_valor": saneado["economia_valor"],
        "imagem": produto.get("imagem", ""),
        "estoque": 1,
        "tipo_promocao": produto.get("tipo_promocao", ""),
        "origem_coleta": produto.get("origem_coleta", "playwright"),
    }


def _modo_coleta():
    import os

    modo = os.getenv("MELI_COLETA_MODO", "auto").strip().lower()
    return modo if modo in {"api", "playwright", "auto"} else "auto"


def _coletar_api():
    from coletor_mercadolivre_api import coletar_ofertas_api

    produtos = coletar_ofertas_api()
    registrar_log("coletor_mercadolivre", f"Coleta API concluída: candidatos={len(produtos)}")
    return produtos


def _coletar_playwright():
    from playwright_perfil import PERFIL_PRINCIPAL, PERFIL_RESERVA, criar_perfil_reserva

    produtos = coletar_ofertas(str(PERFIL_PRINCIPAL))
    origem = "playwright_principal"
    if not produtos:
        try:
            reserva = PERFIL_RESERVA if PERFIL_RESERVA.exists() else criar_perfil_reserva()
            produtos = coletar_ofertas(str(reserva))
            origem = "playwright_reserva"
        except Exception as erro:
            registrar_log("coletor_mercadolivre", f"Perfil reserva indisponível: {erro}", nivel="warning")
    registrar_log("coletor_mercadolivre", f"Coleta Playwright concluída: origem={origem} candidatos={len(produtos)}")
    return produtos


def coletar(salvar_no_banco=True):
    registrar_log("coletor_mercadolivre", "Iniciando coleta Mercado Livre")
    registrar_evento_sistema("coleta", "mercado_livre", "iniciado", "Coleta Mercado Livre iniciada")
    modo = _modo_coleta()
    origem = "playwright"
    try:
        if modo == "playwright":
            produtos = _coletar_playwright()
        elif modo == "auto":
            from coletor_mercadolivre_api import busca_api_bloqueada

            if busca_api_bloqueada():
                produtos = _coletar_playwright()
                origem = "playwright_cache_api_403"
            else:
                try:
                    produtos = _coletar_api()
                    origem = "api"
                    if not produtos:
                        raise RuntimeError("API não retornou candidatos utilizáveis")
                except Exception as erro_api:
                    # O 403 de busca já foi registrado pela camada API. O fallback é normal.
                    if "HTTP 403" not in str(erro_api) and "cache de indisponibilidade" not in str(erro_api):
                        registrar_log("coletor_mercadolivre", f"Falha na coleta API: {erro_api}", nivel="warning")
                    produtos = _coletar_playwright()
                    origem = "playwright_fallback"
        else:
            try:
                produtos = _coletar_api()
                origem = "api"
                if not produtos:
                    raise RuntimeError("API não retornou candidatos utilizáveis")
            except Exception as erro_api:
                registrar_log("coletor_mercadolivre", f"Falha na coleta API: {erro_api}", nivel="error")
                registrar_evento_sistema("coleta_api", "mercado_livre", "erro", "API sem candidatos; usando fallback Playwright", str(erro_api))
                raise
        if not produtos:
            raise RuntimeError("nenhum candidato retornado pela coleta")
    except Exception as erro:
        registrar_evento_sistema("coleta", "mercado_livre", "erro", "Falha na coleta Mercado Livre", str(erro))
        raise
    normalizados = [normalizar_produto(produto) for produto in produtos]
    salvos = 0
    rejeitados = 0

    if salvar_no_banco:
        itens_processados = set()
        for produto in normalizados:
            chave = str(produto.get("item_id") or produto.get("link_original") or "").strip()
            if chave and chave in itens_processados:
                registrar_log("deduplicacao", f"Produto repetido na mesma coleta ignorado: {chave}")
                continue
            if chave:
                itens_processados.add(chave)
            try:
                # A mesma atualização idempotente é usada para API e
                # Playwright: um item reencontrado atualiza preço/dados e
                # acrescenta histórico quando necessário, sem duplicá-lo.
                produto["origem_coleta"] = origem
                resultado = salvar_ou_atualizar_produto_api(produto)
                ok = resultado["acao"] in {"criado", "atualizado"}
                motivo = resultado.get("criterio", "")
            except Exception as erro:
                rejeitados += 1
                registrar_log("coletor_mercadolivre", f"Falha ao salvar produto: {produto['titulo']} ({erro})", nivel="error")
                continue
            if ok:
                salvos += 1
            else:
                rejeitados += 1
                registrar_log(
                    "coletor_mercadolivre",
                    f"Produto rejeitado: {produto['titulo']} ({motivo})",
                )

    registrar_log(
        "coletor_mercadolivre",
        f"Coleta finalizada. origem={origem} coletados={len(normalizados)} salvos={salvos} rejeitados={rejeitados}",
    )
    registrar_evento_sistema(
        "coleta", "mercado_livre", "concluido", "Coleta Mercado Livre concluída",
        f"origem={origem} coletados={len(normalizados)} salvos={salvos} rejeitados={rejeitados}",
    )
    return normalizados


if __name__ == "__main__":
    coletar()
