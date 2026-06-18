import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from gerar_site import SITE_DIR, gerar_site


def servir_site(host="127.0.0.1", porta=8000):
    gerar_site()
    site_dir = SITE_DIR.resolve()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(site_dir), **kwargs)

    servidor = ThreadingHTTPServer((host, porta), Handler)
    print(f"Site local em http://localhost:{porta}/")
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
