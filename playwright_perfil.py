"""Operação segura dos perfis persistentes usados pelo Playwright."""

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path


PERFIL_PRINCIPAL = Path("perfil_mercadolivre")
PERFIL_RESERVA = Path("perfil_mercadolivre_backup")
ARQUIVOS_LOCK = ("SingletonLock", "SingletonCookie", "SingletonSocket")


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
