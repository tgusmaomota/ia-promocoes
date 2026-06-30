# Segurança

A arquitetura de segurança aprovada para o Promogg tem como pilares:

1. Confidencialidade
2. Integridade
3. Disponibilidade
4. Autenticidade
5. Auditoria
6. Rastreabilidade

Este documento descreve o estado atual, os riscos conhecidos e a arquitetura futura planejada. Ele não representa implementação completa de autenticação, RBAC, MFA ou API autenticada.

## Documentos da Fase 1

- [Threat Model](threat-model.md)
- [Inventário de Dados](inventario-dados.md)
- [RBAC](rbac.md)
- [Modelo de Identidade e Auditoria](auth-model.md)
- [Checklist de Autenticacao para Producao](auth-production-checklist.md)

## Status dos Controles

| Controle | Status | Observação |
|---|---|---|
| Segredos fora do Git | Implementado | `.env`, tokens, banco, logs, backups e perfis locais são ignorados. |
| Catálogo público sanitizado | Implementado | `catalogo_publico/ofertas.json` é validado antes da publicação. |
| Deploy com bloqueio de catálogo vazio | Implementado | Validações impedem publicação sem ofertas suficientes. |
| Serviços locais em `127.0.0.1` | Parcial | Site local, analytics e painel remoto foram desenhados para não abrir porta pública diretamente. |
| Cloudflare Access para painel remoto | Parcial | Documentado e auditado, mas depende de configuração externa. |
| Auditoria operacional sanitizada | Parcial | Há `sistema_eventos` e logs sanitizados, mas ainda sem identidade forte por usuário. |
| API read-only endurecida | Parcial | `/api/v1` tem testes, headers de segurança, CORS sem wildcard default, erros padronizados e logs mínimos sem query/payload. |
| Modelo de identidade e sessões | Planejado | Entidades, lifecycle, permissões e auditoria futura definidos em `docs/auth-model.md`. |
| Base técnica de auth isolada | Parcial | Hash Argon2id, tokens opacos, RBAC em memória/persistente experimental e sanitização de auditoria existem como módulos internos, sem proteção de rotas read-only. |
| Persistência auth experimental | Parcial | `auth_dev.db` separado, configurável por `PROMOGG_AUTH_DB_PATH`, com schema de usuários/sessões/tokens/auditoria; sem admin automático e sem tocar no `banco.db`. |
| Serviço auth experimental | Parcial | Serviço interno autentica em ambiente experimental local, com sessão, refresh rotativo, reuso e logout; sem produção e sem proteção de rotas read-only. |
| Configuração central de segurança | Parcial | `api_promogg/security/` centraliza settings, feature flags, constantes e validadores para autenticação futura; auth continua desabilitada por padrão. |
| Rotas auth experimentais locais | Parcial | `/api/v1/auth/*` só existe em `PROMOGG_ENV=development` com `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true`; usa cookie/refresh opaco experimental e não funciona em produção. |
| Infraestrutura JWT/cookies | Parcial | Contratos e helpers internos existem; o router experimental pode emitir cookie e access credential em development, mas `JWT_ENABLED` fica desligado por padrão e produção não emite nada. |
| Fachada de credenciais | Parcial | `api_promogg/auth/auth_facade.py` centraliza emissão experimental via `CredentialProvider`, recusando antes de gerar token quando flags/ambiente bloqueiam. |
| CSRF/cookies/sessao | Parcial | Helpers de CSRF, origem e session fixation existem; uso restrito ao router experimental em development, com produção sem cookies. |
| Rate limiting de analytics | Parcial | Limite simples por item/evento/minuto. |
| JWT e refresh token | Parcial | Refresh opaco rotativo existe no laboratório local; JWT access credential ainda não é produção. |
| Sessões seguras | Parcial | Sessões experimentais revogáveis existem em `auth_dev.db`; política definitiva de produção ainda pendente. |
| RBAC | Parcial | Papéis/permissões persistentes existem no banco experimental; `/api/v1/auth/*` usa RBAC apenas em development com flags experimentais ligadas; produção e rotas read-only seguem sem RBAC ativo. |
| OAuth2 Google/GitHub | Planejado | Ainda não implementado para login do Promogg. |
| MFA/TOTP | Planejado | Ainda não implementado. |
| Senhas com Argon2id/bcrypt | Planejado | Ainda não há autenticação por senha no Promogg. |
| PostgreSQL e criptografia em repouso | Planejado | SQLite local segue como banco operacional atual. |
| Docker e CI/CD completo | Planejado | GitHub Pages já existe para site estático; stack de app ainda não. |

