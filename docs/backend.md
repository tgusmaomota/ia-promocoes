# Backend

O backend atual é composto por scripts Python, serviços locais e painel Streamlit. A entrada principal é `ia_promocoes.py`, que expõe comandos de operação, validação, curadoria, publicação e manutenção.

Ainda não existe uma API autenticada própria do Promogg. A autenticação e autorização internas serão criadas em paralelo ao backend atual, sem interromper CLI, Streamlit local, geração estática e GitHub Pages.

## Áreas Principais

- Coleta e captura: `coletor_mercadolivre.py`, `coletor_mercadolivre_api.py`, `captura_hibrida.py`.
- Curadoria e score: `curadoria_automatica.py`, `ia_revisora.py`, `auditoria_score.py`.
- Afiliados: `gerador_afiliados_oficial.py`, `gerador_link_mercadolivre.py`.
- Catálogo e integridade: `catalogo_integridade.py`, `qualidade_catalogo.py`, `integridade_paginas_produto.py`.
- Assistente local: `promogg_assistente.py`, documentado originalmente em `docs/historico/originais/README_ASSISTENTE_OLLAMA.md`.
- Analytics: `analytics_promogg.py`, `servidor_analytics.py`.
- Serviços locais: `servicos_promogg.py`, `servidor_site.py`, `painel.py`, `painel_remoto.py`.

## Estado Atual

- A operação é local e comandada por CLI/Streamlit.
- O banco operacional é SQLite em `banco.db`.
- O painel Streamlit deve rodar localmente ou atrás de Cloudflare Tunnel + Cloudflare Access.
- O site público é estático e gerado a partir de catálogo sanitizado.
- A auditoria atual registra eventos operacionais, mas ainda não há identidade forte por usuário interno.

## API Autenticada Planejada

A API será criada em paralelo, começando por `/api/v1`. A primeira etapa é read-only e usa somente `catalogo_publico/ofertas.json`, sem consultar `banco.db` e sem implementar autenticação real.

O desenho de autenticação futura está em `docs/auth-model.md`. Ele define entidades de usuários, papéis, permissões, sessões, refresh tokens, MFA, reset de senha, contas OAuth e eventos de auditoria antes de qualquer implementação de login/JWT.

A base técnica isolada de autenticação fica em `api_promogg/auth/` e cobre hash Argon2id, tokens opacos, rotação simulada de refresh token, RBAC em memória e sanitização de auditoria. Ela ainda não é ligada às rotas, não cria tabelas, não protege endpoints read-only e não implementa login real.

A persistência experimental da Fase 3C usa SQLite separado (`auth_dev.db` por padrão, ou `PROMOGG_AUTH_DB_PATH`) para preparar usuários, sessões, refresh tokens e auditoria. Esse banco não é o `banco.db` operacional, é ignorado pelo Git, não cria admin automático e não ativa autenticação nas rotas existentes.

O serviço interno experimental em `api_promogg/auth/service.py` une repository, password, tokens e audit para autenticação local controlada pelo router experimental. Ele usa somente `auth_dev.db` ou `PROMOGG_AUTH_DB_PATH`, não cria admin automático, não toca no `banco.db` e não protege as rotas read-only atuais.

A configuração central de segurança fica em `api_promogg/security/`. Ela concentra feature flags, TTLs, política de senha, allowlists de CORS/hosts, nomes de permissões, papéis, erros, eventos de auditoria, headers, cookies, variáveis de ambiente e validadores reutilizáveis. Futuras rotas de autenticação devem consultar `feature_flags.py` e `settings.py`, evitando configuração espalhada pelo projeto. Por padrão, `PROMOGG_AUTH_ENABLED` e `PROMOGG_AUTH_EXPERIMENTAL_ENABLED` permanecem desligados.

