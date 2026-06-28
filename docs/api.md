# API e Integrações

As integrações principais atuais são Mercado Livre, GitHub Pages, Cloudflare Analytics e, localmente, Ollama para o assistente.

O Promogg ainda não possui API autenticada própria para operação administrativa. Este documento define o contrato inicial planejado da API `/api/v1` antes de implementar backend, mantendo CLI, Streamlit, banco SQLite e site estático intactos.

## Estado

- Status deste documento: contrato planejado.
- Backend API: ainda não implementado.
- Autenticação própria: ainda não implementada.
- RBAC próprio: ainda não implementado.
- Painel atual: continua sendo Streamlit/local.
- CLI atual: continua sendo `ia_promocoes.py`.

## Mercado Livre

Arquivos relacionados:

- `meli_oauth.py`
- `mercadolivre_api.py`
- `login_ml.py`
- `trocar_token_meli.py`

A documentação original de OAuth está preservada em `docs/historico/originais/README_MERCADO_LIVRE_OAUTH.md`.

## Versionamento

A versão inicial planejada é:

```text
/api/v1
```

Política:

- contratos de `/api/v1` não devem quebrar clientes antigos sem aviso e janela de migração;
- mudanças incompatíveis devem ir para `/api/v2`;
- campos novos podem ser adicionados em respostas de `/api/v1` quando forem compatíveis;
- remoção ou mudança de semântica de campo exige nova versão;
- endpoints experimentais devem ser marcados como planejados ou internos antes de uso em produção.

## Headers Obrigatórios

Requisições:

- `X-Request-ID`: recomendado pelo cliente; se ausente, a API deve gerar um.
- `Content-Type: application/json`: obrigatório em requisições com corpo.
- `Authorization: Bearer <token>`: futuro, obrigatório para rotas privadas quando autenticação existir.

Respostas:

- `X-Request-ID`: sempre presente.
- `Content-Type: application/json`.
- CORS restrito aos domínios oficiais.

Headers de segurança planejados para painel/API:

- `Strict-Transport-Security`
- `Content-Security-Policy`
- `X-Content-Type-Options`
- `Referrer-Policy`
- `Permissions-Policy`

## Padrão de Resposta

Sucesso:

```json
{
  "data": {},
  "request_id": "req_..."
}
```

Lista paginada:

```json
{
  "data": [],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 751
  },
  "request_id": "req_..."
}
```

