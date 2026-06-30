# Modelo de Identidade, Sessões, Permissões e Auditoria

Este documento define o desenho da Fase 3A e a base técnica isolada da Fase 3B. Ainda não há login real, JWT, tabela de usuários, migração de banco, rotas mutáveis ou autenticação aplicada à API read-only.

## Princípios

- Implementar autenticação somente depois de contrato, dados sensíveis, lifecycle e auditoria estarem definidos.
- Guardar apenas hashes de segredos de autenticação.
- Nunca logar senha, access token, refresh token, cookie, secret, código OAuth, TOTP secret, recovery code ou token de reset.
- Usar `request_id`, `session_id` e `user_id` para rastreabilidade.
- Exigir MFA para administradores e ações críticas.
- Revogar sessões quando houver troca de senha, reuso de refresh token, alteração crítica de papel ou suspeita de incidente.

## Entidades Futuras

### `users`

| Campo | Tipo planejado | Observação |
|---|---|---|
| `id` | string/uuid | Identificador público interno, ex: `usr_...`. |
| `email` | string | Normalizado em lowercase; único. |
| `email_verified_at` | timestamp nullable | Confirmação de e-mail. |
| `password_hash` | string nullable | Hash Argon2id preferencialmente; bcrypt aceitável. |
| `name` | string nullable | Nome de exibição. |
| `status` | enum | `pending`, `active`, `disabled`, `locked`. |
| `failed_login_count` | integer | Contador para bloqueio progressivo. |
| `locked_until` | timestamp nullable | Bloqueio temporário. |
| `last_login_at` | timestamp nullable | Último login bem-sucedido. |
| `password_changed_at` | timestamp nullable | Usado para invalidar sessões antigas. |
| `created_at` / `updated_at` | timestamp | Controle operacional. |
| `disabled_at` | timestamp nullable | Desativação. |

- Campos sensíveis: `email`, `password_hash`, estado de bloqueio.
- Nunca em logs: `password_hash`, senha recebida, tokens de reset, códigos MFA.
- Índices: único em `email`; índice em `status`; índice em `created_at`.
- Retenção: manter enquanto a conta existir; após desativação, reter trilha mínima para auditoria conforme política operacional.
- Criptografia/hash: senha sempre com Argon2id ou bcrypt; e-mail pode exigir criptografia em repouso no banco futuro.
- Segurança: desativar usuário deve revogar sessões e refresh tokens ativos.

### `roles`

| Campo | Tipo planejado | Observação |
|---|---|---|
| `id` | string/uuid | Identificador do papel. |
| `name` | string | Ex: Administrador, Operador, Revisor. |
| `description` | string | Descrição curta. |
| `is_system` | boolean | Papel nativo não removível. |
| `created_at` / `updated_at` | timestamp | Controle operacional. |

- Campos sensíveis: nenhum segredo, mas papéis revelam estrutura de autorização.
- Nunca em logs: não registrar payload completo se contiver alterações amplas; registrar antes/depois sanitizado.
- Índices: único em `name`.
- Retenção: papéis de sistema permanentes; papéis removidos devem permanecer referenciáveis na auditoria.
- Criptografia/hash: não aplicável.
- Segurança: alteração de papel exige `roles:manage`, MFA e auditoria.

### `permissions`

| Campo | Tipo planejado | Observação |
|---|---|---|
| `id` | string/uuid | Identificador interno. |
| `code` | string | Ex: `offers:read`. |
| `description` | string | Finalidade. |
| `risk_level` | enum | `low`, `medium`, `high`, `critical`. |
| `requires_mfa` | boolean | MFA obrigatório por permissão. |
| `created_at` / `updated_at` | timestamp | Controle operacional. |

- Campos sensíveis: permissões críticas indicam superfície administrativa.
- Nunca em logs: não logar dumps extensos de políticas; registrar códigos alterados.
- Índices: único em `code`; índice em `risk_level`.
- Retenção: permissões devem ser versionáveis; remoção exige migração cuidadosa.
- Criptografia/hash: não aplicável.
- Segurança: permissões críticas devem ter teste de autorização antes de implementação.

### `user_roles`

