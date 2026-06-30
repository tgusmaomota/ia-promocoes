# API e Integrações

As integrações principais atuais são Mercado Livre, GitHub Pages, Cloudflare Analytics e, localmente, Ollama para o assistente.

O Promogg ainda não possui API autenticada própria para operação administrativa. Este documento define o contrato inicial planejado da API `/api/v1` antes de implementar backend, mantendo CLI, Streamlit, banco SQLite e site estático intactos.

## Estado

- Status deste documento: contrato planejado.
- Backend API: esqueleto read-only inicial criado em paralelo, com endurecimento básico de segurança.
- Autenticação própria: rotas experimentais existem somente para desenvolvimento local e ficam inativas por padrão.
- RBAC próprio: experimental persistente, aplicado somente ao router local `/api/v1/auth/*` em development.
- Painel atual: continua sendo Streamlit/local.
- CLI atual: continua sendo `ia_promocoes.py`.
- Fonte inicial da API: `catalogo_publico/ofertas.json`.
- Banco SQLite: não é consultado pela API read-only inicial.
- Banco de autenticação experimental: separado do `banco.db`, usado apenas quando `PROMOGG_ENV=development` e `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true`.
- RBAC experimental: só atua quando `PROMOGG_ENV=development`, `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true` e `PROMOGG_RBAC_ENABLED=true`; produção continua sem auth/RBAC ativo.

## Execução Local da API Read-only

Comando planejado para desenvolvimento local:

```bash
uvicorn api_promogg.main:app --host 127.0.0.1 --port 8001 --reload
```

Comando oficial pelo CLI:

```bash
python3 ia_promocoes.py api
```

Smoke test interno sem depender de servidor rodando:

```bash
python3 ia_promocoes.py api-teste
```

Smoke test seguro da autenticação experimental local:

```bash
python3 ia_promocoes.py auth-teste
```

Essa API inicial é paralela ao fluxo existente. Ela não substitui CLI, Streamlit, geração do site, GitHub Pages ou banco SQLite.

O CLI usa `127.0.0.1` e porta `8001` por padrão. `--host` e `--porta` são aceitos, mas `0.0.0.0` é bloqueado para evitar exposição acidental antes de autenticação real.

`auth-teste` usa `TestClient`, banco temporário em `/tmp` e variáveis experimentais somente no processo do comando. Ele testa login, `/me`, refresh, logout, senha incorreta, ausência de dados sensíveis nas respostas e produção 404 em auth. A saída segura esperada é apenas `AUTH_TESTE=ok`.

Com RBAC experimental ligado, somente o router `/api/v1/auth/*` consulta o autorizador persistente. `/auth/me` e `/auth/logout` exigem sessão válida, e `/auth/refresh` exige refresh token e sessão válidos. Nenhuma permissão administrativa é aplicada ainda porque não há rotas operacionais mutáveis nesta fase.

## Testes Automatizados

A API read-only possui testes de contrato e segurança em `tests/test_api_readonly.py`.

Cobertura atual:

- health básico e detalhado;
- listagem e detalhe de ofertas;
- listagem de categorias;
- comando `api-teste` do CLI;
- comando `auth-teste` do CLI;
- auth experimental com RBAC desligado preservando o fluxo atual;
- auth experimental com RBAC ligado negando sessão inválida e usuário inativo/bloqueado;
- validação padronizada para parâmetros inválidos;
- `NOT_FOUND` padronizado;
- preservação de `X-Request-ID`;
- presença de `request_id` em erros;
- headers de segurança;
- CORS padrão sem wildcard.

Comando:

```bash
python3 -m pytest tests/test_api_readonly.py
```

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

- `X-Content-Type-Options: nosniff`: implementado na API read-only.
- `Referrer-Policy: no-referrer`: implementado na API read-only.
- `X-Frame-Options: DENY`: implementado na API read-only.
- `Permissions-Policy`: implementado com política restritiva na API read-only.
- `Cache-Control: no-store`: implementado na API read-only.
- `Strict-Transport-Security`: planejado para ambiente HTTPS de produção.
- `Content-Security-Policy`: planejado para painel HTML; não aplicado agora porque a API atual retorna JSON puro.

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

## Logs Seguros

A API read-only registra log mínimo por requisição:

- `request_id`;
- método HTTP;
- path sem query string;
- status code;
- tempo de resposta em milissegundos.

Os logs não devem registrar token, cookie, `Authorization`, query sensível ou payload sensível. Como a fase atual é somente leitura e sem corpo de escrita, nenhum payload é logado.

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