Erro:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dados inválidos.",
    "request_id": "req_..."
  }
}
```

Regras:

- erros nunca devem expor stack trace, SQL, token, cookie, secret, `.env` ou detalhe interno sensível;
- falhas de autenticação e autorização devem gerar auditoria;
- erros de validação podem indicar campos inválidos, sem ecoar segredo;
- `request_id` deve correlacionar resposta, logs e auditoria.

## Códigos de Erro

| Código | HTTP | Uso |
|---|---:|---|
| `VALIDATION_ERROR` | 400 | Parâmetro, corpo ou formato inválido. |
| `UNAUTHENTICATED` | 401 | Token ausente, expirado ou inválido. |
| `FORBIDDEN` | 403 | Usuário autenticado sem permissão RBAC. |
| `MFA_REQUIRED` | 403 | Ação exige MFA recente. |
| `NOT_FOUND` | 404 | Recurso inexistente ou não visível para o papel. |
| `CONFLICT` | 409 | Estado incompatível com a ação. |
| `RATE_LIMITED` | 429 | Limite excedido. |
| `INTERNAL_ERROR` | 500 | Falha inesperada mascarada. |
| `SERVICE_UNAVAILABLE` | 503 | Sistema em manutenção, offline ou dependência indisponível. |

## Segurança de API

Controles obrigatórios para `/api/v1`:

- autenticação em todas as rotas privadas;
- autorização RBAC em toda ação sensível;
- CORS restrito aos domínios oficiais;
- CSP forte no painel administrativo;
- CSRF para rotas mutáveis quando cookies forem usados;
- rate limiting por IP, usuário, rota e ação sensível;
- validação de entrada por schema;
- sanitização de saída pública;
- proteção contra SQL Injection com queries parametrizadas ou ORM seguro;
- proteção contra XSS com escape padrão e sanitização de HTML;
- uploads seguros com allowlist, limite de tamanho e storage isolado quando existirem;
- HTTPS obrigatório em produção.

## Resumo dos Endpoints

| Método | Path | Status | Auth | Permissão | MFA | Auditoria |
|---|---|---|---|---|---|---|
| GET | `/api/v1/health` | Fase inicial | Não | Nenhuma | Não | Não |
| GET | `/api/v1/health/detalhada` | Fase inicial | Sim | `health:read` | Não | Sim |
| GET | `/api/v1/ofertas` | Fase inicial | Não para dados públicos | `offers:read` se privado | Não | Não público; sim privado |
| GET | `/api/v1/ofertas/{oferta_id}` | Fase inicial | Não para dados públicos | `offers:read` se privado | Não | Não público; sim privado |
| GET | `/api/v1/categorias` | Fase inicial | Não | Nenhuma | Não | Não |
| POST | `/api/v1/auth/login` | Futuro | Não | Nenhuma | Pode exigir | Sim |
| POST | `/api/v1/auth/refresh` | Futuro | Cookie refresh | Nenhuma | Não | Sim |
| POST | `/api/v1/auth/logout` | Futuro | Sim | Nenhuma | Não | Sim |
| GET | `/api/v1/auth/me` | Futuro | Sim | Nenhuma | Não | Sim |
| GET | `/api/v1/users` | Futuro | Sim | `users:manage` | Sim | Sim |
| POST | `/api/v1/users` | Futuro | Sim | `users:manage` | Sim | Sim |
| PATCH | `/api/v1/users/{id}` | Futuro | Sim | `users:manage` | Sim | Sim |
| GET | `/api/v1/roles` | Futuro | Sim | `roles:manage` ou `audit:read` | Sim | Sim |
| PATCH | `/api/v1/users/{id}/roles` | Futuro | Sim | `roles:manage` | Sim | Sim |
| GET | `/api/v1/audit/events` | Futuro | Sim | `audit:read` | Sim para exportação | Sim |
| POST | `/api/v1/operations/coleta` | Futuro | Sim | `collection:run` | Não | Sim |
| POST | `/api/v1/operations/curadoria` | Futuro | Sim | `offers:review` | Não | Sim |
| POST | `/api/v1/operations/publicar-site` | Futuro | Sim | `site:publish` | Sim | Sim |
| POST | `/api/v1/operations/publicar-telegram` | Futuro | Sim | `telegram:publish` | Sim | Sim |
| POST | `/api/v1/operations/parar-producao` | Futuro | Sim | `production:stop` | Sim | Sim |

## Health

### GET `/api/v1/health`

Finalidade: retornar disponibilidade básica da API.

- Status: fase inicial.
- Autenticação: não.
- Permissão RBAC: nenhuma.
- MFA: não.
- Auditoria: não.
- Parâmetros: nenhum.

Resposta:

```json
{
  "data": {
    "ok": true,
    "service": "promogg-api",
    "version": "v1"
  },
  "request_id": "req_..."
}
```

Erros esperados:

- `SERVICE_UNAVAILABLE`
- `INTERNAL_ERROR`

### GET `/api/v1/health/detalhada`

Finalidade: retornar saúde detalhada de banco, workers, catálogo, analytics e integrações.

- Status: fase inicial.
- Autenticação: sim, futura.
- Permissão RBAC: `health:read`.
- MFA: não.
- Auditoria: sim.
- Parâmetros: `include=workers,integrations,storage` opcional.

Resposta:

```json
{
  "data": {
    "estado": "ONLINE",
    "banco": "ok",
    "catalogo_publico": "ok",
    "workers": [],
    "integrations": {
      "mercado_livre": "nao_verificado",
      "telegram": "nao_verificado"
    }
  },
  "request_id": "req_..."
}
```

Erros esperados:

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `SERVICE_UNAVAILABLE`
- `INTERNAL_ERROR`

## Ofertas Públicas e Read-only

### GET `/api/v1/ofertas`

Finalidade: listar ofertas públicas sanitizadas e, no futuro autenticado, permitir visão operacional conforme papel.

- Status: fase inicial.
- Autenticação: não para dados públicos; sim para campos privados futuros.
- Permissão RBAC: nenhuma para público; `offers:read` para visão privada.
- MFA: não.
- Auditoria: não para público; sim para visão privada.
- Parâmetros: `categoria`, `busca`, `limit`, `offset`, `ordenar`, `somente_publicas`.

Resposta:

```json
{
  "data": [
    {
      "oferta_id": "MLB123456",
      "titulo": "Produto exemplo",
      "categoria": "tecnologia",
      "preco": 199.9,
      "url": "https://promogg.com.br/produto/MLB123456/"
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 751
  },
  "request_id": "req_..."
}
```

Erros esperados:

- `VALIDATION_ERROR`
- `RATE_LIMITED`
- `INTERNAL_ERROR`

### GET `/api/v1/ofertas/{oferta_id}`

Finalidade: retornar detalhe público sanitizado de uma oferta.

- Status: fase inicial.
- Autenticação: não para dados públicos; sim para campos privados futuros.
- Permissão RBAC: nenhuma para público; `offers:read` para visão privada.
- MFA: não.
- Auditoria: não para público; sim para visão privada.
- Parâmetros: `oferta_id` no path.

Resposta:

```json
{
  "data": {
    "oferta_id": "MLB123456",
    "titulo": "Produto exemplo",
    "categoria": "tecnologia",
    "preco": 199.9,
    "descricao_curta": "Resumo público sanitizado.",
    "url": "https://promogg.com.br/produto/MLB123456/"
  },
  "request_id": "req_..."
}
```

Erros esperados:

- `NOT_FOUND`
- `VALIDATION_ERROR`
- `RATE_LIMITED`
- `INTERNAL_ERROR`

### GET `/api/v1/categorias`

Finalidade: listar categorias públicas disponíveis.

- Status: fase inicial.
- Autenticação: não.
- Permissão RBAC: nenhuma.
- MFA: não.
- Auditoria: não.
- Parâmetros: nenhum.

Resposta:

```json
{
  "data": [
    {
      "id": "tecnologia",
      "nome": "Tecnologia",
      "total_ofertas": 120
    }
  ],
  "request_id": "req_..."
}
```

Erros esperados:

- `RATE_LIMITED`
- `INTERNAL_ERROR`

## Autenticação Futura

### POST `/api/v1/auth/login`

Finalidade: autenticar usuário interno ou iniciar fluxo compatível com OAuth2 no futuro.

- Status: futuro.
- Autenticação: não.
- Permissão RBAC: nenhuma.
- MFA: pode exigir etapa adicional.
- Auditoria: sim.
- Parâmetros: corpo JSON com `email`, `password` ou provedor futuro.

Resposta:

```json
{
  "data": {
    "mfa_required": false,
    "user": {
      "id": "usr_...",
      "email": "admin@example.com"
    }
  },
  "request_id": "req_..."
}
```

Erros esperados:

- `VALIDATION_ERROR`
- `UNAUTHENTICATED`
- `MFA_REQUIRED`
- `RATE_LIMITED`

### POST `/api/v1/auth/refresh`

Finalidade: emitir novo access token usando refresh token rotativo em cookie seguro.

- Status: futuro.
- Autenticação: cookie refresh `HttpOnly`, `Secure`, `SameSite`.
- Permissão RBAC: nenhuma.
- MFA: não.
- Auditoria: sim.
- Parâmetros: cookie de refresh; sem token no corpo.

Resposta:

```json
{
  "data": {
    "access_token_expires_in": 900
  },
  "request_id": "req_..."
}
```

Erros esperados:

- `UNAUTHENTICATED`
- `CONFLICT`
- `RATE_LIMITED`

### POST `/api/v1/auth/logout`

Finalidade: revogar sessão atual e invalidar refresh token.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: nenhuma.
- MFA: não.
- Auditoria: sim.
- Parâmetros: nenhum.

Resposta:

```json
{
  "data": {
    "logged_out": true
  },
  "request_id": "req_..."
}
```

Erros esperados:

- `UNAUTHENTICATED`
- `INTERNAL_ERROR`

### GET `/api/v1/auth/me`

Finalidade: retornar usuário autenticado, papéis, permissões e estado MFA.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: nenhuma.
- MFA: não.
- Auditoria: sim.
- Parâmetros: nenhum.

Resposta:

```json
{
  "data": {
    "id": "usr_...",
    "email": "admin@example.com",
    "roles": ["Administrador"],
    "permissions": ["users:manage", "roles:manage"],
    "mfa_enabled": true
  },
  "request_id": "req_..."
}
```

Erros esperados:

- `UNAUTHENTICATED`
- `INTERNAL_ERROR`

## RBAC Futuro

### GET `/api/v1/users`

Finalidade: listar usuários administrativos.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `users:manage`.
- MFA: sim.
- Auditoria: sim.
- Parâmetros: `status`, `role`, `limit`, `offset`.

Resposta:

```json
{
  "data": [
    {
      "id": "usr_...",
      "email": "operador@example.com",
      "status": "ativo",
      "roles": ["Operador"]
    }
  ],
  "request_id": "req_..."
}
```

Erros esperados: `UNAUTHENTICATED`, `FORBIDDEN`, `MFA_REQUIRED`, `VALIDATION_ERROR`.

### POST `/api/v1/users`

Finalidade: criar usuário administrativo.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `users:manage`.
- MFA: sim.
- Auditoria: sim.
- Parâmetros: `email`, `roles`, `status`.

Resposta:

```json
{
  "data": {
    "id": "usr_...",
    "email": "novo@example.com",
    "status": "pendente"
  },
  "request_id": "req_..."
}
```

Erros esperados: `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `MFA_REQUIRED`, `CONFLICT`.

### PATCH `/api/v1/users/{id}`

Finalidade: atualizar status ou metadados seguros de um usuário.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `users:manage`.
- MFA: sim.
- Auditoria: sim.
- Parâmetros: `id` no path; corpo com `status` ou campos permitidos.

Resposta:

```json
{
  "data": {
    "id": "usr_...",
    "status": "ativo"
  },
  "request_id": "req_..."
}
```

Erros esperados: `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `MFA_REQUIRED`, `NOT_FOUND`, `CONFLICT`.

### GET `/api/v1/roles`

Finalidade: listar papéis e permissões disponíveis.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `roles:manage` ou `audit:read`.
- MFA: sim.
- Auditoria: sim.
- Parâmetros: nenhum.

Resposta:

```json
{
  "data": [
    {
      "name": "Operador",
      "permissions": ["collection:run", "site:publish"]
    }
  ],
  "request_id": "req_..."
}
```

Erros esperados: `UNAUTHENTICATED`, `FORBIDDEN`, `MFA_REQUIRED`.

### PATCH `/api/v1/users/{id}/roles`

Finalidade: alterar papéis de um usuário.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `roles:manage`.
- MFA: sim.
- Auditoria: sim.
- Parâmetros: `id` no path; corpo com `roles`.

Resposta:

```json
{
  "data": {
    "id": "usr_...",
    "roles": ["Revisor"]
  },
  "request_id": "req_..."
}
```

Erros esperados: `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `MFA_REQUIRED`, `NOT_FOUND`, `CONFLICT`.

## Auditoria

### GET `/api/v1/audit/events`

Finalidade: consultar eventos de auditoria por período, usuário, ação, recurso ou resultado.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `audit:read`.
- MFA: sim para exportação ou consulta ampla.
- Auditoria: sim.
- Parâmetros: `from`, `to`, `actor_id`, `action`, `resource`, `result`, `limit`, `offset`.

Resposta:

```json
{
  "data": [
    {
      "id": "aud_...",
      "actor_id": "usr_...",
      "action": "site.publish",
      "resource": "catalogo_publico",
      "result": "success",
      "created_at": "2026-06-28T12:00:00Z"
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 1
  },
  "request_id": "req_..."
}
```

Erros esperados:

- `VALIDATION_ERROR`
- `UNAUTHENTICATED`
- `FORBIDDEN`
- `MFA_REQUIRED`
- `RATE_LIMITED`

## Operações Futuras

### POST `/api/v1/operations/coleta`

Finalidade: solicitar execução de coleta.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `collection:run`.
- MFA: não por padrão; sim para modo Playwright/confiável.
- Auditoria: sim.
- Parâmetros: `modo`, `dry_run`.

Resposta:

```json
{
  "data": {
    "operation_id": "op_...",
    "status": "queued"
  },
  "request_id": "req_..."
}
```

Erros esperados: `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `MFA_REQUIRED`, `CONFLICT`, `SERVICE_UNAVAILABLE`.

### POST `/api/v1/operations/curadoria`

Finalidade: solicitar curadoria automática ou revisão assistida.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `offers:review`.
- MFA: não.
- Auditoria: sim.
- Parâmetros: `dry_run`, `escopo`, `limite`.

Resposta:

```json
{
  "data": {
    "operation_id": "op_...",
    "status": "queued"
  },
  "request_id": "req_..."
}
```

Erros esperados: `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `CONFLICT`, `SERVICE_UNAVAILABLE`.

### POST `/api/v1/operations/publicar-site`

Finalidade: publicar ou preparar publicação do site público.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `site:publish`.
- MFA: sim para publicação real.
- Auditoria: sim.
- Parâmetros: `dry_run`, `validar_catalogo`, `mensagem`.

Resposta:

```json
{
  "data": {
    "operation_id": "op_...",
    "status": "queued",
    "requires_validation": true
  },
  "request_id": "req_..."
}
```

Erros esperados: `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `MFA_REQUIRED`, `CONFLICT`, `SERVICE_UNAVAILABLE`.

### POST `/api/v1/operations/publicar-telegram`

Finalidade: publicar oferta no Telegram.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `telegram:publish`.
- MFA: sim.
- Auditoria: sim.
- Parâmetros: `oferta_id`, `dry_run`.

Resposta:

```json
{
  "data": {
    "operation_id": "op_...",
    "status": "queued"
  },
  "request_id": "req_..."
}
```

Erros esperados: `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `MFA_REQUIRED`, `NOT_FOUND`, `CONFLICT`.

### POST `/api/v1/operations/parar-producao`

Finalidade: parar produção, scheduler ou automações operacionais.

- Status: futuro.
- Autenticação: sim.
- Permissão RBAC: `production:stop`.
- MFA: sim.
- Auditoria: sim.
- Parâmetros: `motivo`, `escopo`.

Resposta:

```json
{
  "data": {
    "operation_id": "op_...",
    "status": "accepted"
  },
  "request_id": "req_..."
}
```

Erros esperados: `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `MFA_REQUIRED`, `CONFLICT`, `SERVICE_UNAVAILABLE`.

## Autenticação Planejada

Plano:

- access token JWT curto para chamadas API;
- refresh token opaco, rotativo e armazenado em hash;
- refresh token enviado em cookie `HttpOnly`, `Secure` e `SameSite`;
- sessões persistidas e revogáveis;
- logout revoga sessão;
- troca de senha, MFA ou suspeita de incidente revoga sessões relacionadas.

## Autorização Planejada

A API deve aplicar RBAC por rota e por ação.

Papéis planejados:

- Administrador
- Operador
- Revisor
- Analista
- Somente leitura

Referência principal: [RBAC](rbac.md).

## Integrações Externas

OAuth2 Google/GitHub para login administrativo deve usar Authorization Code Flow com PKCE. A identidade externa será vinculada a usuário interno; papéis e permissões continuarão sendo definidos pelo Promogg.

Secrets de integrações devem vir de variáveis de ambiente em desenvolvimento e Secret Manager em produção. Nunca devem ser hardcoded ou enviados ao Git.
