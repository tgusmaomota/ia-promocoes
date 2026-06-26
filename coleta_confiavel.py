"""Coleta conservadora: confirma e persiste uma oferta por vez."""

import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from agente_ofertas import extrair_preco, identificar_tipo_promocao, montar_urls_ofertas
from analisador_promocao import analisar_produto
from banco import conectar, registrar_log, salvar_ou_atualizar_produto_api
from fila_postagens import gerar_fila_de_produtos
from gerador_afiliados_oficial import gerar_link_oficial_na_pagina
from gerador_link_mercadolivre import link_afiliado_valido
from item_utils import extrair_item_id
from mercadolivre_api import ErroMercadoLivre, consultar_item, item_id_valido
from playwright_perfil import (
    PERFIL_PRINCIPAL,
    PERFIL_RESERVA,
    LoginNecessario,
    abrir_contexto_persistente,
    login_necessario_na_pagina,
)
from saneamento_ofertas import sanear_titulo
from enriquecimento_pagina_ml import extrair_sinais_comerciais
from captura_hibrida import captura_hibrida_ativa, capturar_produto_hibrido


CHECKPOINT = Path(".coleta_confiavel_checkpoint.json")
RELATORIO = Path("RELATORIO_COLETA_CONFIAVEL.md")


def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _salvar_checkpoint(**dados):
    CHECKPOINT.write_text(json.dumps({"atualizado_em": _agora(), **dados}, ensure_ascii=False, indent=2), encoding="utf-8")


def _limpar_checkpoint():
    CHECKPOINT.unlink(missing_ok=True)


def _carregar_checkpoint():
    try:
        return json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _publica(url):
    partes = urlparse(str(url or ""))
    return partes.scheme == "https" and bool(partes.netloc)


def _preco_pagina(pagina):
    for seletor in ('meta[itemprop="price"]', 'meta[property="product:price:amount"]'):
        try:
            valor = pagina.locator(seletor).first.get_attribute("content")
            preco = float(str(valor).replace(",", "."))
            if preco > 0:
                return preco
        except Exception:
            continue
    try:
        return float(extrair_preco(pagina.inner_text("body", timeout=12000)))
    except Exception:
        return 0.0


def _titulo_pagina(pagina):
    for seletor in ('meta[property="og:title"]', 'h1'):
        try:
            elemento = pagina.locator(seletor).first
            valor = elemento.get_attribute("content") if seletor.startswith("meta") else elemento.inner_text()
            if str(valor or "").strip():
                return str(valor).strip()
        except Exception:
            continue
    return ""


def _imagem_pagina(pagina):
    for seletor in ('meta[property="og:image"]', 'img[data-zoom]'):
        try:
            elemento = pagina.locator(seletor).first
            valor = elemento.get_attribute("content") if seletor.startswith("meta") else (elemento.get_attribute("data-zoom") or elemento.get_attribute("src"))
            if _publica(valor):
                return str(valor).strip()
        except Exception:
            continue
    return ""


def _detalhar_produto_legado(pagina, candidato, visual=False):
    permalink = str(candidato["permalink"]).strip()
    pagina.goto(permalink, wait_until="domcontentloaded", timeout=45000)
    pagina.wait_for_timeout(2500 if visual else 1200)
    if login_necessario_na_pagina(pagina):
        raise LoginNecessario("sessão Mercado Livre não autenticada na página do produto")
    url_atual = pagina.url
    item_id = extrair_item_id(url_atual) or extrair_item_id(pagina.content())
    titulo = _titulo_pagina(pagina) or candidato["titulo"]
    preco = _preco_pagina(pagina)
    imagem = _imagem_pagina(pagina)
    if not item_id_valido(item_id):
        raise ValueError("item_id ausente ou inválido")
    if not titulo or preco <= 0 or not imagem:
        raise ValueError("dados essenciais incompletos (título, preço ou imagem)")

    sinais = extrair_sinais_comerciais(pagina)
    categoria_id = ""
    categoria_nome = sinais.get("categoria_nome", "")
    origem_categoria = sinais.get("origem_categoria", "")
    try:
        api = consultar_item(item_id)
        if api.get("disponivel"):
            categoria_id = api.get("categoria_id", "")
            categoria_nome = api.get("categoria_nome", "") or categoria_nome
            if api.get("categoria_nome"):
                origem_categoria = "api_oficial"
            imagem = api.get("imagem_url") or imagem
    except ErroMercadoLivre:
        pass

    link_afiliado = gerar_link_oficial_na_pagina(pagina, permalink, navegar=False)
    if not link_afiliado_valido(link_afiliado):
        raise ValueError("portal não retornou link afiliado oficial meli.la")
    preco_original = sinais.get("preco_original_visivel") or candidato.get("preco_original")
    desconto_visivel = sinais.get("percentual_off") or candidato.get("desconto", 0)
    saneado = sanear_titulo(titulo, preco, preco_original, desconto_visivel)
    return {
        "item_id": item_id,
        "titulo": saneado["titulo"],
        "preco": preco,
        "preco_atual": preco,
        "preco_anterior": candidato.get("preco_anterior"),
        "link_original": permalink,
        "link_afiliado": link_afiliado,
        "imagem": imagem,
        "categoria_id": categoria_id,
        "categoria_nome": categoria_nome,
        "categoria": categoria_nome or "ofertas",
        "origem_categoria": origem_categoria,
        "plataforma": "mercado_livre",
        "desconto": saneado["desconto_percentual"] or candidato.get("desconto", 0),
        "percentual_off": sinais.get("percentual_off"),
        "preco_original": saneado["preco_original"],
        "desconto_percentual": saneado["desconto_percentual"],
        "economia_valor": saneado["economia_valor"],
        "tipo_promocao": candidato.get("tipo_promocao", ""),
        "data_coleta": _agora(),
        "status": "coletado",
        **sinais,
    }