## Arquitetura Atual

O Promogg hoje é uma operação local com publicação pública estática.

- `ia_promocoes.py`: CLI principal para coleta, curadoria, validação, publicação e manutenção.
- `painel.py`: painel Streamlit local.
- `painel_remoto.py`: operação remota prevista atrás de Cloudflare Tunnel + Cloudflare Access.
- `banco.py`: SQLite local em `banco.db`.
- `gerar_site.py`: geração local a partir do banco operacional.
- `gerar_site_publico.py`: geração pública a partir de `catalogo_publico/ofertas.json`.
- `validar_catalogo_publico.py`: validação do contrato público.
- `servidor_analytics.py` e `analytics_cloudflare_worker.js`: coleta de eventos públicos sem IP, cookie, e-mail ou identificador pessoal.
- `.github/workflows/pages.yml`: publicação do site estático no GitHub Pages.

O desenho atual separa dados operacionais privados do site público. A publicação pública não deve depender de `.env`, `banco.db`, CSVs locais, logs, cookies, perfis de navegador ou secrets.

## Riscos Atuais

| Pilar | Risco | Impacto |
|---|---|---|
| Confidencialidade | Vazamento de `.env`, `banco.db`, logs, backups ou perfil Playwright. | Exposição de tokens, sessões e dados operacionais. |
| Integridade | Painel e CLI ainda não têm RBAC interno. | Um operador com acesso local pode executar ações críticas. |
| Disponibilidade | SQLite local e processos manuais concentram operação. | Falhas locais podem interromper coleta, painel ou publicação. |
| Autenticidade | Ações operacionais não são vinculadas a usuário autenticado interno. | Autoria depende de contexto local ou Cloudflare Access. |
| Auditoria | Eventos são úteis, mas ainda não são trilha forense completa. | Investigação limitada após incidente. |
| Rastreabilidade | Mudanças em ofertas não têm cadeia completa usuário -> ação -> recurso -> resultado. | Dificuldade de reconstruir decisões. |

## Arquitetura Futura

A evolução recomendada é criar uma aplicação autenticada em paralelo ao fluxo atual, sem mover arquivos Python antes de uma refatoração separada.

Estrutura futura sugerida:

```text
frontend/
api/
auth/
core/
models/
services/
workers/
integrations/
tests/
docs/
```

Responsabilidades planejadas:

- `frontend/`: painel administrativo autenticado.
- `api/`: API HTTP versionada, começando por `/api/v1`.
- `auth/`: usuários, senhas, JWT, refresh tokens, sessões, OAuth2 e MFA.
- `core/`: configuração, segurança, logging, policies e middlewares.
- `models/`: entidades persistidas e contratos.
- `services/`: regras de negócio do Promogg.
- `workers/`: coleta, curadoria, publicação, monitoramento e tarefas assíncronas.
- `integrations/`: Mercado Livre, Telegram, GitHub, Cloudflare e provedores externos.
- `tests/`: testes de unidade, integração, autorização e segurança.

## Autenticação

O modelo detalhado de entidades futuras, lifecycle de sessão, refresh tokens, MFA, reset de senha, OAuth e eventos mínimos de auditoria está em [Modelo de Identidade e Auditoria](auth-model.md). Esta seção resume as regras de segurança que a implementação futura deve seguir.

A base técnica isolada já possui módulos internos para hashing de senha, tokens opacos, RBAC em memória/persistente experimental e auditoria sanitizada. Esses módulos não protegem as rotas read-only atuais nem ativam produção.

A persistência experimental usa banco SQLite separado e ignorado pelo Git. Ela existe para testes e preparação técnica, sem endpoint público de login, sem admin padrão, sem senha hardcoded e sem alteração do banco operacional.

O serviço interno experimental orquestra autenticação em testes com erros genéricos, auditoria sanitizada e revogação em reuso de refresh token. Ele não deve ser exposto em router até a fase de integração planejada.

Antes de qualquer endpoint público de login, a configuração de segurança deve passar por `api_promogg/security/`:

