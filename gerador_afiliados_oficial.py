"""Geração de links oficiais meli.la pelo botão Compartilhar do Mercado Livre."""

import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from banco import atualizar_link_afiliado_oficial, conectar, inicializar_banco, registrar_evento_sistema, registrar_log
from gerador_link_mercadolivre import link_afiliado_valido
from playwright_perfil import (
    PERFIL_PRINCIPAL,
    PERFIL_RESERVA,
    LoginNecessario,
    abrir_contexto_persistente,
    login_necessario_na_pagina,
)


MELI_LINK_RE = re.compile(r"https://meli\.la/[A-Za-z0-9]+")
PASTA_DIAGNOSTICO = Path("logs") / "afiliados"
CHECKPOINT_AFILIADOS = Path(".afiliados_checkpoint.json")


def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _salvar_checkpoint(**dados):
    CHECKPOINT_AFILIADOS.write_text(
        json.dumps({"atualizado_em": _agora(), **dados}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _carregar_checkpoint():
    try:
        return json.loads(CHECKPOINT_AFILIADOS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _limpar_checkpoint():
    CHECKPOINT_AFILIADOS.unlink(missing_ok=True)


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


def produtos_sem_afiliado(limite=None):
    inicializar_banco()
    consulta = """
        SELECT id, item_id, titulo, link_original
        FROM produtos
        WHERE plataforma = 'mercado_livre'
          AND status NOT IN ('indisponivel', 'erro', 'duplicado_oculto')
          AND TRIM(COALESCE(link_afiliado, '')) = ''
          AND TRIM(COALESCE(link_original, '')) <> ''
        ORDER BY id
    """
    if limite:
        consulta += " LIMIT ?"
    with conectar() as conn:
        rows = conn.execute(consulta, (int(limite),) if limite else ()).fetchall()
    return [dict(row) for row in rows]


def _extrair_meli_la(pagina):
    for link in pagina.locator('a[href^="https://meli.la/"]').all():
        try:
            href = link.get_attribute("href") or ""
        except Exception:
            continue
        if link_afiliado_valido(href):
            return href
    for seletor in ("textarea", "input"):
        for campo in pagina.locator(seletor).all():
            try:
                valor = campo.input_value()
            except Exception:
                continue
            encontrado = MELI_LINK_RE.search(str(valor or ""))
            if encontrado and link_afiliado_valido(encontrado.group(0)):
                return encontrado.group(0)
    try:
        encontrado = MELI_LINK_RE.search(pagina.content())
        if encontrado and link_afiliado_valido(encontrado.group(0)):
            return encontrado.group(0)
    except Exception:
        pass
    return ""


def _nome_diagnostico(permalink, etapa):
    item = re.search(r"MLB\d+", permalink or "", re.I)
    identificador = item.group(0).upper() if item else "produto"
    instante = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return PASTA_DIAGNOSTICO / f"{identificador}_{etapa}_{instante}.png"


def _screenshot(pagina, permalink, etapa):
    try:
        PASTA_DIAGNOSTICO.mkdir(parents=True, exist_ok=True)
        destino = _nome_diagnostico(permalink, etapa)
        pagina.screenshot(path=str(destino), full_page=False)
        return str(destino)
    except Exception:
        return ""


def _botao_oficial(pagina):
    botoes = pagina.locator('button[data-testid="generate_link_button"]')
    candidatos = []
    for indice in range(botoes.count()):
        botao = botoes.nth(indice)
        try:
            if not botao.is_visible():
                continue
            caixa = botao.bounding_box()
            if caixa:
                candidatos.append((caixa["y"], botao, caixa))
        except Exception:
            continue
    if not candidatos:
        return None, "", None
    _, botao, caixa = min(candidatos, key=lambda candidato: candidato[0])
    return botao, "data-testid", caixa


def _aguardar_botao_oficial(pagina):
    try:
        pagina.locator('button[data-testid="generate_link_button"]').first.wait_for(
            state="visible", timeout=15000
        )
    except Exception:
        pass
    return _botao_oficial(pagina)


def _botao_fallback(pagina):
    candidatos = []
    altura = (pagina.viewport_size or {}).get("height", 900)
    controles = pagina.locator("button, a, [role='button']")
    for indice in range(controles.count()):
        botao = controles.nth(indice)
        try:
            if not botao.is_visible() or "compartilhar" not in botao.inner_text().strip().lower():
                continue
            caixa = botao.bounding_box()
            if caixa and caixa["y"] <= altura * 0.7:
                candidatos.append((caixa["y"], botao, caixa))
        except Exception:
            continue
    if not candidatos:
        return None, "", None
    _, botao, caixa = min(candidatos, key=lambda candidato: candidato[0])
    return botao, "fallback_compartilhar_superior", caixa


def diagnosticar_compartilhar(permalink, clicar=False):
    """Abre um produto e diagnostica o gerador oficial sem tocar no SQLite."""
    perfil = PERFIL_PRINCIPAL if PERFIL_PRINCIPAL.exists() else PERFIL_RESERVA
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch_persistent_context(user_data_dir=str(perfil), headless=False)
        try:
            pagina = navegador.new_page()
            pagina.set_default_timeout(12000)
            pagina.goto(permalink, wait_until="domcontentloaded", timeout=45000)
            pagina.wait_for_timeout(1800)
            if login_necessario_na_pagina(pagina):
                raise LoginNecessario("sessão Mercado Livre não autenticada")
            antes = _screenshot(pagina, permalink, "antes_clique")
            botao, estrategia, caixa = _aguardar_botao_oficial(pagina)
            if not botao:
                botao, estrategia, caixa = _botao_fallback(pagina)
            resultado = {
                "encontrado": bool(botao),
                "estrategia": estrategia or "nao_encontrado",
                "coordenadas": caixa,
                "screenshot_antes": antes,
                "screenshot_depois": "",
                "screenshot_link": "",
                "link": "",
            }
            if clicar and botao:
                botao.click()
                pagina.wait_for_timeout(1500)
                resultado["screenshot_depois"] = _screenshot(pagina, permalink, "depois_clique")
                resultado["link"] = _extrair_meli_la(pagina)
                if resultado["link"]:
                    resultado["screenshot_link"] = _screenshot(pagina, permalink, "link_encontrado")
            return resultado
        finally:
            navegador.close()


def gerar_link_oficial_na_pagina(pagina, permalink="", navegar=True):
    """Extrai meli.la no contexto já autenticado da página do produto."""
    if navegar:
        pagina.goto(permalink, wait_until="domcontentloaded", timeout=45000)
        pagina.wait_for_timeout(1800)
    if login_necessario_na_pagina(pagina):
        raise LoginNecessario("sessão Mercado Livre não autenticada")
    _screenshot(pagina, permalink, "antes_clique")
    botao, estrategia, _ = _aguardar_botao_oficial(pagina)
    if not botao:
        botao, estrategia, _ = _botao_fallback(pagina)
    if not botao:
        raise RuntimeError("Botão oficial generate_link_button não encontrado")
    if estrategia != "data-testid":
        registrar_log("afiliados", f"Fallback de Compartilhar usado para {permalink}", nivel="warning")
    botao.click()
    pagina.wait_for_timeout(2200)
    _screenshot(pagina, permalink, "depois_clique")
    link = _extrair_meli_la(pagina)
    if not link:
        for espera in (2500, 4000):
            pagina.wait_for_timeout(espera)
            link = _extrair_meli_la(pagina)
            if link:
                break
    if link:
        _screenshot(pagina, permalink, "link_encontrado")
    return link


def _gerar_em_pagina(pagina, permalink):
    return gerar_link_oficial_na_pagina(pagina, permalink, navegar=True)


def gerar_links_afiliados(limite=None):
    pendentes = produtos_sem_afiliado(limite)
    return gerar_links_afiliados_para(pendentes)


def gerar_links_afiliados_para(pendentes):
    pendentes = [dict(item) for item in (pendentes or [])]
    resultado = {"pendentes": len(pendentes), "gerados": 0, "falhas": 0, "itens": []}
    if not pendentes:
        _limpar_checkpoint()
        return resultado

    checkpoint = _carregar_checkpoint()
    item_checkpoint = str(checkpoint.get("item_id") or "").strip()
    if item_checkpoint:
        posicao = next((i for i, item in enumerate(pendentes) if item["item_id"] == item_checkpoint), 0)
        pendentes = pendentes[posicao:]

    tamanho_lote = _config_int("PLAYWRIGHT_LOTE_TAMANHO", 25, minimo=1, maximo=30)
    perfis = (PERFIL_PRINCIPAL, PERFIL_RESERVA)
    with sync_playwright() as playwright:
        navegador = None
        processados_lote = 0
        try:
            for indice, produto in enumerate(pendentes):
                if navegador is None:
                    navegador = abrir_contexto_persistente(playwright, visual=True, perfis=perfis)
                    processados_lote = 0
                if processados_lote >= tamanho_lote:
                    navegador.close()
                    navegador = None
                    _salvar_checkpoint(indice=indice, item_id=produto["item_id"], url=produto["link_original"], etapa="pausa_lote", motivo="limite_de_lote")
                    _pausa_lote()
                    navegador = abrir_contexto_persistente(playwright, visual=True, perfis=perfis)
                    processados_lote = 0

                _salvar_checkpoint(indice=indice, item_id=produto["item_id"], url=produto["link_original"], etapa="gerando_meli_la", motivo="andamento")
                pagina = navegador.new_page()
                pagina.set_default_timeout(12000)
                try:
                    link = _gerar_em_pagina(pagina, produto["link_original"])
                    if not link:
                        raise RuntimeError("Portal não retornou link meli.la após espera estendida")
                    atualizar_link_afiliado_oficial(produto["id"], link)
                    resultado["gerados"] += 1
                    resultado["itens"].append({"item_id": produto["item_id"], "status": "gerado"})
                    processados_lote += 1
                    _salvar_checkpoint(indice=indice + 1, item_id=produto["item_id"], url=produto["link_original"], etapa="salvo", motivo="andamento")
                    _pausa_produto()
                except LoginNecessario as erro:
                    _salvar_checkpoint(indice=indice, item_id=produto["item_id"], url=produto["link_original"], etapa="login_necessario", motivo=str(erro))
                    registrar_evento_sistema("playwright", "mercado_livre", "login_necessario", "Login Mercado Livre necessário para afiliados", str(erro))
                    registrar_log("afiliados", "Login necessário; geração de afiliados pausada com checkpoint preservado.", nivel="warning")
                    raise
                except Exception as erro:
                    resultado["falhas"] += 1
                    resultado["itens"].append({"item_id": produto["item_id"], "status": "falhou"})
                    registrar_log("afiliados", f"Falha ao gerar meli.la para {produto['item_id']}: {erro}", nivel="warning")
                finally:
                    try:
                        pagina.close()
                    except Exception:
                        pass
            _limpar_checkpoint()
            return resultado
        finally:
            if navegador:
                navegador.close()