def _detalhar_produto(pagina, candidato, visual=False):
    if captura_hibrida_ativa():
        resultado = capturar_produto_hibrido(pagina, candidato, visual=visual)
        if not resultado["completo"]:
            raise ValueError("captura híbrida incompleta: " + ", ".join(resultado["campos_faltantes"]))
        return resultado["produto"]
    return _detalhar_produto_legado(pagina, candidato, visual)


def _candidatos_da_pagina(pagina):
    candidatos = []
    vistos = set()
    for card in pagina.locator("div.andes-card").all():
        try:
            texto = card.inner_text(timeout=12000)
            links = card.locator("a").all()
            permalink = ""
            titulo = ""
            for link in links:
                href = link.get_attribute("href") or ""
                if "mercadolivre.com.br" in href:
                    permalink = href
                    titulo = link.inner_text().strip()
                    break
            item_id = extrair_item_id(permalink)
            if not permalink or not item_id or item_id in vistos:
                continue
            vistos.add(item_id)
            candidatos.append({
                "permalink": permalink,
                "titulo": titulo,
                "item_id": item_id,
                "desconto": 0,
                "tipo_promocao": identificar_tipo_promocao(texto),
            })
        except Exception:
            continue
    return candidatos


def _config_float(nome, padrao):
    try:
        return float(os.getenv(nome, str(padrao)).replace(",", "."))
    except (TypeError, ValueError):
        return float(padrao)


def _config_int(nome, padrao, minimo=1, maximo=100):
    try:
        valor = int(os.getenv(nome, str(padrao)))
    except (TypeError, ValueError):
        valor = int(padrao)
    return max(minimo, min(maximo, valor))


def _pausa_produto():
    minimo = _config_float("PLAYWRIGHT_PAUSA_MIN", 1.5)
    maximo = max(minimo, _config_float("PLAYWRIGHT_PAUSA_MAX", 4.0))
    time.sleep(random.uniform(minimo, maximo))


def _pausa_lote():
    minimo = _config_float("PLAYWRIGHT_PAUSA_LOTE_MIN", 20)
    maximo = max(minimo, _config_float("PLAYWRIGHT_PAUSA_LOTE_MAX", 45))
    time.sleep(random.uniform(minimo, maximo))