| Campo | Tipo planejado | Observação |
|---|---|---|
| `user_id` | string/uuid | Referência a `users`. |
| `role_id` | string/uuid | Referência a `roles`. |
| `granted_by` | string/uuid nullable | Usuário que concedeu o papel. |
| `granted_at` | timestamp | Data de concessão. |
| `revoked_at` | timestamp nullable | Revogação lógica. |

- Campos sensíveis: vínculo usuário-papel.
- Nunca em logs: e-mail + matriz completa desnecessária; preferir ids e papéis alterados.
- Índices: composto em `user_id, role_id`; índice em `role_id`; índice em `revoked_at`.
- Retenção: histórico de concessão/revogação deve ser mantido para auditoria.
- Criptografia/hash: não aplicável.
- Segurança: mudança em papel administrativo deve revogar sessões ou exigir reautenticação/MFA.

### `sessions`

| Campo | Tipo planejado | Observação |
|---|---|---|
| `id` | string/uuid | `session_id` usado em JWT e auditoria. |
| `user_id` | string/uuid | Dono da sessão. |
| `status` | enum | `active`, `revoked`, `expired`, `compromised`. |
| `created_at` | timestamp | Criação. |
| `last_seen_at` | timestamp | Último uso. |
| `expires_at` | timestamp | Expiração absoluta. |
| `revoked_at` | timestamp nullable | Revogação. |
| `revocation_reason` | string nullable | Motivo sanitizado. |
| `ip_hash` | string nullable | Hash/HMAC do IP aproximado. |
| `user_agent_hash` | string nullable | Hash do User Agent. |
| `mfa_verified_at` | timestamp nullable | MFA recente. |

- Campos sensíveis: `ip_hash`, `user_agent_hash`, `session_id`.
- Nunca em logs: cookies, refresh token, IP bruto quando não necessário.
- Índices: `user_id, status`; `expires_at`; `last_seen_at`.
- Retenção: sessões ativas até expiração; sessões revogadas retidas para auditoria por período definido.
- Criptografia/hash: IP e User Agent devem ser hash/HMAC quando persistidos; banco com criptografia em repouso.
- Segurança: sessão comprometida revoga toda família de refresh tokens.

### `refresh_tokens`

| Campo | Tipo planejado | Observação |
|---|---|---|
| `id` | string/uuid | Identificador interno. |
| `session_id` | string/uuid | Sessão associada. |
| `token_hash` | string | Hash do refresh token opaco. |
| `family_id` | string/uuid | Família para rotação e detecção de reuso. |
| `previous_token_id` | string/uuid nullable | Encadeamento de rotação. |
| `created_at` | timestamp | Criação. |
| `used_at` | timestamp nullable | Primeiro uso. |
| `expires_at` | timestamp | Expiração. |
| `revoked_at` | timestamp nullable | Revogação. |
| `reuse_detected_at` | timestamp nullable | Reuso detectado. |

- Campos sensíveis: `token_hash`, `family_id`, vínculo com sessão.
- Nunca em logs: refresh token bruto, cookie, hash completo.
- Índices: único em `token_hash`; `session_id`; `family_id`; `expires_at`.
- Retenção: tokens expirados/revogados retidos pelo período necessário para detectar reuso e investigar incidentes.
- Criptografia/hash: token opaco aleatório; persistir somente hash forte/HMAC.
- Segurança: reuso de refresh token antigo revoga a família inteira e marca a sessão como comprometida.

### `audit_events`

| Campo | Tipo planejado | Observação |
|---|---|---|
| `id` | string/uuid | Identificador do evento. |
| `created_at` | timestamp | Timestamp UTC. |
| `actor_user_id` | string/uuid nullable | Usuário autenticado, quando existir. |
| `actor_session_id` | string/uuid nullable | Sessão associada. |
| `action` | string | Ex: `auth.login.success`. |
| `permission` | string nullable | Permissão usada. |
| `resource_type` | string | Ex: `offer`, `site`, `secret`. |
| `resource_id` | string nullable | Identificador do recurso. |
| `result` | enum | `success`, `failure`, `blocked`, `error`. |
| `reason` | string nullable | Motivo sanitizado. |
| `request_id` | string | Correlação HTTP/logs. |
| `ip_hash` | string nullable | Hash/HMAC do IP. |
| `user_agent_hash` | string nullable | Hash do User Agent. |
| `metadata` | json nullable | Metadados sanitizados. |

