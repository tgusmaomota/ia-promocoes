import subprocess
import sys


python_atual = sys.executable

print("Iniciando IA-Promocoes pelo comando operacional oficial.")

resultado = subprocess.run(
    [python_atual, "ia_promocoes.py", "iniciar"],
)

if resultado.returncode != 0:
    print("Erro ao executar o robô de produção.")
    raise SystemExit(resultado.returncode)

print("\nProcesso finalizado.")
print("\nComando oficial:")
print(f"{python_atual} ia_promocoes.py iniciar")
