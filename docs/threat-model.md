# Threat Model

Este documento inicia a Fase 1 de segurança do Promogg. Ele prepara a futura implementação de autenticação, autorização, auditoria e segurança sem alterar código.

## Escopo

Inclui:

- operação local por CLI e Streamlit;
- banco SQLite operacional;
- catálogo público versionado;
- site estático publicado;
- integrações Mercado Livre, Telegram, GitHub Pages e Cloudflare;
- analytics público;
- futuros backend API, autenticação, RBAC, auditoria e workers.

Fora do escopo nesta fase:

- implementação de autenticação;
- mudança de banco;
- alteração de workflow;
- movimentação de arquivos;
- deploy de infraestrutura.

## Ativos Protegidos

| Ativo | Descrição | Criticidade |
|---|---|---:|
| `.env` | Tokens, IDs, secrets e flags locais. | Crítica |
| `banco.db` | Produtos, postagens, histórico, eventos e dados operacionais. | Crítica |
| Perfis de navegador | Sessões Playwright/Chrome e estado de login. | Crítica |
| Tokens Mercado Livre | Access token, refresh token, client secret e code OAuth. | Crítica |
| Tokens Telegram | Bot token e IDs de chat. | Alta |
| Dados de afiliado | IDs, links e fluxos de geração de afiliado. | Alta |
| Catálogo público | `catalogo_publico/ofertas.json`. | Média |
| Site público | Artefato estático publicado em `promogg.com.br`. | Média |
| Painel Streamlit | Interface operacional com ações críticas. | Alta |
| CLI operacional | Comandos de coleta, publicação, deploy, backup e restauração. | Alta |
| Logs e auditoria | Eventos, erros, status e evidências operacionais. | Alta |
| Backups | Snapshots do banco e configuração sanitizada. | Alta |
| GitHub Pages/workflow | Pipeline de publicação pública. | Alta |
| Analytics | Eventos agregados de cliques sem identificador pessoal. | Média |
| Futura API | Rotas administrativas e públicas versionadas. | Crítica |

## Atores Legítimos

| Ator | Objetivo legítimo | Acesso esperado |
|---|---|---|
| Administrador | Governar usuários, secrets, deploy, rollback e segurança. | Total, com MFA e auditoria. |
| Operador | Rodar coleta, produção, publicação e manutenção. | Operacional, sem gerenciar usuários/secrets. |
| Revisor | Avaliar, editar, aprovar e rejeitar ofertas. | Fluxos de curadoria. |
| Analista | Consultar analytics, relatórios e saúde. | Leitura analítica. |
| Somente leitura | Visualizar painel e status sanitizado. | Leitura restrita. |
| GitHub Actions | Gerar e publicar site estático. | Repositório e Pages, sem secrets operacionais locais. |
| Cloudflare | Proteger DNS, WAF, Access, Tunnel e analytics. | Camada de borda configurada. |
| Worker/automação | Executar coleta, monitoramento e publicação. | Permissões mínimas por tarefa. |

## Atores Maliciosos

| Ator | Motivação | Capacidade provável |
|---|---|---|
| Visitante externo | Explorar site público ou analytics. | Requisições HTTP, abuso de payload e scraping. |
| Bot automatizado | Spam, DDoS leve, abuso de endpoints. | Alto volume de requisições. |
| Atacante com acesso ao host | Roubar banco, `.env`, perfis e backups. | Leitura/escrita local. |
| Operador mal-intencionado | Alterar publicação ou ocultar rastros. | Acesso legítimo abusado. |
| Conta GitHub comprometida | Alterar catálogo, workflow ou Pages. | Push, PR, secrets do GitHub. |
| Provedor externo comprometido | Afetar OAuth, Telegram, Cloudflare ou ML. | Controle parcial de integração. |
| Atacante de cadeia de suprimentos | Inserir dependência ou ação maliciosa. | Mudanças em dependências/workflows. |
| Usuário sem MFA | Conta tomada por senha fraca ou phishing. | Login legítimo comprometido. |