- Campos sensíveis: `metadata`, identificadores de usuário/sessão, hashes de rede.
- Nunca em logs: senha, token, cookie, secret, payload bruto, antes/depois com dados sensíveis.
- Índices: `created_at`; `actor_user_id, created_at`; `action, created_at`; `resource_type, resource_id`; `request_id`.
- Retenção: maior que logs comuns; definir janela mínima para investigação e conformidade operacional.
- Criptografia/hash: banco com criptografia em repouso; IP/User Agent em hash/HMAC.
- Segurança: preferir append-only; alterações/correções devem gerar novo evento.

### `mfa_factors`

| Campo | Tipo planejado | Observação |
|---|---|---|
| `id` | string/uuid | Identificador do fator. |
| `user_id` | string/uuid | Usuário dono. |
| `type` | enum | `totp`, futuro `webauthn`. |
| `secret_encrypted` | string nullable | Segredo TOTP criptografado. |
| `recovery_codes_hash` | json nullable | Hash dos recovery codes. |
| `enabled_at` | timestamp nullable | Ativação. |
| `disabled_at` | timestamp nullable | Desativação. |
| `last_used_at` | timestamp nullable | Último uso. |

- Campos sensíveis: `secret_encrypted`, recovery codes.
- Nunca em logs: segredo TOTP, QR code, recovery codes, códigos digitados.
- Índices: `user_id`; `type`; `enabled_at`.
- Retenção: fatores desativados retidos com metadados mínimos para auditoria.
- Criptografia/hash: TOTP secret criptografado; recovery codes somente hash.
- Segurança: ativar/desativar MFA gera auditoria; desativar MFA exige MFA recente ou procedimento administrativo forte.

### `password_reset_tokens`

| Campo | Tipo planejado | Observação |
|---|---|---|
| `id` | string/uuid | Identificador interno. |
| `user_id` | string/uuid | Usuário dono. |
| `token_hash` | string | Hash do token de reset. |
| `created_at` | timestamp | Criação. |
| `expires_at` | timestamp | Expiração curta. |
| `used_at` | timestamp nullable | Uso. |
| `revoked_at` | timestamp nullable | Revogação. |
| `request_ip_hash` | string nullable | Hash/HMAC do IP solicitante. |

- Campos sensíveis: `token_hash`, vínculo de reset.
- Nunca em logs: token bruto, link de reset completo, hash completo.
- Índices: único em `token_hash`; `user_id`; `expires_at`.
- Retenção: curta após expiração/uso; manter evento de auditoria sem token.
- Criptografia/hash: token opaco; persistir somente hash forte/HMAC.
- Segurança: uso de reset revoga sessões existentes e refresh tokens.

### `oauth_accounts`

| Campo | Tipo planejado | Observação |
|---|---|---|
| `id` | string/uuid | Identificador interno. |
| `user_id` | string/uuid | Usuário vinculado. |
| `provider` | string | `google`, `github`, futuro. |
| `provider_subject` | string | `sub`/id do provedor. |
| `email_at_provider` | string nullable | E-mail informado pelo provedor. |
| `linked_at` | timestamp | Vínculo. |
| `last_login_at` | timestamp nullable | Último login pelo provedor. |
| `status` | enum | `active`, `disabled`. |

- Campos sensíveis: `provider_subject`, e-mail externo.
- Nunca em logs: access token do provedor, refresh token do provedor, ID token bruto, código OAuth.
- Índices: único em `provider, provider_subject`; índice em `user_id`.
- Retenção: vínculo ativo enquanto a conta existir; histórico mínimo após desvincular.
- Criptografia/hash: tokens de provedor não devem ser persistidos nesta fase; se futuramente necessários, usar cofre/criptografia.
- Segurança: OAuth autentica identidade; papéis continuam vindo do RBAC interno.

## Lifecycle de Sessão

### Login

1. Receber credenciais ou retorno OAuth em rota futura.
2. Validar entrada sem logar senha, código OAuth ou payload bruto.
3. Aplicar rate limit por IP, usuário e rota.
4. Em sucesso, registrar `auth.login.success`; em falha, registrar `auth.login.failure` com motivo genérico.
5. Se MFA for obrigatório, criar estado intermediário curto e retornar `MFA_REQUIRED`.

