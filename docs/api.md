# API e Integrações

As integrações principais são Mercado Livre, GitHub Pages, Cloudflare Analytics e, localmente, Ollama para o assistente.

## Mercado Livre

Arquivos relacionados:

- `meli_oauth.py`
- `mercadolivre_api.py`
- `login_ml.py`
- `trocar_token_meli.py`

A documentação original de OAuth está preservada em `docs/historico/originais/README_MERCADO_LIVRE_OAUTH.md`.

## Diretrizes Futuras de API

- Versionar rotas públicas quando houver API HTTP.
- Validar e sanitizar todas as entradas.
- Usar CORS restritivo em produção.
- Nunca retornar stack trace ao cliente.
- Padronizar erros internos e mascarar detalhes sensíveis.
- Adicionar rate limiting.

## Autenticação Futura

O roadmap prevê JWT, OAuth2 Google/GitHub, MFA, RBAC e hashing com bcrypt ou Argon2.
