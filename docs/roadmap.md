# Roadmap

## Concluído

- Limpeza segura do índice Git.
- Remoção de artefatos gerados do Git.
- Catálogo público sanitizado.
- Geração estática via `gerar_site_publico.py`.
- Proteção contra deploy vazio.
- GitHub Pages gerando `dist_site/` no CI.
- Remoção de `dist_site/` do Git.
- Organização inicial da documentação.
- Aprovação da direção arquitetural de segurança para produção.

## Em Andamento

- Consolidação da documentação operacional.
- Redução da quantidade de arquivos na raiz.
- Separação entre documentação permanente e histórico.
- Melhoria contínua das validações de publicação.
- Planejamento da arquitetura de segurança antes de implementar autenticação.

## Fases de Segurança e Produção

### Fase 1: Threat Model, Inventário e RBAC

Status: em documentação inicial.

- Mapear ameaças por ativo: banco, painel, catálogo, tokens, deploy, analytics e workers.
- Inventariar dados sensíveis, públicos e operacionais.
- Definir matriz RBAC com papéis, permissões e ações críticas.
- Definir política de auditoria e rastreabilidade.
- Definir critérios de aceite antes de qualquer implementação de login.

### Fase 2: Backend API Autenticado em Paralelo

Status: Fase 2B com esqueleto read-only inicial em paralelo.

- Criar API HTTP versionada em `/api/v1`.
- Manter CLI, Streamlit e fluxo estático funcionando durante a transição.
- Expor primeiro rotas somente leitura e health checks.
- Padronizar erros, validação, sanitização, CORS e rate limiting.
- Criar testes de contrato e segurança para a nova API.

### Fase 3: Usuários, Senhas, JWT, Refresh Cookie e Sessões

- Criar usuários internos.
- Implementar senhas com Argon2id ou bcrypt.
- Criar access token JWT curto.
- Criar refresh token opaco, rotativo e armazenado em hash.
- Usar cookies `HttpOnly`, `Secure` e `SameSite`.
- Persistir sessões revogáveis e registrar eventos de login/logout.

### Fase 4: RBAC em Ações Críticas

- Proteger aprovação, rejeição, edição, publicação e ocultação de ofertas.
- Proteger início/parada de workers.
- Proteger deploy, rollback e alteração de configurações.
- Exigir permissões explícitas por rota e ação.
- Auditar decisões com usuário, IP, User Agent, recurso e resultado.

### Fase 5: OAuth2 e MFA

- Implementar login Google e GitHub com Authorization Code Flow + PKCE.
- Vincular identidades externas a usuários internos.
- Implementar MFA/TOTP para aplicativos autenticadores.
- Criar recovery codes com hash.
- Exigir MFA para administradores e ações sensíveis.

### Fase 6: PostgreSQL, Auditoria e Criptografia

- Planejar migração de SQLite local para PostgreSQL em produção.
- Criar migrações versionadas.
- Adotar criptografia em repouso no provedor ou volume.
- Criar backups automáticos e rotina de restore testada.
- Criar trilha de auditoria append-only.
- Definir retenção por classe de dado.

### Fase 7: Docker, CI/CD, Staging, Rollback e Monitoramento

- Criar containers para backend, frontend, worker, analytics e dependências de desenvolvimento.
- Criar ambiente de staging.
- Implantar pipeline CI/CD com testes, varredura de secrets e validações de segurança.
- Padronizar rollback por imagem, tag ou release.
- Adicionar monitoramento de disponibilidade, erros, login, rate limit, workers e ações administrativas.
- Integrar alertas para atividades suspeitas e falhas críticas.

## Próxima Versão

- Formalizar threat model e inventário de dados.
- Detalhar matriz RBAC.
- Projetar contratos iniciais de `/api/v1`.
- Definir modelo de usuários, sessões, refresh tokens e auditoria.

## Longo Prazo

- Aplicação autenticada pronta para produção.
- API versionada com autenticação, autorização e auditoria completas.
- Painel administrativo migrado para fluxo autenticado.
- PostgreSQL gerenciado em produção.
- Docker e CI/CD completo.
- Monitoramento de segurança e atividade suspeita.
- Hardening de infraestrutura com Cloudflare, WAF, HTTPS obrigatório e banco privado.