- `settings.py`: lê variáveis de ambiente como `PROMOGG_AUTH_ENABLED`, `PROMOGG_JWT_ENABLED`, TTLs, política de senha, CORS e hosts permitidos;
- `feature_flags.py`: interface única para rotas futuras consultarem `auth_enabled()`, `auth_experimental_enabled()`, `rbac_enabled()`, `mfa_enabled()` e `jwt_enabled()`;
- `constants.py`: nomes oficiais de permissões, papéis, erros, auditoria, headers, cookies e variáveis de ambiente;
- `validators.py`: validação reutilizável de e-mail, senha, nome de usuário, origem CORS, host, request id e tamanho de entrada.

Essa camada ainda não cria rota, não protege endpoint existente e não altera o Streamlit, workflows ou `banco.db`.

As rotas experimentais da Fase 3E existem somente para desenvolvimento local:

- `POST /api/v1/auth/login`;
- `POST /api/v1/auth/logout`;
- `POST /api/v1/auth/refresh`;
- `GET /api/v1/auth/me`.

Elas retornam `404 Not Found` quando `PROMOGG_AUTH_EXPERIMENTAL_ENABLED` não está ligado ou quando `PROMOGG_ENV` não é exatamente `development`. Produção, staging e ambientes desconhecidos continuam sem autenticação ativa, sem cookies e sem `/api/v1/auth/*`. A Fase 5A não altera rotas públicas read-only, não toca no `banco.db` e não deve ser usada em produção.

Em development, `login` usa o serviço experimental e o banco `auth_dev.db` ou `PROMOGG_AUTH_DB_PATH`, grava refresh token apenas como hash, envia refresh opaco em cookie `HttpOnly` com `SameSite=Lax` e `Secure` quando aplicável, e não retorna refresh token no JSON. `refresh` não aceita token em query string, rotaciona o refresh token e revoga a sessão em caso de reuso. `logout` revoga sessão e expira cookie. `me` retorna apenas dados mínimos de usuário e sessão.

O comando `python3 ia_promocoes.py auth-teste` testa esse fluxo de forma local e descartável. Ele usa `TestClient`, força as flags experimentais somente dentro do processo, usa banco temporário em `/tmp`, valida que produção continua 404 em auth e imprime apenas `AUTH_TESTE=ok`, sem senha, token, cookie, signing key ou refresh token.

A Fase 4A prepara infraestrutura interna para credenciais:

- contratos `AccessCredential`, `RefreshCredential` e `CredentialProvider`;
- provider JWT experimental, com algoritmo permitido `HS256`;
- helpers de cookie seguro com `HttpOnly`, `Secure`, `SameSite`, `Path`, `Max-Age` e limpeza.

Esses módulos são usados apenas pelo router experimental em development. Nenhum cookie real é escrito em produção, nenhum JWT é emitido por padrão e produção continua bloqueada.

A Fase 4B cria uma fachada interna para credenciais. Ela recusa emissao quando `PROMOGG_AUTH_ENABLED`, `PROMOGG_AUTH_EXPERIMENTAL_ENABLED` ou `PROMOGG_JWT_ENABLED` nao estao ligados, ou quando `PROMOGG_ENV` nao e `development`. A recusa acontece antes de chamar o provider, reduzindo risco de emissao acidental. Na Fase 5A, somente o router experimental pode usar a fachada e exige `PROMOGG_JWT_SIGNING_KEY` para emitir access credential.

A Fase 4C prepara infraestrutura passiva para CSRF, cookies e protecao de sessao:

- `api_promogg/security/csrf.py`: gera e valida token CSRF com comparacao em tempo constante e expiracao configuravel;
- `api_promogg/security/origin.py`: valida `Origin`, `Host` e `Referer` por allowlist e ambiente;
- `api_promogg/security/session_security.py`: define contratos para rotacao/regeneracao de sessao, invalidacao da sessao antiga, prevencao de session fixation e politicas futuras de idle/absolute timeout;
- `api_promogg/auth/cookies.py`: possui especificacoes passivas para refresh cookie e CSRF cookie.

`CSRF_ENABLED` e `SESSION_ROTATION_ENABLED` continuam desativados por padrao. O uso de cookies/CSRF fica restrito ao router experimental em development; produção continua sem `set_cookie` ou `delete_cookie`.

### JWT

O access token JWT deve ser curto, preferencialmente entre 5 e 15 minutos, e usado para autenticar chamadas à API. Ele deve conter apenas claims necessárias, como `sub`, `session_id`, `roles`, `permissions`, `iat`, `exp`, `iss` e `aud`.

### Refresh Token

O refresh token deve ser opaco, de longa duração, rotacionado a cada uso e armazenado no servidor somente em hash. Reuso de refresh token antigo deve invalidar toda a família da sessão.

