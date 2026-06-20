"""Geração de links oficiais meli.la pelo botão Compartilhar do Mercado Livre."""

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from banco import atualizar_link_afiliado_oficial, conectar, inicializar_banco, registrar_log
from gerador_link_mercadolivre import link_afiliado_valido
from playwright_perfil import PERFIL_PRINCIPAL, PERFIL_RESERVA


MELI_LINK_RE = re.compile(r"https://meli\.la/[A-Za-z0-9]+")
PASTA_DIAGNOSTICO = Path("logs") / "afiliados"


def produtos_sem_afiliado(limite=None):
    inicializar_banco()
    consulta = """
        SELECT id, item_id, titulo, link_original
        FROM produtos
        WHERE plataforma = 'mercado_livre'
          AND status NOT IN ('indisponivel', 'erro')
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
            state="visible", timeout=8000
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
    _screenshot(pagina, permalink, "antes_clique")
    botao, estrategia, _ = _aguardar_botao_oficial(pagina)
    if not botao:
        botao, estrategia, _ = _botao_fallback(pagina)
    if not botao:
        raise RuntimeError("Botão oficial generate_link_button não encontrado")
    if estrategia != "data-testid":
        registrar_log("afiliados", f"Fallback de Compartilhar usado para {permalink}", nivel="warning")
    botao.click()
    pagina.wait_for_timeout(1200)
    _screenshot(pagina, permalink, "depois_clique")
    link = _extrair_meli_la(pagina)
    if link:
        _screenshot(pagina, permalink, "link_encontrado")
    return link


def _gerar_em_pagina(pagina, permalink):
    return gerar_link_oficial_na_pagina(pagina, permalink, navegar=True)


def gerar_links_afiliados(limite=None):
    pendentes = produtos_sem_afiliado(limite)
    resultado = {"pendentes": len(pendentes), "gerados": 0, "falhas": 0, "itens": []}
    if not pendentes:
        return resultado

    perfis = [PERFIL_PRINCIPAL] + ([PERFIL_RESERVA] if PERFIL_RESERVA.exists() else [])
    ultimo_erro = None
    for perfil in perfis:
        try:
            with sync_playwright() as playwright:
                navegador = playwright.chromium.launch_persistent_context(
                    user_data_dir=str(perfil), headless=False
                )
                try:
                    for produto in pendentes:
                        pagina = navegador.new_page()
                        pagina.set_default_timeout(12000)
                        try:
                            link = _gerar_em_pagina(pagina, produto["link_original"])
                            if not link:
                                raise RuntimeError("Portal não retornou link meli.la")
                            atualizar_link_afiliado_oficial(produto["id"], link)
                            resultado["gerados"] += 1
                            resultado["itens"].append({"item_id": produto["item_id"], "status": "gerado"})
                        except Exception as erro:
                            resultado["falhas"] += 1
                            resultado["itens"].append({"item_id": produto["item_id"], "status": "falhou"})
                            registrar_log("afiliados", f"Falha ao gerar meli.la para {produto['item_id']}: {erro}", nivel="warning")
                        finally:
                            try:
                                pagina.close()
                            except Exception:
                                pass
                    return resultado
                finally:
                    navegador.close()
        except Exception as erro:
            ultimo_erro = erro
            continue
    raise RuntimeError(f"Não foi possível abrir perfil para gerar links afiliados: {ultimo_erro}")