A Fase 5A integra as rotas experimentais em `/api/v1/auth/*` somente quando `PROMOGG_ENV=development` e `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true`. Fora disso, inclusive em produção com flags ligadas, elas continuam 404. Login, refresh, logout e me usam sessão experimental, refresh token opaco com hash persistido e cookie `HttpOnly` local; JWT access credential só é emitida em development quando `PROMOGG_AUTH_ENABLED`, `PROMOGG_JWT_ENABLED` e `PROMOGG_JWT_SIGNING_KEY` também estão configurados.

A Fase 4A adiciona infraestrutura de credenciais em `api_promogg/auth/credentials.py`, `api_promogg/auth/jwt_provider.py` e `api_promogg/auth/cookies.py`. Esses módulos preparam contratos para access credential, refresh credential, provider de credenciais, claims JWT experimentais e especificações de cookies seguros. Na Fase 5A, apenas o router experimental usa parte dessa infraestrutura em development; `JWT_ENABLED` permanece desligado por padrão e produção não emite JWT/cookies.

A Fase 4B adiciona `api_promogg/auth/auth_facade.py`, a fachada interna para emissão experimental de credenciais. Ela é o único ponto autorizado para emissão, renovação, revogação e validação de credenciais e opera via `CredentialProvider`. A fachada exige `PROMOGG_AUTH_ENABLED=true`, `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true`, `PROMOGG_JWT_ENABLED=true` e `PROMOGG_ENV=development`; na Fase 5A, apenas o router experimental pode chamá-la.

A Fase 4C adiciona helpers para CSRF, validação de origem/host/referer e proteção contra session fixation em `api_promogg/security/`. Na Fase 5A, o router experimental pode usar cookies/CSRF apenas em development; produção segue sem cookies reais e `CSRF_ENABLED`/`SESSION_ROTATION_ENABLED` continuam desligados por padrão.

Objetivos:

- preservar o backend atual durante a transição;
- iniciar com rotas somente leitura e health checks;
- adicionar autenticação JWT e refresh token seguro;
- aplicar RBAC em ações críticas;
- padronizar validação, erros, logs, auditoria e rate limiting;
- permitir que o painel futuro consuma a API em vez de executar comandos diretamente.

Endurecimento atual da API read-only:

- testes automatizados em `tests/test_api_readonly.py`;
- headers de segurança em todas as respostas JSON;
- logs mínimos com `request_id`, método, path, status code e duração;
- CORS restrito por allowlist, sem wildcard na configuração padrão;
- erros padronizados com `request_id`.

Comando local planejado para a API read-only:

```bash
uvicorn api_promogg.main:app --host 127.0.0.1 --port 8001 --reload
```

Comandos oficiais no CLI:

```bash
python3 ia_promocoes.py api
python3 ia_promocoes.py api-teste
```

`api` inicia o Uvicorn localmente em `127.0.0.1:8001` por padrão e bloqueia `0.0.0.0`. `api-teste` usa chamada interna com `TestClient`, valida health, ofertas, categorias, `X-Request-ID`, erro `NOT_FOUND` padronizado e ausência de rotas mutáveis.

Rotas iniciais:

- `GET /api/v1/health`
- `GET /api/v1/health/detalhada`
- `GET /api/v1/ofertas`
- `GET /api/v1/ofertas/{oferta_id}`
- `GET /api/v1/categorias`

Rotas experimentais locais, inativas por padrão:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

Validação de testes:

```bash
python3 -m pytest tests/test_api_readonly.py
```

## Assistente

O assistente usa dados públicos e regras locais para responder perguntas sobre ofertas. A documentação original foi preservada em `docs/historico/originais/README_ASSISTENTE_OLLAMA.md`.

## Boas Práticas

- Não logar tokens, senhas, cookies, secrets ou URLs sensíveis.
- Usar consultas parametrizadas no SQLite.
- Validar dados antes de publicar.
- Manter comandos destrutivos protegidos por simulação, backup ou aprovação explícita.
- Não expor Streamlit diretamente na internet.
- Não adicionar autenticação parcial como remendo antes da base de sessões, usuários, RBAC e auditoria.