Limitações atuais:

- não há login utilizável em produção;
- as rotas `/api/v1/auth/*` respondem 404 fora de desenvolvimento local com feature flag experimental ligada;
- RBAC só está ativo no router experimental de auth em development; MFA ainda não está ativo;
- não há rotas mutáveis;
- a API read-only não consulta o banco SQLite;
- CORS padrão não usa `"*"`.

## Autenticação Experimental Local

As rotas abaixo existem apenas para preparar a integração futura de autenticação. Elas são registradas no app, mas retornam `404 Not Found` quando qualquer condição não for satisfeita:

- `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true`;
- `PROMOGG_ENV=development`.

Ambientes `production`, `staging` ou qualquer valor desconhecido continuam sem endpoints de autenticação ativos. Essa funcionalidade não deve ser usada em produção.

Rotas experimentais:

- `POST /api/v1/auth/login`;
- `POST /api/v1/auth/logout`;
- `POST /api/v1/auth/refresh`;
- `GET /api/v1/auth/me`.

Contrato das Fases 5A/6B:

- `login` usa `ExperimentalAuthService` e o banco `auth_dev.db` ou `PROMOGG_AUTH_DB_PATH`;
- não cria admin automático nem usuário hardcoded;
- não retorna senha, hash, refresh token hash ou refresh token no JSON;
- refresh token opaco é persistido apenas como hash e enviado em cookie experimental `HttpOnly`;
- `refresh` aceita token opaco no corpo JSON ou cookie, nunca em query string, rotaciona o token e revoga a sessão em caso de reuso;
- `logout` revoga a sessão e expira o cookie experimental;
- `me` retorna apenas dados mínimos de usuário e sessão;
- com `PROMOGG_RBAC_ENABLED=true`, `/me` e `/logout` exigem sessão válida, e `/refresh` exige refresh/sessão válidos;
- se `PROMOGG_AUTH_ENABLED=true`, `PROMOGG_JWT_ENABLED=true` e `PROMOGG_JWT_SIGNING_KEY` estiver definido em `development`, login/refresh podem emitir access credential experimental;
- não protege rotas read-only;
- não altera Streamlit, CLI, catálogo público, GitHub Pages ou workflows;
- usa apenas sessão experimental, refresh token opaco e banco experimental configurável por `PROMOGG_AUTH_DB_PATH`;
- permanece desligada por padrão.

## Credenciais e Cookies Experimentais

A Fase 5A conecta esses contratos apenas ao router experimental `/api/v1/auth/*` em `development`:

- produção continua sem `/api/v1/auth/*`, sem JWT, sem cookies e sem autenticação ativa;
- nenhuma rota read-only foi protegida;
- o cookie experimental de refresh é `HttpOnly`, `SameSite=Lax` e `Secure` quando a requisição usa HTTPS;
- CSRF permanece desligado por padrão, mas pode emitir cookie/header experimental em development;
- `PROMOGG_JWT_ENABLED` permanece `false` por padrao;
- producao continua sem emissao de tokens ou cookies, mesmo com configuracao parcial.

Os modulos internos sao:

- `api_promogg/auth/credentials.py`: contratos `AccessCredential`, `RefreshCredential` e `CredentialProvider`;
- `api_promogg/auth/jwt_provider.py`: provider JWT experimental, apenas para uso interno futuro;
- `api_promogg/auth/cookies.py`: helpers que retornam especificacoes de cookies para uso controlado pelo router experimental.
- `api_promogg/auth/auth_facade.py`: fachada experimental para emissão, renovação, revogação e validação via `CredentialProvider`.

A fachada é usada pelo router experimental somente para access credential em development, sempre bloqueando emissão fora de `PROMOGG_ENV=development` ou sem as flags `PROMOGG_AUTH_ENABLED`, `PROMOGG_AUTH_EXPERIMENTAL_ENABLED` e `PROMOGG_JWT_ENABLED`.

Configuracoes previstas:

- `PROMOGG_JWT_ISSUER`;
- `PROMOGG_JWT_AUDIENCE`;
- `PROMOGG_JWT_SIGNING_KEY`;
- `PROMOGG_JWT_ACCESS_TTL`;
- `PROMOGG_JWT_REFRESH_TTL`;
- `PROMOGG_JWT_ALGORITHM`.

## Resumo dos Endpoints

O mapa abaixo é contratual. As rotas `GET` read-only estão implementadas; rotas mutáveis permanecem apenas planejadas e não existem na API atual.