### Cookies Seguros

Refresh tokens devem ser enviados em cookie:

- `HttpOnly`: impede leitura por JavaScript.
- `Secure`: obrigatório em produção; só trafega por HTTPS.
- `SameSite=Strict`: preferencial para painel interno.
- `SameSite=Lax`: aceitável quando o fluxo OAuth precisar retornar ao painel.
- `SameSite=None`: evitar; usar apenas se houver necessidade cross-site real e sempre com `Secure`.

### Sessões

Cada login deve criar uma sessão persistida com `session_id`, usuário, IP aproximado, User Agent, data de criação, último uso, expiração e status. Logout, troca de senha, ativação de MFA, suspeita de incidente e rotação crítica devem revogar sessões.

## Autorização RBAC

Toda rota, comando crítico e ação de painel deve exigir permissão explícita.

Na Fase 6B, essa regra é aplicada somente ao router experimental `/api/v1/auth/*` em development. O autorizador experimental persistente usa papéis/permissões do banco de autenticação isolado, exige `PROMOGG_ENV=development`, `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true` e `PROMOGG_RBAC_ENABLED=true`, e nega por padrão fora desse contexto. Produção continua sem auth/RBAC ativo.

`/auth/me` e `/auth/logout` exigem sessão válida; `/auth/refresh` exige refresh token e sessão válidos. As rotas públicas `/health`, `/health/detalhada`, `/ofertas`, `/ofertas/{id}` e `/categorias` continuam abertas e não consultam RBAC.

| Papel | Permissões |
|---|---|
| Administrador | Gerenciar usuários, papéis, secrets, configurações, deploy, rollback, auditoria e todas as ações do sistema. |
| Operador | Rodar coleta, monitoramento, publicação, workers e manutenção operacional sem gerenciar usuários ou secrets. |
| Revisor | Aprovar, rejeitar, editar e comentar ofertas; não publica diretamente sem fluxo autorizado. |
| Analista | Ler métricas, analytics, relatórios, saúde e exportações controladas. |
| Somente leitura | Visualizar painel, catálogo, status e logs sanitizados sem alterar dados. |

Permissões planejadas incluem `offers:read`, `offers:review`, `offers:edit`, `offers:publish`, `workers:start`, `workers:stop`, `analytics:read`, `audit:read`, `users:manage`, `roles:manage`, `secrets:manage`, `deploy:run` e `rollback:run`.

## OAuth2 Google/GitHub

Login via Google e GitHub deve usar Authorization Code Flow com PKCE. OAuth2 autentica a identidade; a autorização continua sendo do RBAC interno do Promogg.

Regras:

- vincular login externo a usuário interno existente;
- restringir por e-mail, domínio ou allowlist quando necessário;
- validar `state`, `nonce`, `redirect_uri`, `iss`, `aud` e expiração;
- nunca conceder papel administrativo apenas porque o provedor autenticou o usuário;
- registrar login, falha, provedor, IP, User Agent e resultado na auditoria.

## MFA/TOTP

MFA planejado:

- TOTP compatível com aplicativos autenticadores;
- segredo TOTP criptografado;
- recovery codes armazenados somente em hash;
- MFA obrigatório para administradores;
- MFA exigido para ações críticas: deploy, rollback, rotação de secrets, alteração de papéis e desativação de MFA.

## Senhas

Senhas devem usar Argon2id preferencialmente. bcrypt é alternativa aceitável. Nunca usar MD5, SHA simples ou hash sem salt.

Política planejada:

- mínimo de 12 caracteres;
- bloqueio de senhas comuns ou vazadas;
- rate limit por IP, usuário e rota;
- bloqueio progressivo por tentativas;
- recuperação por token único, curto e armazenado em hash;
- troca obrigatória após reset, suspeita de incidente ou criação por administrador;
- revogação de sessões após troca de senha.

## Segurança de API

A API futura deve começar em `/api/v1`.

Estado implementado da API read-only:

- somente rotas `GET`;
- fonte exclusiva em `catalogo_publico/ofertas.json`;
- sem consulta ao SQLite;
- sem login, JWT, refresh token, sessão, RBAC ou MFA;
- testes automatizados em `tests/test_api_readonly.py`;
- CORS por allowlist e bloqueio de wildcard na configuração padrão;
- logs de requisição com `request_id`, método, path sem query, status code e duração;
- sem log de token, cookie, authorization, query sensível ou payload.

Controles obrigatórios:

