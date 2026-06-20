"""Troca um code OAuth por tokens locais, sem exibir segredos."""

import argparse

from meli_oauth import ErroOAuthMercadoLivre, trocar_codigo


def main():
    parser = argparse.ArgumentParser(description="Troca código OAuth do Mercado Livre por tokens locais")
    parser.add_argument("code", help="Código recebido na URL de retorno OAuth")
    args = parser.parse_args()
    try:
        perfil = trocar_codigo(args.code)
    except ErroOAuthMercadoLivre as erro:
        raise SystemExit(str(erro))
    print("Tokens OAuth salvos no .env local. Nenhum token foi exibido.")
    print(f"Token validado: HTTP {perfil['http_status']} | user_id={perfil['user_id']} | nickname={perfil['nickname']} | site_id={perfil['site_id']}")


if __name__ == "__main__":
    main()