## Superfícies de Ataque

| Superfície | Estado atual | Risco principal |
|---|---|---|
| Site público estático | Publicado via GitHub Pages. | XSS por dado público mal sanitizado, catálogo adulterado. |
| Analytics público | Endpoint local ou Cloudflare Worker. | Abuse, payload inválido, volume excessivo. |
| Painel Streamlit | Local ou atrás de Cloudflare Access. | Exposição direta, ausência de RBAC interno. |
| CLI `ia_promocoes.py` | Execução local. | Comandos críticos sem identidade de usuário. |
| SQLite `banco.db` | Arquivo local ignorado no Git. | Exfiltração, corrupção ou restauração indevida. |
| `.env` | Local, ignorado. | Vazamento de tokens e secrets. |
| Perfis Playwright/Chrome | Locais, ignorados. | Roubo de sessão. |
| Git/GitHub | Código, docs, catálogo e workflow. | Push indevido, secret em commit, alteração de workflow. |
| Mercado Livre OAuth | Tokens em `.env`. | Roubo/uso indevido de refresh token. |
| Telegram | Bot token e chat IDs. | Publicações indevidas. |
| Backups/logs | Locais, ignorados. | Vazamento de dados operacionais. |
| Futura API `/api/v1` | Planejada. | Auth bypass, CSRF, CORS, injeção, XSS, brute force. |

## Ameaças por Pilar

### Confidencialidade

| Ameaça | Severidade | Mitigação planejada | Prioridade |
|---|---:|---|---:|
| Vazamento de `.env` com tokens e secrets. | Crítica | Secret Manager, rotação, varredura de secrets, menor privilégio. | P0 |
| Exfiltração de `banco.db`. | Crítica | PostgreSQL gerenciado, criptografia em repouso, backups criptografados, allowlist. | P0 |
| Roubo de perfil Playwright/Chrome. | Alta | Isolamento do perfil, permissões de filesystem, rotação de sessões, não sincronizar perfil. | P1 |
| Logs com segredo por erro de implementação. | Alta | Sanitização centralizada, testes de vazamento, mascaramento em auditoria. | P1 |
| Exposição direta do painel Streamlit. | Alta | Cloudflare Access, API autenticada, RBAC interno, HTTPS obrigatório. | P0 |

### Integridade

| Ameaça | Severidade | Mitigação planejada | Prioridade |
|---|---:|---|---:|
| Alteração indevida de ofertas. | Alta | RBAC, auditoria, MFA para ações críticas, histórico antes/depois. | P0 |
| Publicação indevida no Telegram ou site. | Alta | Permissões `telegram:publish` e `site:publish`, aprovação, MFA para produção. | P0 |
| Catálogo público adulterado. | Alta | Validação de contrato, revisão, assinatura/hash futuro, CI com bloqueios. | P1 |
| Workflow alterado para vazar dados. | Crítica | Proteção de branch, revisão obrigatória, permissões mínimas, secret scanning. | P0 |
| Restauração de backup incorreto. | Alta | Permissão específica, MFA, dry-run, registro de origem e checksum. | P1 |

### Disponibilidade

| Ameaça | Severidade | Mitigação planejada | Prioridade |
|---|---:|---|---:|
| Corrupção ou perda do SQLite. | Alta | Backups automáticos, restore testado, migração planejada para PostgreSQL. | P0 |
| Abuso de analytics com alto volume. | Média | Rate limiting por IP/rota/evento, WAF, filas. | P1 |
| Falha de worker de coleta/publicação. | Média | Healthchecks, supervisor, alertas, retry controlado. | P2 |
| Indisponibilidade do GitHub Pages ou Cloudflare. | Média | Monitoramento, plano de fallback, rollback de release. | P2 |
| Comando operacional destrutivo acidental. | Alta | Dry-run, confirmação, RBAC, auditoria e backups antes da ação. | P1 |

### Autenticidade

