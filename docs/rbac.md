# RBAC

Este documento define a matriz inicial de controle de acesso baseado em papéis para o Promogg. A Fase 6B aplica o RBAC experimental persistente somente ao router local `/api/v1/auth/*`, usando o banco de autenticação isolado (`auth_dev.db` ou `PROMOGG_AUTH_DB_PATH`). Ela não aplica autorização nas rotas read-only, não ativa RBAC em produção e não cria rotas operacionais mutáveis. O modelo detalhado de entidades, sessões, refresh tokens e auditoria futura está em [Modelo de Identidade e Auditoria](auth-model.md).

## Estado da Fase 6B

- Papéis e permissões padrão são semeados no banco experimental.
- Usuários podem receber ou perder papéis pelo repository experimental.
- Helpers internos listam permissões efetivas e checam uma ou múltiplas permissões.
- A autorização nega por padrão quando usuário, papel ou permissão não existe, quando o usuário não está ativo, ou quando o ambiente não é `development` com `PROMOGG_RBAC_ENABLED=true`.
- O router experimental de auth usa `PersistentRBACAuthorizer` apenas em `development` com `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true` e `PROMOGG_RBAC_ENABLED=true`.
- `/api/v1/auth/me` e `/api/v1/auth/logout` exigem sessão válida; `/api/v1/auth/refresh` exige refresh/sessão válidos.
- Futuras ações administrativas deverão exigir permissões explícitas, mas essas rotas ainda não existem.
- Produção continua sem RBAC ativo.
- `/api/v1/health`, `/api/v1/ofertas` e `/api/v1/categorias` continuam públicas.
- `banco.db`, Streamlit e workflows não são alterados.

## Papéis

| Papel | Descrição |
|---|---|
| Administrador | Governa segurança, usuários, papéis, secrets, deploy, rollback e configurações críticas. |
| Operador | Executa rotina operacional: coleta, produção, publicação, workers e manutenção controlada. |
| Revisor | Avalia, aprova, rejeita e edita ofertas dentro do fluxo de curadoria. |
| Analista | Consulta métricas, analytics, relatórios e saúde do sistema. |
| Somente leitura | Visualiza dados e status sanitizados sem executar mudanças. |

## Regras Gerais

- Toda ação mutável deve exigir permissão explícita.
- Toda ação crítica deve exigir auditoria.
- MFA deve ser obrigatório para administradores.
- MFA deve ser exigido para ações críticas mesmo quando executadas por papel autorizado.
- Operador não gerencia usuários, papéis ou secrets.
- Revisor não publica diretamente em produção sem permissão adicional.
- Analista e Somente leitura não executam comandos mutáveis.

## Permissões

| Permissão | Descrição |
|---|---|
| `panel:read` | Visualizar painel. |
| `offers:read` | Visualizar ofertas. |
| `offers:review` | Aprovar ou rejeitar ofertas. |
| `offers:edit` | Editar dados de oferta. |
| `offers:publish` | Publicar oferta em canais públicos. |
| `catalog:read` | Visualizar catálogo público/operacional. |
| `catalog:generate` | Gerar ou preparar catálogo/site. |
| `telegram:publish` | Publicar oferta no Telegram. |
| `site:deploy` | Publicar/deployar site. |
| `workers:read` | Visualizar serviços e workers. |
| `workers:run` | Iniciar execução de worker/produção. |
| `workers:stop` | Parar worker/produção. |
| `site:publish` | Alias legado planejado para `site:deploy`. |
| `production:start` | Alias legado planejado para `workers:run`. |
| `production:stop` | Alias legado planejado para `workers:stop`. |
| `collection:run` | Rodar coleta. |
| `affiliates:generate` | Gerar links afiliados. |
| `logs:read` | Acessar logs sanitizados. |
| `analytics:read` | Acessar analytics. |
| `users:read` | Consultar usuários. |
| `users:manage` | Criar, editar, desativar usuários. |
| `roles:manage` | Alterar papéis e permissões. |
| `secrets:manage` | Alterar secrets/configurações sensíveis. |
| `rollback:run` | Executar rollback. |
| `backup:restore` | Restaurar backup. |
| `backup:create` | Criar backup manual. |
| `data:export` | Exportar dados. |
| `audit:read` | Consultar trilha de auditoria. |
| `system:admin` | Administração crítica do sistema. |

## Matriz de Ações

