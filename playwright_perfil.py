"""Operação segura dos perfis persistentes usados pelo Playwright."""

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from banco import registrar_evento_sistema, registrar_log


PERFIL_PRINCIPAL = Path("perfil_mercadolivre")
PERFIL_RESERVA = Path("perfil_mercadolivre_backup")
ARQUIVOS_LOCK = ("SingletonLock", "SingletonCookie", "SingletonSocket")
CHECKPOINT_COLETA = Path(".coleta_confiavel_checkpoint.json")
URL_MERCADO_LIVRE = "https://www.mercadolivre.com.br/"
URL_CONTA = "https://www.mercadolivre.com.br/my-account"
PROCESSOS_CHROME_TESTING = (
    "Google Chrome for Testing",
    "chrome for testing",
    "Chromium",
)


class LoginNecessario(RuntimeError):
    """Sinaliza que a sessão Mercado Livre precisa ser renovada manualmente."""


def _processos_do_perfil(perfil):
    try:
        resultado = subprocess.run(
            ["ps", "-axo", "pid=,command="],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as erro:
        return [], f"Não foi possível listar processos: {erro}"
    if resultado.returncode != 0:
        return [], "Permissão insuficiente para listar processos do Chrome."

    caminho = str(Path(perfil).resolve())
    processos = []
    for linha in resultado.stdout.splitlines():
        if caminho not in linha:
            continue
        partes = linha.strip().split(None, 1)
        try:
            processos.append({"pid": int(partes[0]), "comando": partes[1] if len(partes) > 1 else ""})
        except (IndexError, ValueError):
            continue
    return processos, ""


def diagnosticar_perfil(perfil=PERFIL_PRINCIPAL):
    perfil = Path(perfil)
    processos, aviso = _processos_do_perfil(perfil)
    locks = [str(perfil / nome) for nome in ARQUIVOS_LOCK if (perfil / nome).exists() or (perfil / nome).is_symlink()]
    return {
        "perfil": str(perfil),
        "existe": perfil.is_dir(),
        "processos": processos,
        "locks": locks,
        "disponivel": perfil.is_dir() and not processos and not locks,
        "aviso": aviso,
    }


def abrir_contexto_persistente(playwright, visual=False, perfis=None):
    """Abre um contexto persistente, preferindo o perfil oficial salvo."""
    ultimo_erro = None
    for perfil in (perfis or (PERFIL_PRINCIPAL, PERFIL_RESERVA)):
        perfil = Path(perfil)
        if not perfil.exists():
            continue
        try:
            return playwright.chromium.launch_persistent_context(
                user_data_dir=str(perfil),
                headless=not visual,
            )
        except Exception as erro:
            ultimo_erro = erro
            continue
    if ultimo_erro:
        raise RuntimeError(f"Não foi possível abrir perfil Playwright: {ultimo_erro}")
    raise RuntimeError("Perfil Mercado Livre não encontrado; rode: python3 ia_promocoes.py login-mercadolivre")


def login_necessario_na_pagina(pagina):
    """Detecta sinais de logout sem ler cookies nem expor dados de sessão."""
    try:
        url = str(pagina.url or "").lower()
    except Exception:
        url = ""
    if any(trecho in url for trecho in ("login", "authorization", "auth", "identify")):
        return True
    try:
        texto = pagina.locator("body").inner_text(timeout=2500).lower()
    except Exception:
        texto = ""
    sinais = (
        "entrar",
        "iniciar sessão",
        "crie a sua conta",
        "crie sua conta",
        "identificação",
        "portal afiliado",
        "faça login",
    )
    if "mercado livre" in texto and any(sinal in texto for sinal in sinais):
        return True
    try:
        botao = pagina.locator("text=/^\\s*Entrar\\s*$/i").first
        return bool(botao.is_visible(timeout=1000))
    except Exception:
        return False


def verificar_login_mercadolivre(visual=False):
    """Abre o perfil salvo, confirma login e fecha o navegador sem coletar."""
    from playwright.sync_api import sync_playwright

    diagnostico = diagnosticar_perfil(PERFIL_PRINCIPAL)
    if not diagnostico["existe"]:
        return {"logado": False, "perfil": str(PERFIL_PRINCIPAL), "motivo": "perfil_mercadolivre ausente"}
    if diagnostico["processos"] or diagnostico["locks"]:
        return {"logado": False, "perfil": str(PERFIL_PRINCIPAL), "motivo": "perfil em uso ou com locks temporários"}

    with sync_playwright() as playwright:
        navegador = abrir_contexto_persistente(playwright, visual=visual, perfis=(PERFIL_PRINCIPAL,))
        try:
            pagina = navegador.pages[0] if navegador.pages else navegador.new_page()
            pagina.set_default_timeout(12000)
            pagina.goto(URL_CONTA, wait_until="domcontentloaded", timeout=30000)
            pagina.wait_for_timeout(1200)
            if login_necessario_na_pagina(pagina):
                return {"logado": False, "perfil": str(PERFIL_PRINCIPAL), "motivo": "Mercado Livre solicitou login"}
            try:
                texto = pagina.locator("body").inner_text(timeout=5000).lower()
            except Exception:
                texto = ""
            sinais = ("minha conta", "minhas compras", "meus dados", "vender")
            logado = any(sinal in texto for sinal in sinais)
            return {
                "logado": bool(logado),
                "perfil": str(PERFIL_PRINCIPAL),
                "motivo": "Área da conta acessível" if logado else "sinais de login insuficientes",
            }
        finally:
            navegador.close()


def _processos_chrome_testing():
    try:
        resultado = subprocess.run(
            ["ps", "-axo", "pid=,command="],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    processos = []
    for linha in resultado.stdout.splitlines():
        comando = linha.strip()
        if not any(nome.lower() in comando.lower() for nome in PROCESSOS_CHROME_TESTING):
            continue
        partes = comando.split(None, 1)
        try:
            processos.append({"pid": int(partes[0]), "comando": partes[1] if len(partes) > 1 else ""})
        except (IndexError, ValueError):
            continue
    return processos


def pausar_playwright_seguro():
    """Pausa automações locais e libera o perfil sem apagar cookies/sessão."""
    from estado_sistema import MANUTENCAO, definir_estado_sistema

    definir_estado_sistema(MANUTENCAO, "pausar-playwright acionado")
    Path(".ia_promocoes.stop").write_text("parar\n", encoding="utf-8")
    encerrados = []
    for processo in _processos_chrome_testing():
        try:
            os.kill(processo["pid"], signal.SIGTERM)
            encerrados.append(processo["pid"])
        except (ProcessLookupError, PermissionError):
            continue
    limite = time.time() + 8
    while time.time() < limite:
        if not _processos_chrome_testing():
            break
        time.sleep(0.4)

    removidos = []
    for perfil in (PERFIL_PRINCIPAL, PERFIL_RESERVA):
        for nome in ARQUIVOS_LOCK:
            caminho = perfil / nome
            if caminho.exists() or caminho.is_symlink():
                try:
                    caminho.unlink()
                    removidos.append(str(caminho))
                except OSError:
                    pass
    registrar_log("playwright", "Playwright pausado com perfil e checkpoint preservados.")
    registrar_evento_sistema("playwright", "master", "sucesso", "Playwright pausado com segurança", f"processos={len(encerrados)} locks={len(removidos)}")
    return {
        "estado": "MANUTENCAO",
        "processos_encerrados": encerrados,
        "locks_removidos": removidos,
        "perfil_preservado": PERFIL_PRINCIPAL.exists(),
        "checkpoint_preservado": CHECKPOINT_COLETA.exists(),
    }


def imprimir_diagnostico(perfil=PERFIL_PRINCIPAL):
    dados = diagnosticar_perfil(perfil)
    print(f"Perfil: {dados['perfil']}")
    print(f"Existe: {'sim' if dados['existe'] else 'não'}")
    print(f"Processos Chrome usando o perfil: {len(dados['processos'])}")
    for processo in dados["processos"]:
        print(f"- PID {processo['pid']}: {processo['comando'][:180]}")
    print("Locks temporários:")
    if dados["locks"]:
        for lock in dados["locks"]:
            print(f"- {lock}")
    else:
        print("- nenhum")
    print(f"Perfil disponível: {'sim' if dados['disponivel'] else 'não'}")
    if dados["aviso"]:
        print(f"Aviso: {dados['aviso']}")
    return dados


def criar_perfil_reserva():
    """Cria uma cópia do perfil apenas quando ele está livre, sem apagar o original."""
    principal = diagnosticar_perfil(PERFIL_PRINCIPAL)
    if not principal["existe"]:
        raise RuntimeError("Perfil principal não existe; faça login pelo Playwright antes de criar a reserva.")
    if principal["processos"] or principal["locks"]:
        raise RuntimeError("Perfil principal está em uso ou possui locks; repare-o antes de criar a reserva.")
    if PERFIL_RESERVA.exists():
        return PERFIL_RESERVA

    ignorar = shutil.ignore_patterns(*ARQUIVOS_LOCK, "Crashpad", "Code Cache", "GPUCache")
    shutil.copytree(PERFIL_PRINCIPAL, PERFIL_RESERVA, symlinks=True, ignore=ignorar)
    return PERFIL_RESERVA


def reparar_perfil():
    """Encerra somente processos que apontam para o perfil e remove locks órfãos."""
    antes = diagnosticar_perfil(PERFIL_PRINCIPAL)
    encerrados = []
    for processo in antes["processos"]:
        try:
            os.kill(processo["pid"], signal.SIGTERM)
            encerrados.append(processo["pid"])
        except (ProcessLookupError, PermissionError) as erro:
            raise RuntimeError(f"Não foi possível encerrar PID {processo['pid']}: {erro}") from erro

    limite = time.time() + 8
    while time.time() < limite:
        restantes, _ = _processos_do_perfil(PERFIL_PRINCIPAL)
        if not restantes:
            break
        time.sleep(0.4)

    restantes, _ = _processos_do_perfil(PERFIL_PRINCIPAL)
    if restantes:
        raise RuntimeError("Ainda há processos usando o perfil; feche o Chrome manualmente antes de remover locks.")

    removidos = []
    for nome in ARQUIVOS_LOCK:
        caminho = PERFIL_PRINCIPAL / nome
        if caminho.exists() or caminho.is_symlink():
            caminho.unlink()
            removidos.append(str(caminho))

    reserva = criar_perfil_reserva()
    depois = diagnosticar_perfil(PERFIL_PRINCIPAL)
    return {"encerrados": encerrados, "locks_removidos": removidos, "reserva": str(reserva), "disponivel": depois["disponivel"]}