| Ameaça | Severidade | Mitigação planejada | Prioridade |
|---|---:|---|---:|
| Ação sem identidade de usuário interno. | Alta | Usuários, sessões, JWT, auditoria por `user_id`. | P0 |
| Conta administrativa tomada. | Crítica | MFA obrigatório, alertas de login, revogação de sessão, recovery seguro. | P0 |
| OAuth externo vinculado a usuário errado. | Alta | PKCE, `state`, vínculo explícito, allowlist e revisão de domínio/e-mail. | P1 |
| Token JWT roubado. | Alta | Access token curto, refresh rotativo, revogação por sessão, cookies seguros. | P1 |

### Auditoria

| Ameaça | Severidade | Mitigação planejada | Prioridade |
|---|---:|---|---:|
| Evento crítico sem registro suficiente. | Alta | Auditoria obrigatória por ação crítica. | P0 |
| Log adulterado por operador. | Alta | Auditoria append-only, exportação para serviço externo/SIEM futuro. | P1 |
| Registro com segredo acidental. | Alta | Sanitização, mascaramento e testes. | P1 |
| Falta de correlação entre request, usuário e recurso. | Média | `request_id`, `session_id`, `resource_id` e trilha antes/depois. | P1 |

### Rastreabilidade

| Ameaça | Severidade | Mitigação planejada | Prioridade |
|---|---:|---|---:|
| Não conseguir reconstruir publicação indevida. | Alta | Cadeia usuário -> ação -> recurso -> resultado -> deploy. | P0 |
| Não saber qual dado gerou uma oferta publicada. | Média | Registrar origem, versão do catálogo e snapshot sanitizado. | P2 |
| Backup restaurado sem evidência completa. | Alta | Auditoria, checksum, origem, operador, MFA e resultado. | P1 |
| Exportação de dados sem destino ou justificativa. | Média | Permissão própria, motivo obrigatório e registro de escopo. | P2 |

## Registro de Riscos

| ID | Risco | Severidade | Probabilidade | Prioridade | Mitigação planejada |
|---|---|---:|---:|---:|---|
| R1 | Painel operacional sem RBAC interno. | Alta | Média | P0 | API autenticada, RBAC e auditoria antes de expor operação. |
| R2 | Secrets locais em `.env` vazarem por cópia, log ou commit. | Crítica | Média | P0 | Secret Manager, secret scanning, rotação e revisão de `.gitignore`. |
| R3 | SQLite local exfiltrado ou corrompido. | Crítica | Média | P0 | Backups testados, criptografia e PostgreSQL gerenciado. |
| R4 | Publicação indevida no site ou Telegram. | Alta | Média | P0 | Permissões específicas, MFA para produção e trilha de aprovação. |
| R5 | Conta GitHub ou workflow comprometido. | Crítica | Baixa/Média | P0 | Proteção de branch, revisão, permissões mínimas e monitoramento. |
| R6 | Logs insuficientes para investigação. | Alta | Alta | P0 | Modelo de auditoria append-only com usuário, IP, UA e resultado. |
| R7 | Analytics abusado por bots. | Média | Média | P1 | Rate limiting, WAF e limitação por evento. |
| R8 | OAuth Mercado Livre usado indevidamente. | Alta | Média | P1 | Rotação de token, Secret Manager, menor privilégio e alerta de falhas. |
| R9 | Backup restaurado por engano. | Alta | Baixa/Média | P1 | MFA, confirmação, dry-run, checksum e auditoria. |
| R10 | XSS por conteúdo de oferta ou catálogo. | Alta | Baixa/Média | P1 | Sanitização, escape padrão, CSP e validação do catálogo. |

## Critérios de Aceite da Fase 1

- Ativos e superfícies de ataque documentados.
- Atores legítimos e maliciosos documentados.
- Ameaças classificadas por pilar.
- Riscos priorizados com mitigação planejada.
- Inventário de dados documentado.
- Matriz RBAC inicial documentada.
- Nenhuma implementação de autenticação feita nesta fase.