| Ação | Permissão | Papéis permitidos | MFA | Auditoria | Risco | Observação |
|---|---|---|---|---|---|---|
| Visualizar painel | `panel:read` | Administrador, Operador, Revisor, Analista, Somente leitura | Não | Sim | Baixo | Auditoria leve de acesso. |
| Visualizar ofertas | `offers:read` | Administrador, Operador, Revisor, Analista, Somente leitura | Não | Sim | Baixo | Dados exibidos devem ser compatíveis com o papel. |
| Aprovar oferta | `offers:review` | Administrador, Operador, Revisor | Não | Sim | Médio/Alto | Registrar oferta, decisão, motivo e usuário. |
| Rejeitar oferta | `offers:review` | Administrador, Operador, Revisor | Não | Sim | Médio | Registrar motivo e estado anterior. |
| Editar oferta | `offers:edit` | Administrador, Operador, Revisor | Não | Sim | Alto | Registrar antes/depois sanitizado. |
| Ocultar oferta | `offers:edit` | Administrador, Operador | Não | Sim | Alto | Revisor pode solicitar, mas ocultação final fica com Operador/Admin. |
| Restaurar oferta | `offers:edit` | Administrador, Operador | Sim | Sim | Alto | Exige backup/status anterior e motivo. |
| Publicar Telegram | `telegram:publish` | Administrador, Operador | Sim | Sim | Alto | Pode afetar canal público e reputação. |
| Publicar site | `site:publish` | Administrador, Operador | Sim | Sim | Alto | Exigir validação de catálogo antes. |
| Preparar publicação | `site:publish` | Administrador, Operador | Não | Sim | Médio | Pode ser dry-run sem MFA; publicação real exige MFA. |
| Iniciar produção | `production:start` | Administrador, Operador | Sim | Sim | Alto | Ativa automações custosas/externas. |
| Parar produção | `production:stop` | Administrador, Operador | Sim | Sim | Alto | Pode afetar disponibilidade. |
| Rodar coleta | `collection:run` | Administrador, Operador | Não | Sim | Médio | Pode acionar APIs externas. |
| Rodar coleta confiável/Playwright | `collection:run` | Administrador, Operador | Sim | Sim | Alto | Envolve sessão de navegador e risco de bloqueio. |
| Gerar afiliados | `affiliates:generate` | Administrador, Operador | Sim | Sim | Alto | Impacta links comerciais. |
| Testar token Mercado Livre | `secrets:manage` | Administrador, Operador | Sim | Sim | Alto | Não deve exibir token. |
| Renovar token Mercado Livre | `secrets:manage` | Administrador | Sim | Sim | Crítico | Operador pode solicitar; execução final por Admin. |
| Acessar logs | `logs:read` | Administrador, Operador, Analista | Não | Sim | Médio | Logs devem ser sanitizados. |
| Acessar auditoria | `audit:read` | Administrador, Analista | Sim para exportação | Sim | Alto | Pode expor IP, User Agent e ações internas. |
| Acessar analytics | `analytics:read` | Administrador, Operador, Analista, Somente leitura | Não | Sim | Baixo/Médio | Preferir dados agregados para Somente leitura. |
| Gerenciar usuários | `users:manage` | Administrador | Sim | Sim | Crítico | Criar/desativar usuário, reset de MFA/senha. |
| Alterar papéis | `roles:manage` | Administrador | Sim | Sim | Crítico | Exigir confirmação e registrar antes/depois. |
| Alterar secrets | `secrets:manage` | Administrador | Sim | Sim | Crítico | Nunca registrar valor do secret. |
| Fazer rollback | `rollback:run` | Administrador, Operador | Sim | Sim | Alto | Registrar versão origem/destino. |
| Restaurar backup | `backup:restore` | Administrador | Sim | Sim | Crítico | Exigir checksum, dry-run e janela de manutenção. |
| Criar backup manual | `backup:create` | Administrador, Operador | Não | Sim | Médio | Backup deve ser criptografado se sair do host. |
| Exportar dados | `data:export` | Administrador, Analista | Sim | Sim | Alto | Exigir escopo, motivo e destino. |
| Exportar catálogo público | `data:export` | Administrador, Operador, Analista | Não | Sim | Médio | Apenas dados sanitizados. |
| Alterar configurações de deploy | `deploy:configure` | Administrador | Sim | Sim | Crítico | Inclui domínio, túnel, Pages e Cloudflare. |
| Iniciar/parar serviços | `services:manage` | Administrador, Operador | Sim para produção | Sim | Alto | Painel/site local pode ser menor risco; produção exige MFA. |
| Visualizar saúde do sistema | `health:read` | Administrador, Operador, Analista, Somente leitura | Não | Sim | Baixo | Detalhes sensíveis devem ser filtrados por papel. |
| Executar manutenção | `maintenance:run` | Administrador, Operador | Sim | Sim | Alto | Pode pausar automações. |
| Executar comandos destrutivos | `admin:dangerous` | Administrador | Sim | Sim | Crítico | Exigir confirmação, backup e motivo. |

## Acesso por Papel

| Permissão | Administrador | Operador | Revisor | Analista | Somente leitura |
|---|---|---|---|---|---|
| `panel:read` | Sim | Sim | Sim | Sim | Sim |
| `offers:read` | Sim | Sim | Sim | Sim | Sim |
| `offers:review` | Sim | Sim | Sim | Não | Não |
| `offers:edit` | Sim | Sim | Sim, limitado | Não | Não |
| `telegram:publish` | Sim | Sim | Não | Não | Não |
| `site:publish` | Sim | Sim | Não | Não | Não |
| `production:start` | Sim | Sim | Não | Não | Não |
| `production:stop` | Sim | Sim | Não | Não | Não |
| `collection:run` | Sim | Sim | Não | Não | Não |
| `affiliates:generate` | Sim | Sim | Não | Não | Não |
| `logs:read` | Sim | Sim | Não | Sim | Não |
| `analytics:read` | Sim | Sim | Não | Sim | Sim, agregado |
| `audit:read` | Sim | Não | Não | Sim, limitado | Não |
| `users:manage` | Sim | Não | Não | Não | Não |
| `roles:manage` | Sim | Não | Não | Não | Não |
| `secrets:manage` | Sim | Não | Não | Não | Não |
| `rollback:run` | Sim | Sim | Não | Não | Não |
| `backup:restore` | Sim | Não | Não | Não | Não |
| `data:export` | Sim | Não | Não | Sim, limitado | Não |

## Auditoria Obrigatória

Toda ação auditada deve registrar:

- usuário;
- papel;
- sessão;
- IP;
- User Agent;
- ação;
- permissão usada;
- recurso;
- resultado;
- motivo quando aplicável;
- request id;
- timestamp.

Nunca registrar senha, token, cookie, refresh token, segredo ou código OAuth.

## Critérios de Aceite

- Toda ação crítica possui permissão nomeada.
- Todo papel tem escopo explícito.
- Toda ação mutável exige auditoria.
- Ações críticas exigem MFA.
- A matriz pode ser convertida diretamente em policies na futura API.