### Criação de Sessão

1. Criar `sessions` com `status=active`, `user_id`, expiração absoluta e hashes de IP/User Agent.
2. Emitir access token curto com `sub`, `session_id`, papéis/permissões mínimas, `iat`, `exp`, `iss`, `aud`.
3. Criar refresh token opaco rotativo em `refresh_tokens`.
4. Enviar refresh token apenas em cookie `HttpOnly`, `Secure`, `SameSite`.

### Access Token Curto

- Duração recomendada: 5 a 15 minutos.
- Não deve conter segredo nem dado sensível desnecessário.
- Deve ser invalidado por expiração e por revogação de sessão no servidor.

### Refresh Token Rotativo

1. Cliente chama rota futura de refresh com cookie seguro.
2. Servidor compara hash do token.
3. Se válido e não usado, marca `used_at`, emite novo access token e novo refresh token da mesma família.
4. Token antigo nunca volta a ser aceito.

### Reuso de Refresh Token

1. Se token antigo já usado aparecer de novo, marcar `reuse_detected_at`.
2. Revogar a família de refresh tokens.
3. Marcar sessão como `compromised`.
4. Registrar `auth.refresh.reused`.
5. Exigir novo login e, para usuário crítico, MFA/revisão administrativa.

### Logout

- Revogar sessão atual e refresh tokens ativos.
- Limpar cookie de refresh.
- Registrar `auth.logout`.

### Troca de Senha

- Validar senha atual ou token de reset.
- Atualizar `password_hash` e `password_changed_at`.
- Revogar sessões e refresh tokens existentes, exceto sessão corrente se política permitir.
- Registrar `auth.password.changed`.

### Ativação de MFA

- Gerar segredo TOTP, validar primeiro código e só então ativar.
- Armazenar segredo criptografado e recovery codes com hash.
- Registrar `auth.mfa.enabled`.
- Exigir MFA recente para desativar ou regenerar recovery codes.

### Revogação de Sessão

- Pode ocorrer por logout, troca de senha, desativação de usuário, alteração crítica de papel, suspeita de incidente ou reuso de refresh token.
- Deve registrar motivo sanitizado em `sessions.revocation_reason` e evento de auditoria.

### Expiração

- Access token expira rapidamente.
- Refresh token expira por janela absoluta e por rotação.
- Sessão expira por tempo absoluto e pode ter expiração por inatividade.

### Bloqueio por Tentativas

- Incrementar contador em falhas de login.
- Aplicar atraso progressivo e `locked_until`.
- Não revelar se e-mail existe.
- Registrar falhas agregáveis sem senha ou payload.

## Permissões Futuras

| Permissão | Descrição | Risco | MFA |
|---|---|---|---|
| `offers:read` | Ler ofertas e detalhes compatíveis com o papel. | Baixo | Não |
| `offers:review` | Aprovar ou rejeitar ofertas. | Médio/Alto | Não por padrão |
| `offers:edit` | Editar ou ocultar ofertas. | Alto | Conforme ação |
| `offers:publish` | Publicar oferta em canais públicos. | Alto | Sim |
| `catalog:read` | Ler catálogo público/operacional. | Baixo | Não |
| `catalog:generate` | Gerar ou preparar catálogo/site. | Médio/Alto | Conforme publicação |
| `telegram:publish` | Publicar no Telegram. | Alto | Sim |
| `site:deploy` | Fazer deploy do site. | Alto | Sim |
| `workers:read` | Ver status de workers/serviços. | Baixo | Não |
| `workers:run` | Iniciar execução operacional. | Alto | Sim em produção |
| `workers:stop` | Parar produção ou worker. | Alto | Sim |
| `analytics:read` | Ler métricas e analytics. | Baixo/Médio | Não |
| `audit:read` | Ler auditoria. | Alto | Sim para exportação/amplo |
| `users:read` | Listar/consultar usuários. | Médio | Sim para consulta ampla |
| `users:manage` | Criar, desativar ou alterar usuários. | Crítico | Sim |
| `roles:manage` | Alterar papéis e permissões. | Crítico | Sim |
| `secrets:manage` | Alterar segredos e integrações. | Crítico | Sim |
| `backup:create` | Criar backup manual. | Médio | Não por padrão |
| `backup:restore` | Restaurar backup. | Crítico | Sim |
| `system:admin` | Administração sensível do sistema. | Crítico | Sim |