| Método | Path | Status | Exposição | Autenticação | Permissão futura | MFA | Auditoria |
|---|---|---|---|---|---|---|---|
| GET | `/api/v1/health` | Implementado read-only | Pública | Não | Nenhuma | Não | Não |
| GET | `/api/v1/health/detalhada` | Implementado read-only | Pública nesta fase; privada no futuro | Não nesta fase | `workers:read` ou `system:admin` para detalhes sensíveis | Não | Futura |
| GET | `/api/v1/ofertas` | Implementado read-only | Pública para dados sanitizados | Não para público | `offers:read` se visão privada | Não | Não público; futura se privado |
| GET | `/api/v1/ofertas/{oferta_id}` | Implementado read-only | Pública para dados sanitizados | Não para público | `offers:read` se visão privada | Não | Não público; futura se privado |
| GET | `/api/v1/categorias` | Implementado read-only | Pública | Não | `catalog:read` se visão privada | Não | Não público; futura se privado |
| POST | `/api/v1/auth/login` | Experimental local, 404 por padrão | Local development | Experimental | Nenhuma nesta fase | Não | Sim, experimental |
| POST | `/api/v1/auth/logout` | Experimental local, 404 por padrão | Local development | Sessão experimental | Nenhuma nesta fase | Não | Sim, experimental |
| POST | `/api/v1/auth/refresh` | Experimental local, 404 por padrão | Local development | Refresh opaco experimental | Nenhuma nesta fase | Não | Sim, experimental |
| GET | `/api/v1/auth/me` | Experimental local, 404 por padrão | Local development | Sessão experimental | Nenhuma nesta fase | Não | Não nesta fase |
| POST | `/api/v1/auth/login` | Futuro | Pública | Não | Nenhuma | Pode exigir etapa MFA | Sim |
| POST | `/api/v1/auth/refresh` | Futuro | Pública com cookie seguro | Cookie refresh | Nenhuma | Não | Sim |
| POST | `/api/v1/auth/logout` | Futuro | Autenticada | Sim | Nenhuma | Não | Sim |
| GET | `/api/v1/auth/me` | Futuro | Autenticada | Sim | Nenhuma | Não | Sim |
| GET | `/api/v1/users` | Futuro | Autenticada | Sim | `users:read` ou `users:manage` | Sim para consulta ampla | Sim |
| POST | `/api/v1/users` | Futuro | Autenticada | Sim | `users:manage` | Sim | Sim |
| PATCH | `/api/v1/users/{id}` | Futuro | Autenticada | Sim | `users:manage` | Sim | Sim |
| GET | `/api/v1/roles` | Futuro | Autenticada | Sim | `roles:manage` ou `audit:read` | Sim para consulta ampla | Sim |
| PATCH | `/api/v1/users/{id}/roles` | Futuro | Autenticada | Sim | `roles:manage` | Sim | Sim |
| GET | `/api/v1/audit/events` | Futuro | Autenticada | Sim | `audit:read` | Sim para exportação/amplo | Sim |
| POST | `/api/v1/operations/coleta` | Futuro | Autenticada | Sim | `workers:run` | Não por padrão; sim para Playwright/confiável | Sim |
| POST | `/api/v1/operations/curadoria` | Futuro | Autenticada | Sim | `offers:review` | Não | Sim |
| POST | `/api/v1/operations/publicar-site` | Futuro | Autenticada | Sim | `site:deploy` ou `catalog:generate` | Sim para deploy real | Sim |
| POST | `/api/v1/operations/publicar-telegram` | Futuro | Autenticada | Sim | `telegram:publish` ou `offers:publish` | Sim | Sim |
| POST | `/api/v1/operations/parar-producao` | Futuro | Autenticada | Sim | `workers:stop` | Sim | Sim |

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

- Status: implementado read-only inicial.
- Autenticação: não nesta fase; sim no futuro.
- Permissão RBAC: futura `health:read`.
- MFA: não.
- Auditoria: futura.
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

- Status: implementado read-only inicial.
- Autenticação: não para dados públicos; sim para campos privados futuros.
- Permissão RBAC: nenhuma nesta fase; futura `offers:read` para visão privada.
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

- Status: implementado read-only inicial.
- Autenticação: não para dados públicos; sim para campos privados futuros.
- Permissão RBAC: nenhuma nesta fase; futura `offers:read` para visão privada.
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

- Status: implementado read-only inicial.
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
