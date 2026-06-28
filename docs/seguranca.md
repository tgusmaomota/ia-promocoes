# Segurança

A arquitetura de segurança aprovada para o Promogg tem como pilares:

1. Confidencialidade
2. Integridade
3. Disponibilidade
4. Autenticidade
5. Auditoria
6. Rastreabilidade

Este documento descreve o estado atual, os riscos conhecidos e a arquitetura futura planejada. Ele não representa implementação completa de autenticação, RBAC, MFA ou API autenticada.

## Status dos Controles

| Controle | Status | Observação |
|---|---|---|
| Segredos fora do Git | Implementado | `.env`, tokens, banco, logs, backups e perfis locais são ignorados. |
| Catálogo público sanitizado | Implementado | `catalogo_publico/ofertas.json` é validado antes da publicação. |
| Deploy com bloqueio de catálogo vazio | Implementado | Validações impedem publicação sem ofertas suficientes. |
| Serviços locais em `127.0.0.1` | Parcial | Site local, analytics e painel remoto foram desenhados para não abrir porta pública diretamente. |
| Cloudflare Access para painel remoto | Parcial | Documentado e auditado, mas depende de configuração externa. |
| Auditoria operacional sanitizada | Parcial | Há `sistema_eventos` e logs sanitizados, mas ainda sem identidade forte por usuário. |
| Rate limiting de analytics | Parcial | Limite simples por item/evento/minuto. |
| JWT e refresh token | Planejado | Ainda não implementado. |
| Sessões seguras | Planejado | Ainda não há tabela formal de sessões de usuário. |
| RBAC | Planejado | Ainda não há usuários, papéis ou permissões internas. |
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

- `Strict-Transport-Security`
- `Content-Security-Policy`
- `X-Content-Type-Options`
- `Referrer-Policy`
- `Permissions-Policy`

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