## Eventos Mínimos de Auditoria

| Evento | Ação | Resultado | Dados permitidos | Nunca registrar |
|---|---|---|---|---|
| Login sucesso | `auth.login.success` | `success` | `user_id`, `session_id`, `request_id`, hashes de IP/User Agent | senha, token |
| Login falha | `auth.login.failure` | `failure` | e-mail normalizado ou hash, motivo genérico | senha, existência da conta |
| Logout | `auth.logout` | `success` | `user_id`, `session_id` | cookie, refresh token |
| Refresh usado | `auth.refresh.used` | `success` | `session_id`, `family_id` parcial/sanitizado | refresh token, hash completo |
| Refresh reusado | `auth.refresh.reused` | `blocked` | `session_id`, `family_id` parcial, motivo | refresh token |
| Senha alterada | `auth.password.changed` | `success` | `user_id`, método | senha, hash |
| MFA ativado/desativado | `auth.mfa.enabled` / `auth.mfa.disabled` | `success` | `user_id`, tipo | segredo, QR code, recovery code |
| Papel alterado | `rbac.role.changed` | `success` | usuário alvo, papéis antes/depois sanitizados | payload bruto |
| Oferta aprovada/rejeitada/editada | `offers.reviewed` / `offers.edited` | `success` | oferta, decisão, motivo, antes/depois sanitizado | dados sensíveis, tokens |
| Publicação Telegram | `telegram.published` | `success`/`failure` | oferta, canal, resultado | token Telegram |
| Deploy site | `site.deployed` | `success`/`failure` | versão, commit, destino | secrets de deploy |
| Início/parada de produção | `production.started` / `production.stopped` | `success` | serviço, modo, motivo | env/secrets |
| Restore de backup | `backup.restored` | `success`/`failure` | backup id, checksum, motivo | caminho sensível se expuser usuário/host |
| Alteração de secret | `secrets.changed` | `success` | nome lógico, escopo, ator | valor anterior/novo |
| Acesso a logs | `logs.accessed` | `success` | escopo, filtros, usuário | conteúdo bruto sensível |
| Exportação de dados | `data.exported` | `success` | escopo, formato, motivo | dados exportados no evento |

## Critérios Para Implementação Futura

- Migração/tabelas revisadas antes de qualquer rota de login.
- Testes para rotação e reuso de refresh token.
- Testes para revogação de sessão em troca de senha e alteração crítica de papel.
- Testes de autorização por permissão e MFA.
- Auditoria obrigatória para eventos críticos.
- Documentação operacional de recuperação de conta, revogação e incidente.

## Base Técnica Isolada da Fase 3B

Módulos internos criados em `api_promogg/auth/`:

- `password.py`: hash e verificação de senha com Argon2id via `argon2-cffi`.
- `tokens.py`: geração de token opaco com `secrets`, hash para armazenamento, comparação segura e simulação em memória de refresh token rotativo com detecção de reuso.
- `rbac.py`: papéis e permissões padrão em memória, com checagem por papel único ou múltiplos papéis.
- `audit.py`: modelo simples de evento de auditoria e sanitização de campos sensíveis.

Limites atuais da Fase 3B:

- sem endpoint público de login;
- sem JWT real;
- sem persistência;
- sem criação de tabelas;
- sem proteção das rotas read-only atuais;
- sem mudança no Streamlit, Pages, site estático ou banco SQLite.

Testes:

```bash
python3 -m pytest tests/test_auth_base.py
```

## Persistência Experimental da Fase 3C

A persistência experimental usa SQLite separado do banco operacional:

- caminho padrão: `auth_dev.db`;
- variável de ambiente: `PROMOGG_AUTH_DB_PATH`;
- testes sempre usam banco temporário fora do caminho padrão;
- `banco.db` operacional não é alterado.

Módulos internos:

- `db.py`: resolução de caminho e conexão SQLite com `PRAGMA foreign_keys = ON`.
- `migrations.py`: schema experimental e seeds de papéis/permissões.
- `models.py`: dataclasses simples para leitura de usuário, sessão, papel e permissão.
- `repository.py`: funções de criação e consulta do banco experimental.

