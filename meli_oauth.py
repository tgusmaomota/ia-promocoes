"""OAuth local e seguro para a API oficial do Mercado Livre."""

import os
from getpass import getpass
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv, set_key


ENV_PATH = Path(".env")
AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ME_URL = "https://api.mercadolibre.com/users/me"


class ErroOAuthMercadoLivre(RuntimeError):
    pass


def _configuracao(exigir_access_token=False):
    load_dotenv(ENV_PATH, override=True)
    dados = {
        "client_id": os.getenv("MELI_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("MELI_CLIENT_SECRET", "").strip(),
        "redirect_uri": os.getenv("MELI_REDIRECT_URI", "").strip(),
        "access_token": os.getenv("MELI_ACCESS_TOKEN", "").strip(),
        "refresh_token": os.getenv("MELI_REFRESH_TOKEN", "").strip(),
    }
    obrigatorios = ["client_id", "client_secret", "redirect_uri"]
    if exigir_access_token:
        obrigatorios.append("access_token")
    faltantes = [nome for nome in obrigatorios if not dados[nome]]
    if faltantes:
        raise ErroOAuthMercadoLivre(f"Variáveis ausentes no .env: {', '.join(faltantes)}")
    return dados


def _client_id_parcial(client_id):
    return f"{client_id[:4]}...{client_id[-4:]}" if len(client_id) > 8 else "[configurado]"


def _resposta_sanitizada(dados):
    permitidos = {"error", "message", "status", "cause", "user_id", "nickname", "site_id", "scope", "permissions"}
    return {chave: valor for chave, valor in dados.items() if chave in permitidos} if isinstance(dados, dict) else {"resposta": "não JSON"}


def _diagnostico(resposta, config, fluxo):
    try:
        dados = resposta.json()
    except ValueError:
        dados = {"message": "resposta não JSON"}
    erro = str(dados.get("error", ""))
    mensagem = str(dados.get("message", ""))
    orientacao = "Revise a configuração do aplicativo no portal de desenvolvedores do Mercado Livre."
    if erro == "invalid_grant":
        orientacao = "O code foi usado, expirou ou a redirect_uri diverge. Gere um code novo e use-o apenas uma vez."
    elif erro == "invalid_client":
        orientacao = "MELI_CLIENT_ID e MELI_CLIENT_SECRET não pertencem ao mesmo aplicativo ou um deles está incorreto."
    elif resposta.status_code == 403:
        orientacao = "Revise autorização do aplicativo, escopos, conta e possíveis restrições de IP."
    return "\n".join((
        f"OAuth {fluxo} falhou.", f"HTTP status: {resposta.status_code}",
        f"error: {erro or 'não informado'}", f"message: {mensagem or 'não informado'}",
        f"redirect_uri usada: {config['redirect_uri']}", f"client_id: {_client_id_parcial(config['client_id'])}",
        f"Orientação: {orientacao}", f"Resposta sanitizada: {_resposta_sanitizada(dados)}",
    ))


def url_autorizacao():
    config = _configuracao()
    return AUTH_URL + "?" + urlencode({"response_type": "code", "client_id": config["client_id"], "redirect_uri": config["redirect_uri"]})


def _salvar_tokens(dados):
    access_token = str(dados.get("access_token", "")).strip()
    refresh_token = str(dados.get("refresh_token", "")).strip()
    if not access_token or not refresh_token:
        raise ErroOAuthMercadoLivre(f"Resposta OAuth não incluiu tokens. Resposta sanitizada: {_resposta_sanitizada(dados)}")
    set_key(ENV_PATH, "MELI_ACCESS_TOKEN", access_token)
    set_key(ENV_PATH, "MELI_REFRESH_TOKEN", refresh_token)


def trocar_codigo(code):
    config = _configuracao()
    resposta = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code", "client_id": config["client_id"],
        "client_secret": config["client_secret"], "code": str(code or "").strip(),
        "redirect_uri": config["redirect_uri"],
    }, timeout=30)
    if resposta.status_code != 200:
        raise ErroOAuthMercadoLivre(_diagnostico(resposta, config, "troca de código"))
    try:
        dados = resposta.json()
    except ValueError as erro:
        raise ErroOAuthMercadoLivre("OAuth retornou conteúdo inválido ao trocar o código.") from erro
    _salvar_tokens(dados)
    return testar_token()


def refresh_token():
    config = _configuracao()
    if not config["refresh_token"]:
        raise ErroOAuthMercadoLivre("MELI_REFRESH_TOKEN ausente no .env.")
    resposta = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token", "client_id": config["client_id"],
        "client_secret": config["client_secret"], "refresh_token": config["refresh_token"],
    }, timeout=30)
    if resposta.status_code != 200:
        raise ErroOAuthMercadoLivre(_diagnostico(resposta, config, "refresh token"))
    try:
        dados = resposta.json()
    except ValueError as erro:
        raise ErroOAuthMercadoLivre("OAuth retornou conteúdo inválido ao renovar o token.") from erro
    _salvar_tokens(dados)
    return testar_token()


def testar_token():
    config = _configuracao(exigir_access_token=True)
    resposta = requests.get(ME_URL, headers={"Authorization": f"Bearer {config['access_token']}", "Accept": "application/json"}, timeout=20)
    try:
        dados = resposta.json()
    except ValueError:
        dados = {}
    if resposta.status_code != 200:
        raise ErroOAuthMercadoLivre(_diagnostico(resposta, config, "teste de token"))
    return {"http_status": resposta.status_code, "user_id": dados.get("id"), "nickname": dados.get("nickname"), "site_id": dados.get("site_id")}


def autenticar_interativo():
    print("Abra esta URL no navegador e autorize o aplicativo:")
    print(url_autorizacao())
    code = getpass("Code OAuth: ")
    return trocar_codigo(code)


def validar_oauth_local():
    erros = []
    try:
        url_autorizacao()
    except ErroOAuthMercadoLivre as erro:
        erros.append(str(erro))
    return erros


def status_oauth_local():
    """Status sem rede: confirma configuração, nunca revela credenciais."""
    try:
        config = _configuracao(exigir_access_token=True)
    except ErroOAuthMercadoLivre:
        return False
    return bool(config["client_id"] and config["client_secret"] and config["redirect_uri"])
