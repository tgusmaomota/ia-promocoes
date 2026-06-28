# Mercado Livre OAuth

O monitoramento usa a API oficial do Mercado Livre. Uma sessão do navegador em `perfil_mercadolivre/` não autoriza chamadas da API.

Quando a API responder `403`, registre ou revise o aplicativo no portal de desenvolvedores do Mercado Livre e configure no `.env` local:

```env
MELI_CLIENT_ID=
MELI_CLIENT_SECRET=
MELI_REDIRECT_URI=
MELI_ACCESS_TOKEN=
MELI_REFRESH_TOKEN=
```

Não publique essas variáveis e não coloque tokens em arquivos do site. O cliente passa `MELI_ACCESS_TOKEN` somente no cabeçalho `Authorization: Bearer` ao consultar a API.

## Comandos do Promogg

```bash
python3 ia_promocoes.py meli-auth
python3 ia_promocoes.py meli-testar-token
python3 ia_promocoes.py meli-refresh-token
```

`meli-auth` imprime a URL, solicita o `code` localmente sem eco no terminal, troca-o pelos tokens e valida `GET /users/me`. Os tokens nunca são impressos.

Depois de obter um token OAuth válido, teste ainda em modo offline:

```bash
python3 ia_promocoes.py monitorar-precos
python3 ia_promocoes.py status
```

Se continuar recebendo `403`, confira o aplicativo, os escopos, o usuário autorizado e eventuais restrições de IP no portal do Mercado Livre.