Tabelas experimentais:

- `users`;
- `roles`;
- `permissions`;
- `role_permissions`;
- `user_roles`;
- `sessions`;
- `refresh_tokens`;
- `audit_events`;
- `schema_migrations`.

Garantias atuais:

- refresh token é persistido apenas como hash;
- senha é persistida apenas como hash Argon2id recebido pelo repositório;
- auditoria passa por sanitização antes de persistir `metadata`;
- seeds criam apenas papéis e permissões padrão;
- nenhum administrador automático é criado;
- não há senha fixa ou hardcoded;
- não há endpoint público de login;
- rotas read-only continuam sem autenticação.

Teste:

```bash
python3 -m pytest tests/test_auth_persistence.py
```

## Serviço Interno Experimental da Fase 3D

A Fase 3D adiciona `api_promogg/auth/service.py`, uma camada interna que orquestra:

- `repository.py` para persistência experimental;
- `password.py` para hash e verificação Argon2id;
- `tokens.py` para refresh tokens opacos;
- `audit.py` para eventos sanitizados.

Funções cobertas:

- criar usuário experimental com senha hasheada;
- autenticar credenciais em modo interno;
- negar autenticação de usuário inativo/bloqueado;
- criar sessão experimental;
- emitir refresh token opaco;
- rotacionar refresh token;
- detectar reuso e revogar sessão/família;
- logout/revogação de sessão;
- registrar auditoria sanitizada.

Limites atuais:

- sem endpoint público de login;
- sem JWT real;
- sem cookie real;
- sem proteção de `/api/v1/health`, `/api/v1/ofertas` ou `/api/v1/categorias`;
- sem admin automático ou senha hardcoded;
- uso apenas por testes internos.

Teste:

```bash
python3 -m pytest tests/test_auth_service.py
```

## Configuração Central de Segurança

A camada `api_promogg/security/` prepara a configuração comum para toda autenticação futura sem expor endpoint público:

- `settings.py`: centraliza flags e parâmetros lidos de variáveis de ambiente, incluindo `AUTH_ENABLED`, `AUTH_EXPERIMENTAL_ENABLED`, `MFA_ENABLED`, `JWT_ENABLED`, `RBAC_ENABLED`, `AUDIT_ENABLED`, tentativas de login, lockout, TTLs, senha, CORS e hosts;
- `feature_flags.py`: fornece a interface que rotas futuras devem consultar antes de ativar qualquer comportamento experimental;
- `constants.py`: concentra nomes de permissões, papéis, códigos de erro, eventos de auditoria, headers HTTP, cookies e variáveis de ambiente;
- `validators.py`: oferece validadores reutilizáveis para entradas comuns de autenticação e segurança.

Padrões atuais:

- `AUTH_ENABLED=False`;
- `AUTH_EXPERIMENTAL_ENABLED=False`;
- `MFA_ENABLED=False`;
- `JWT_ENABLED=False`;
- `RBAC_ENABLED=False`;
- `AUDIT_ENABLED=True`.

Garantias desta etapa:

- nenhuma rota pública de login foi criada;
- nenhuma rota read-only foi alterada ou protegida;
- nenhum fluxo Streamlit, workflow ou `banco.db` foi alterado;
- futuras rotas de autenticação devem usar essa camada em vez de ler variáveis de ambiente diretamente.

Teste:

```bash
python3 -m pytest tests/test_security_settings.py
```

## Rotas Experimentais Locais da Fase 3E

A Fase 3E registra `api_promogg/routers/auth.py` em `/api/v1/auth/*`, mas todas as rotas retornam `404 Not Found` por padrão. Para ficarem disponíveis, as duas condições abaixo precisam ser verdadeiras:

- `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true`;
- `PROMOGG_ENV=development`.

Qualquer outro cenário, incluindo produção, staging ou ambiente desconhecido, mantém os endpoints inativos. Essa proteção usa a camada central `api_promogg/security/`.

Rotas previstas nesta fase:

- `POST /api/v1/auth/login`;
- `POST /api/v1/auth/logout`;
- `POST /api/v1/auth/refresh`;
- `GET /api/v1/auth/me`.

