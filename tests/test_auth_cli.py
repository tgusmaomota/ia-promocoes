import subprocess
import sys
from pathlib import Path


def test_cli_auth_teste_funciona_sem_vazar_segredos_e_sem_tocar_banco_operacional():
    banco_operacional = Path("banco.db")
    auth_dev = Path("auth_dev.db")
    before_banco_mtime = banco_operacional.stat().st_mtime_ns if banco_operacional.exists() else None
    before_auth_dev_exists = auth_dev.exists()

    resultado = subprocess.run(
        [sys.executable, "ia_promocoes.py", "auth-teste"],
        capture_output=True,
        text=True,
        check=False,
    )

    after_banco_mtime = banco_operacional.stat().st_mtime_ns if banco_operacional.exists() else None
    output = f"{resultado.stdout}\n{resultado.stderr}".lower()
    termos_proibidos = (
        "password",
        "senha-correta",
        "senha-incorreta",
        "refresh_token",
        "promogg_refresh_token",
        "signing_key",
        "secret",
        "cookie",
    )

    assert resultado.returncode == 0
    assert resultado.stdout == "AUTH_TESTE=ok\n"
    assert resultado.stderr == ""
    assert not any(termo in output for termo in termos_proibidos)
    assert before_banco_mtime == after_banco_mtime
    assert auth_dev.exists() is before_auth_dev_exists