def _relatorio(resultado):
    linhas = [
        "# Relatório de Coleta Confiável - Promogg", "",
        f"- Início: {resultado['inicio']}",
        f"- Fim: {_agora()}",
        f"- Tempo total (s): {round(time.time() - resultado['inicio_epoch'], 1)}",
        f"- Encontrados: {resultado['encontrados']}",
        f"- Capturados completos: {resultado['completos']}",
        f"- Salvos/atualizados: {resultado['salvos']}",
        f"- Com meli.la: {resultado['afiliados']}",
        f"- Aprovados: {resultado['aprovados']}",
        f"- Pendentes: {resultado['pendentes']}",
        f"- Rejeitados: {resultado['rejeitados']}",
        f"- Falhas: {len(resultado['falhas'])}",
        "", "## Motivos de falha",
    ]
    linhas += [f"- {motivo}" for motivo in resultado["falhas"]] or ["- nenhum"]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def coletar_confiavel(visual=False, retomar=True):
    """Executa coleta lenta em lotes, com checkpoint e retomada segura."""
    inicio = time.time()
    resultado = {
        "inicio": _agora(), "inicio_epoch": inicio, "encontrados": 0, "completos": 0,
        "salvos": 0, "afiliados": 0, "aprovados": 0, "pendentes": 0,
        "rejeitados": 0, "falhas": [],
    }
    checkpoint = _carregar_checkpoint() if retomar else {}
    pagina_inicial = int(checkpoint.get("pagina", 1))
    indice_inicial = int(checkpoint.get("indice", 0))

    tamanho_lote = _config_int("PLAYWRIGHT_LOTE_TAMANHO", 25, minimo=1, maximo=30)
    processados_lote = 0

    with sync_playwright() as playwright:
        navegador = None
        lista = None
        try:
            for numero, url in enumerate(montar_urls_ofertas(), start=1):
                if numero < pagina_inicial:
                    continue
                if navegador is None:
                    navegador = abrir_contexto_persistente(playwright, visual=visual)
                    lista = navegador.new_page()
                    lista.set_default_timeout(12000)
                try:
                    _salvar_checkpoint(pagina=numero, indice=0, item_id="", url=url, etapa="listando", motivo="andamento")
                    lista.goto(url, wait_until="domcontentloaded", timeout=45000)
                    lista.wait_for_timeout(3500 if visual else 1500)
                    if login_necessario_na_pagina(lista):
                        raise LoginNecessario("sessão Mercado Livre não autenticada na listagem")
                    candidatos = _candidatos_da_pagina(lista)
                except LoginNecessario as erro:
                    _salvar_checkpoint(pagina=numero, indice=0, item_id="", url=url, etapa="login_necessario", motivo=str(erro))
                    registrar_evento_sistema("playwright", "mercado_livre", "login_necessario", "Login Mercado Livre necessário", str(erro))
                    registrar_log("coleta_confiavel", "Login necessário; coleta pausada com checkpoint preservado.", nivel="warning")
                    raise
                except Exception as erro:
                    resultado["falhas"].append(f"página {numero}: {erro}")
                    continue
                resultado["encontrados"] += len(candidatos)
                inicio_indice = indice_inicial if numero == pagina_inicial else 0
                for indice, candidato in enumerate(candidatos):
                    if indice < inicio_indice:
                        continue
                    if processados_lote >= tamanho_lote:
                        navegador.close()
                        navegador = None
                        lista = None
                        processados_lote = 0
                        _salvar_checkpoint(pagina=numero, indice=indice, item_id=candidato["item_id"], url=candidato["permalink"], etapa="pausa_lote", motivo="limite_de_lote")
                        _pausa_lote()
                        navegador = abrir_contexto_persistente(playwright, visual=visual)
                        lista = navegador.new_page()
                        lista.set_default_timeout(12000)

                    _salvar_checkpoint(pagina=numero, indice=indice, item_id=candidato["item_id"], url=candidato["permalink"], etapa="iniciando", motivo="andamento")
                    produto = None
                    erro_final = None
                    for tentativa in range(1, 3):
                        pagina_produto = navegador.new_page()
                        pagina_produto.set_default_timeout(12000)
                        try:
                            _salvar_checkpoint(pagina=numero, indice=indice, item_id=candidato["item_id"], url=candidato["permalink"], etapa=f"tentativa_{tentativa}", motivo="andamento")
                            produto = _detalhar_produto(pagina_produto, candidato, visual)
                            if login_necessario_na_pagina(pagina_produto):
                                raise LoginNecessario("sessão Mercado Livre não autenticada após abrir produto")
                            break
                        except LoginNecessario as erro:
                            _salvar_checkpoint(pagina=numero, indice=indice, item_id=candidato["item_id"], url=candidato["permalink"], etapa="login_necessario", motivo=str(erro))
                            registrar_evento_sistema("playwright", "mercado_livre", "login_necessario", "Login Mercado Livre necessário", str(erro))
                            raise
                        except Exception as erro:
                            erro_final = erro
                        finally:
                            pagina_produto.close()
                    if not produto:
                        resultado["falhas"].append(f"{candidato['item_id']}: {erro_final}")
                        registrar_log("coleta_confiavel", f"Produto pulado {candidato['item_id']}: {erro_final}", nivel="warning")
                        continue
                    resultado["completos"] += 1
                    salvo = salvar_ou_atualizar_produto_api(produto)
                    resultado["salvos"] += 1
                    resultado["afiliados"] += 1
                    processados_lote += 1
                    with conectar() as conn:
                        linha = conn.execute("SELECT * FROM produtos WHERE id = ?", (salvo["produto_id"],)).fetchone()
                    fila = gerar_fila_de_produtos([dict(linha)])
                    resultado["aprovados"] += fila["aprovados"]
                    with conectar() as conn:
                        postagem = conn.execute(
                            "SELECT status FROM postagens WHERE produto_id = ? ORDER BY id DESC LIMIT 1",
                            (salvo["produto_id"],),
                        ).fetchone()
                    if postagem and postagem["status"] == "pendente_revisao":
                        resultado["pendentes"] += 1
                    elif postagem and postagem["status"] == "rejeitado":
                        resultado["rejeitados"] += 1
                    _salvar_checkpoint(pagina=numero, indice=indice + 1, item_id=produto["item_id"], url=candidato["permalink"], etapa="salvo", motivo="andamento")
                    _pausa_produto()
            _limpar_checkpoint()
        finally:
            if navegador:
                navegador.close()
    _relatorio(resultado)
    return resultado