Limites:

- JWT access credential nao e emitida por padrao;
- não há cookie real de produção;
- não há login utilizável fora do desenvolvimento local;
- rotas read-only continuam públicas e não protegidas;
- o banco operacional `banco.db` não é usado;
- a persistência continua no banco experimental configurável por `PROMOGG_AUTH_DB_PATH`.

Antes de qualquer ativação real, os itens em `docs/auth-production-checklist.md` precisam ser implementados e revisados.

Teste:

```bash
python3 -m pytest tests/test_auth_experimental_routes.py
```

## Infraestrutura de Credenciais da Fase 4A

A Fase 4A adiciona contratos internos para preparar JWT e cookies seguros sem ativar autenticacao:

- `api_promogg/auth/credentials.py`: define `AccessCredential`, `RefreshCredential` e `CredentialProvider`; a aplicacao futura deve depender desses contratos, nao de JWT diretamente.
- `api_promogg/auth/jwt_provider.py`: provider JWT experimental, interno e explicito. Ele documenta issuer, audience, subject, issued_at, expires_at, not_before, token_id, algoritmo permitido, versao do token e claims privadas.
- `api_promogg/auth/cookies.py`: helpers que retornam especificacoes de cookie `HttpOnly`, `Secure`, `SameSite`, `Path`, `Max-Age` e limpeza de logout.

Limites apos Fase 5A:

- `JWT_ENABLED` continua `False` por padrao;
- o provider so emite quando chamado explicitamente em `PROMOGG_ENV=development` com `PROMOGG_JWT_ENABLED=true`;
- producao nao emite JWT mesmo com configuracao parcial;
- apenas o router experimental pode emitir access credential/cookie em development;
- nenhuma autenticacao de producao foi ativada.

Configuracoes novas:

- `PROMOGG_JWT_ISSUER`;
- `PROMOGG_JWT_AUDIENCE`;
- `PROMOGG_JWT_ACCESS_TTL`;
- `PROMOGG_JWT_REFRESH_TTL`;
- `PROMOGG_JWT_ALGORITHM`.

Teste:

```bash
python3 -m pytest tests/test_auth_credentials_infra.py
```

## Fachada de Credenciais da Fase 4B

A Fase 4B adiciona `api_promogg/auth/auth_facade.py` como o unico ponto autorizado para emissao experimental de credenciais.

A fachada usa somente a interface `CredentialProvider`, mantendo a aplicacao desacoplada do formato JWT. Ela cobre:

- emissao de `AccessCredential`;
- emissao de `RefreshCredential`;
- renovacao de credenciais;
- revogacao por `token_id`;
- validacao temporal e de revogacao.

Condicoes obrigatorias antes de qualquer emissao:

- `PROMOGG_AUTH_ENABLED=true`;
- `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true`;
- `PROMOGG_JWT_ENABLED=true`;
- `PROMOGG_JWT_SIGNING_KEY` definido;
- `PROMOGG_ENV=development`;
- provider habilitado.

A recusa ocorre antes de chamar o provider, evitando geracao acidental de token quando qualquer flag ou ambiente bloqueia. A partir da Fase 5A, somente o router experimental pode chamar a fachada, e apenas para access credential em development.

Limites atuais:

- nenhuma rota retorna JWT por padrao;
- cookies existem apenas no router experimental de development;
- nenhuma autenticacao de producao foi ativada;
- producao continua sem emissao de credenciais, mesmo com configuracao parcial.

Teste:

```bash
python3 -m pytest tests/test_auth_facade.py
```

## CSRF, Cookies e Protecao de Sessao da Fase 4C

A Fase 4C adiciona infraestrutura passiva, sem integracao com routers:

- `api_promogg/security/csrf.py`: helpers para gerar token CSRF, validar token, comparar em tempo constante e respeitar expiracao configuravel.
- `api_promogg/security/origin.py`: validadores de `Origin`, `Host` e `Referer`, com allowlist por ambiente.
- `api_promogg/security/session_security.py`: contratos para rotacao de `session_id` apos login, regeneracao de sessao, invalidacao da sessao antiga, prevencao de session fixation e politicas futuras de idle timeout e absolute timeout.
- `api_promogg/auth/cookies.py`: especificacoes passivas de refresh cookie e CSRF cookie, sem escrever cookies reais.

