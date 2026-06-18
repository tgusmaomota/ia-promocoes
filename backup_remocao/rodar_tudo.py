import subprocess
import sys

python_atual = sys.executable

etapas = [
    ("1/7 - Buscando ofertas do Mercado Livre", "agente_ofertas.py"),
    ("2/7 - Fazendo curadoria", "agente_curadoria.py"),
    ("3/7 - Gerando links afiliados", "agente_afiliado.py"),
    ("4/7 - Importando produtos para posts", "importar_afiliados.py"),
    ("5/7 - Exportando publicações", "agente_publicador.py"),
    ("6/7 - Enviando Telegram", "agente_telegram.py"),
    ("7/7 - Gerando site", "agente_site.py"),
]

for nome, arquivo in etapas:
    print("\n" + "=" * 50)
    print(nome)
    print("=" * 50)

    resultado = subprocess.run([python_atual, arquivo])

    if resultado.returncode != 0:
        print(f"Erro na etapa: {nome}")
        break
