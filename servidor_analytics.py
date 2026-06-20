import json
import os
import re
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from banco import registrar_clique
from estado_sistema import em_offline


TIPOS_EVENTO = {"card_oferta", "ver_oferta", "compra_produto", "teste"}
EVENTOS_RECENTES = {}
LIMITE_EVENTOS_POR_MINUTO = 120


def origens_permitidas():
    configuradas = os.getenv("PROMOGG_ANALYTICS_ORIGINS", "https://promogg.com.br")
    return {origem.strip().rstrip("/") for origem in configuradas.split(",") if origem.strip()}


class AnalyticsHandler(BaseHTTPRequestHandler):
    server_version = "PromoggAnalytics/1.0"

    def log_message(self, format, *args):
        # Não registrar IP ou metadados de acesso no console.
        return

    def _origem_valida(self):
        origem = str(self.headers.get("Origin") or "").rstrip("/")
        return origem in origens_permitidas()

    def _responder(self, status, corpo=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        origem = str(self.headers.get("Origin") or "").rstrip("/")
        if origem in origens_permitidas():
            self.send_header("Access-Control-Allow-Origin", origem)
            self.send_header("Vary", "Origin")
        self.end_headers()
        if corpo is not None:
            self.wfile.write(json.dumps(corpo).encode("utf-8"))

    def do_OPTIONS(self):
        if not self._origem_valida():
            self._responder(HTTPStatus.FORBIDDEN, {"ok": False})
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        origem = str(self.headers.get("Origin") or "").rstrip("/")
        if origem:
            self.send_header("Access-Control-Allow-Origin", origem)
            self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self):
        if self.path != "/health":
            self._responder(HTTPStatus.NOT_FOUND, {"ok": False})
            return
        self._responder(HTTPStatus.OK, {"ok": True, "dados_pessoais": False})

    @staticmethod
    def _evento_valido(evento):
        oferta_id = str(evento.get("oferta_id") or "").strip().upper()
        item_id = str(evento.get("item_id") or oferta_id).strip().upper()
        titulo = " ".join(str(evento.get("titulo") or "").split())[:300]
        categoria = " ".join(str(evento.get("categoria") or "ofertas").split())[:120] or "ofertas"
        origem = " ".join(str(evento.get("origem") or "site_publico").split())[:40] or "site_publico"
        pagina = str(evento.get("pagina_origem") or "/").strip()[:300] or "/"
        tipo = " ".join(str(evento.get("tipo_evento") or "ver_oferta").split())[:40] or "ver_oferta"
        if not re.fullmatch(r"MLB\d{5,}", item_id) or not titulo or tipo not in TIPOS_EVENTO or not pagina.startswith("/"):
            raise ValueError("evento inválido")
        return oferta_id or item_id, item_id, titulo, categoria, origem, pagina, tipo

    @staticmethod
    def _limite_excedido(item_id, tipo):
        janela = int(time.time() // 60)
        chave = (item_id, tipo, janela)
        EVENTOS_RECENTES[chave] = EVENTOS_RECENTES.get(chave, 0) + 1
        for item in list(EVENTOS_RECENTES):
            if item[2] < janela - 1:
                del EVENTOS_RECENTES[item]
        return EVENTOS_RECENTES[chave] > LIMITE_EVENTOS_POR_MINUTO

    def do_POST(self):
        if em_offline():
            self._responder(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False})
            return
        if self.path != "/api/cliques" or not self._origem_valida():
            self._responder(HTTPStatus.NOT_FOUND, {"ok": False})
            return
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            if tamanho <= 0 or tamanho > 2048:
                raise ValueError("tamanho inválido")
            evento = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            dados = self._evento_valido(evento)
            if self._limite_excedido(dados[1], dados[6]):
                self._responder(HTTPStatus.TOO_MANY_REQUESTS, {"ok": False})
                return
            registrar_clique(
                dados[0], dados[2], dados[3], item_id=dados[1],
                origem=dados[4], pagina_origem=dados[5], tipo_evento=dados[6],
            )
        except (AttributeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._responder(HTTPStatus.BAD_REQUEST, {"ok": False})
            return
        self._responder(HTTPStatus.ACCEPTED, {"ok": True})


def main():
    porta = int(os.getenv("PROMOGG_ANALYTICS_PORT", "8787"))
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), AnalyticsHandler)
    print(f"Analytics Promogg em http://127.0.0.1:{porta}/api/cliques (modo local)")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