Configuracoes novas:

- `PROMOGG_CSRF_ENABLED`;
- `PROMOGG_CSRF_COOKIE_NAME`;
- `PROMOGG_CSRF_HEADER_NAME`;
- `PROMOGG_CSRF_TOKEN_TTL`;
- `PROMOGG_SESSION_ROTATION_ENABLED`;
- `PROMOGG_SESSION_IDLE_TIMEOUT`;
- `PROMOGG_SESSION_ABSOLUTE_TIMEOUT`.

Limites atuais:

- CSRF continua desativado por padrao;
- cookies continuam passivos fora do router experimental;
- session fixation ja esta prevista por contrato, mas ainda nao integrada ao servico;
- apenas o router experimental usa parte dessa infraestrutura em development;
- producao continua sem emitir cookies.

Teste:

```bash
python3 -m pytest tests/test_csrf_infra.py
```

## Integracao Experimental Local da Fase 5A

A Fase 5A conecta o router `/api/v1/auth/*` ao servico interno somente quando as duas condicoes sao verdadeiras:

- `PROMOGG_ENV=development`;
- `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true`.

Fora disso, inclusive em producao com flags ligadas, as rotas retornam `404 Not Found`, nao emitem cookies e nao ativam autenticacao.

Rotas:

- `POST /api/v1/auth/login`;
- `POST /api/v1/auth/refresh`;
- `POST /api/v1/auth/logout`;
- `GET /api/v1/auth/me`.

Contrato experimental:

- usa `ExperimentalAuthService` e banco `auth_dev.db` ou `PROMOGG_AUTH_DB_PATH`;
- nao cria admin automatico nem senha hardcoded;
- nao retorna senha, hash, refresh token hash ou refresh token bruto no JSON;
- login cria sessao experimental e refresh token opaco, persistido apenas como hash;
- refresh token e enviado por cookie experimental `HttpOnly`, `SameSite=Lax` e `Secure` quando a requisicao usa HTTPS;
- `refresh` nao aceita refresh token em URL, rotaciona token a cada uso e revoga a sessao quando detecta reuso;
- `logout` revoga sessao e prepara expiracao do cookie;
- `me` retorna apenas dados minimos de usuario e sessao;
- access credential experimental so e emitida se `PROMOGG_AUTH_ENABLED=true`, `PROMOGG_JWT_ENABLED=true` e `PROMOGG_JWT_SIGNING_KEY` estiver configurado em development;
- rotas read-only continuam publicas;
- `banco.db`, Streamlit e workflows permanecem inalterados.

Testes:

```bash
python3 -m pytest tests/test_auth_experimental_routes.py tests/test_auth_experimental_security.py
```

## RBAC Persistente Experimental da Fase 6A

A Fase 6A conecta papéis e permissões ao banco experimental de autenticação, sem proteger rotas públicas atuais e sem ativar produção.

Componentes:

- `AuthRepository.garantir_seeds_papeis_permissoes()`: reaplica seeds padrão de papéis/permissões de forma idempotente;
- `AuthRepository.atribuir_papel_usuario(user_id, role_name, granted_by=None)`;
- `AuthRepository.remover_papel_usuario(user_id, role_name)`;
- `AuthRepository.listar_papeis_usuario(user_id)`;
- `AuthRepository.listar_permissoes_efetivas_usuario(user_id)`;
- `PersistentRBACAuthorizer.list_user_permissions(user_id)`;
- `PersistentRBACAuthorizer.has_permission(user_id, permission)`;
- `PersistentRBACAuthorizer.has_any_permission(user_id, permissions)`;
- `PersistentRBACAuthorizer.has_all_permissions(user_id, permissions)`.

Regras:

- nega por padrão quando usuário, papel ou permissão não existe;
- nega para usuário inativo, bloqueado ou desabilitado;
- nega fora de `PROMOGG_ENV=development` com `PROMOGG_RBAC_ENABLED=true`;
- não cria admin hardcoded;
- não altera `/health`, `/ofertas`, `/categorias`;
- não toca no `banco.db`.

Teste:

```bash
python3 -m pytest tests/test_rbac_persistence.py
```