- autenticação em todas as rotas privadas;
- autorização RBAC em todas as ações;
- CORS restrito aos domínios oficiais;
- CSP forte no painel;
- CSRF para mutações quando houver cookies;
- rate limiting por IP, usuário, rota e ação sensível;
- validação de entrada por schema;
- sanitização de saída pública;
- SQL sempre parametrizado ou via ORM seguro;
- proteção contra XSS por escape padrão e sanitização de HTML;
- erros padronizados sem stack trace;
- uploads com allowlist de MIME/extensão, limite de tamanho, storage isolado e varredura quando aplicável.

Headers planejados:

- `X-Content-Type-Options`: implementado na API read-only.
- `Referrer-Policy`: implementado na API read-only.
- `X-Frame-Options`: implementado na API read-only.
- `Permissions-Policy`: implementado na API read-only.
- `Cache-Control`: implementado como `no-store` na API read-only.
- `Strict-Transport-Security`: planejado para HTTPS em produção.
- `Content-Security-Policy`: planejado para painel HTML; não aplicado agora para JSON puro.

## Banco

Estado atual: SQLite local em `banco.db`, fora do Git, com backups locais antes de migrações relevantes.

Estado futuro:

- PostgreSQL gerenciado para produção;
- criptografia em repouso pelo provedor ou volume criptografado;
- backups automáticos;
- teste periódico de restore;
- retenção definida por classe de dado;
- migrações versionadas;
- allowlist de rede para acesso ao banco;
- trilha de auditoria append-only.

## Logs e Auditoria

Auditoria futura deve registrar:

- quem fez: `user_id`, e-mail, papel e sessão;
- quando: timestamp com timezone;
- de onde: IP, User Agent e request id;
- o quê: ação, recurso e identificador;
- resultado: sucesso, falha, bloqueio ou erro;
- motivo: justificativa quando aplicável;
- antes/depois quando seguro e necessário.

Eventos mínimos obrigatórios estão definidos em `docs/auth-model.md` e incluem login sucesso/falha, logout, refresh token usado/reusado, senha alterada, MFA ativado/desativado, papel alterado, revisão/edição de oferta, publicação Telegram, deploy, início/parada de produção, restore de backup, alteração de secret, acesso a logs e exportação de dados.

Nunca registrar:

- senha;
- token;
- refresh token;
- cookie;
- segredo;
- código OAuth;
- chave de API;
- conteúdo bruto de `.env`.

## Secrets

Estado atual: variáveis de ambiente e `.env` local fora do Git.

Estado futuro:

- Secret Manager em produção;
- secrets separados por ambiente;
- rotação periódica;
- rotação imediata após incidente;
- acesso mínimo necessário;
- mascaramento em logs e CI;
- nenhuma credencial hardcoded.

## Deploy e Infraestrutura

Requisitos futuros:

- HTTPS obrigatório;
- Cloudflare com DNS, WAF, rate limiting e regras de firewall;
- Cloudflare Access como camada adicional para painel administrativo, quando aplicável;
- banco em rede privada com allowlist;
- backup automático antes de migrações;
- rollback por imagem, tag ou release;
- ambientes separados: desenvolvimento, staging e produção;
- CI com validações, testes, varredura de secrets e checagens de segurança.

## Docker

Estrutura planejada:

- `backend`: API autenticada.
- `frontend`: painel administrativo.
- `worker`: coleta, curadoria, publicação e tarefas assíncronas.
- `db`: PostgreSQL apenas em desenvolvimento; produção deve usar serviço gerenciado.
- `redis`: sessões, filas e rate limiting.
- `analytics`: endpoint ou worker de eventos.

Containers devem usar usuário não-root quando possível, variáveis de ambiente para configuração, healthchecks e volumes restritos.

## Monitoramento

Métricas e alertas planejados:

- disponibilidade do painel, API e site;
- latência e erros 4xx/5xx;
- falhas de autenticação;
- bloqueios por rate limit;
- tentativas de CSRF/CORS inválidas;
- alterações de RBAC;
- deploys, rollbacks e falhas de publicação;
- volume anormal de eventos analytics;
- falhas de workers;
- tentativas de acesso a rotas administrativas.

## Dados que Nunca Devem Ir Para o Git

- `.env`
- tokens OAuth
- cookies
- sessões Playwright/Chrome
- `banco.db`
- logs operacionais
- perfis de navegador
- backups de banco
- CSVs temporários
- arquivos de sessão
- chaves privadas
