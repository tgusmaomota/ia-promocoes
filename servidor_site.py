import argparse
import errno
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from gerar_site import SITE_DIR, gerar_site


def _abrir_servidor_livre(host, porta, handler, tentativas=20):
    for candidata in range(porta, porta + tentativas):
        try:
            return ThreadingHTTPServer((host, candidata), handler), candidata
        except OSError as erro:
            if erro.errno != errno.EADDRINUSE:
                raise
    raise OSError(f"Nenhuma porta livre encontrada entre {porta} e {porta + tentativas - 1}")


def servir_site(host="127.0.0.1", porta=8000):
    gerar_site()
    site_dir = SITE_DIR.resolve()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(site_dir), **kwargs)

    servidor, porta_usada = _abrir_servidor_livre(host, porta, Handler)
    print(f"Site local em http://localhost:{porta_usada}/")
    print("Abra essa URL no navegador. Para encerrar, pressione Ctrl+C neste terminal.")
    print(f"Servindo pasta: {site_dir}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        servidor.server_close()


def main():
    parser = argparse.ArgumentParser(description="Servidor local do site público IA-Promocoes")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=8000)
    args = parser.parse_args()
    servir_site(args.host, args.porta)


if __name__ == "__main__":
    main()
