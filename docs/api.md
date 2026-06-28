# API e Integrações

As integrações principais atuais são Mercado Livre, GitHub Pages, Cloudflare Analytics e, localmente, Ollama para o assistente.

O Promogg ainda não possui API autenticada própria para operação administrativa. A API futura será criada em paralelo ao backend atual e versionada desde o início.

## Mercado Livre

Arquivos relacionados:

- `meli_oauth.py`
- `mercadolivre_api.py`
- `login_ml.py`
- `trocar_token_meli.py`

A documentação original de OAuth está preservada em `docs/historico/originais/README_MERCADO_LIVRE_OAUTH.md`.

## API Futura

Versão inicial planejada:

```text
/api/v1
```

Diretrizes:

- todas as rotas privadas exigem autenticação;
- toda ação sensível exige autorização RBAC;
- contratos devem ser estáveis e versionados;
- mudanças incompatíveis devem ir para nova versão;
- respostas devem usar formato padronizado;
- erros não devem expor stack trace, SQL, segredo ou detalhe interno sensível;
- request id deve acompanhar logs e respostas de erro.

## Autenticação

Plano:

- access token JWT curto para chamadas API;
- refresh token opaco, rotativo e armazenado em hash;
- refresh token enviado em cookie `HttpOnly`, `Secure` e `SameSite`;
- sessões persistidas e revogáveis;
- logout revoga sessão;
- troca de senha, MFA ou suspeita de incidente revoga sessões relacionadas.

## Autorização

A API deve aplicar RBAC por rota e por ação.

Papéis planejados:

- Administrador
- Operador
- Revisor
- Analista
- Somente leitura

Exemplos de permissões:

- `offers:read`
- `offers:review`
- `offers:edit`
- `offers:publish`
- `workers:start`
- `workers:stop`
- `analytics:read`
- `audit:read`
- `users:manage`
- `roles:manage`
- `secrets:manage`
- `deploy:run`
- `rollback:run`

## Erros Padronizados

Formato planejado:

```json
{
  "ok": false,
  "error": {
    "code": "permission_denied",
    "message": "Ação não permitida.",
    "request_id": "req_..."
  }
}
```

Regras:

- mensagens externas devem ser seguras e curtas;
- detalhes técnicos ficam apenas em logs sanitizados;
- falhas de autenticação e autorização devem ser auditadas;
- erro de validação deve apontar campos inválidos sem ecoar segredo.

## Segurança de API

Controles obrigatórios para `/api/v1`:

- CORS restrito aos domínios oficiais.
- CSP forte no painel administrativo.
- CSRF para rotas mutáveis quando cookies forem usados.
- Rate limiting por IP, usuário, rota e ação sensível.
- Validação de entrada por schema.
- Sanitização de saída pública.
- Proteção contra SQL Injection com queries parametrizadas ou ORM seguro.
- Proteção contra XSS com escape padrão e sanitização de HTML.
- Uploads seguros com allowlist, limite de tamanho e storage isolado.
- HTTPS obrigatório em produção.

## Integrações Externas

OAuth2 Google/GitHub para login administrativo deve usar Authorization Code Flow com PKCE. A identidade externa será vinculada a usuário interno; papéis e permissões continuarão sendo definidos pelo Promogg.

Secrets de integrações devem vir de variáveis de ambiente em desenvolvimento e Secret Manager em produção. Nunca devem ser hardcoded ou enviados ao Git.
