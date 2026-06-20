from meli_oauth import ErroOAuthMercadoLivre, url_autorizacao


try:
    print("Abra este link no navegador:")
    print(url_autorizacao())
except ErroOAuthMercadoLivre as erro:
    raise SystemExit(str(erro))
