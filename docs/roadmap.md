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

Status: Fase 2D com comandos oficiais da API no CLI em andamento.

- Criar API HTTP versionada em `/api/v1`.
- Manter CLI, Streamlit e fluxo estático funcionando durante a transição.
- Expor primeiro rotas somente leitura e health checks.
- Padronizar erros, validação, sanitização, CORS e rate limiting.
- Criar testes de contrato e segurança para a nova API.
- Endurecer respostas read-only com headers de segurança, logs sem segredos e CORS sem wildcard default.
- Adicionar comandos oficiais `api`, `api-teste` e `auth-teste` ao CLI sem substituir Streamlit.
- Manter autenticação real, JWT, sessões e RBAC para fases posteriores.

### Fase 3: Usuários, Senhas, JWT, Refresh Cookie e Sessões

Status: Fase 5A com integração experimental local em `/api/v1/auth/*`, sem login real em produção.

- Definir modelo de entidades de identidade, sessões, refresh tokens, MFA, reset de senha, OAuth e auditoria.
- Definir lifecycle de sessão, access token curto, refresh token rotativo e detecção de reuso.
- Mapear permissões futuras e eventos mínimos de auditoria antes de criar rotas autenticadas.
- Criar módulos internos testáveis para hashing de senha, tokens opacos, RBAC em memória e sanitização de auditoria.
- Criar persistência experimental em `auth_dev.db`, separada do `banco.db`, com schema para usuários, sessões, refresh tokens e auditoria.
- Criar serviço interno experimental para simular autenticação completa em testes.
- Criar camada central `api_promogg/security/` para settings, feature flags, constantes e validadores compartilhados por toda autenticação futura.
- Registrar rotas experimentais `/api/v1/auth/*`, desativadas por padrão e disponíveis apenas com `PROMOGG_ENV=development` e feature flag experimental ligada.
- Preparar contratos de credenciais, provider JWT experimental e helpers de cookies seguros sem ativar JWT, cookies ou autenticação em produção.
- Criar fachada interna para emissão experimental de credenciais via `CredentialProvider`, sem uso por rotas públicas.
- Preparar infraestrutura passiva de CSRF, validação de origem e proteção contra session fixation, sem uso por rotas.
- Integrar login, refresh, logout e me somente em `PROMOGG_ENV=development` com `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true`.
- Enviar refresh token opaco em cookie experimental `HttpOnly`, rotacionar a cada refresh e revogar sessão em caso de reuso.
- Criar comando `auth-teste` para exercitar auth experimental com `TestClient`, banco temporário e saída sem segredos.
- Manter produção sem `/api/v1/auth/*`, sem cookies e sem autenticação ativa, mesmo com flags parciais ligadas.
- Sem admin automático, senha hardcoded, endpoint de login ou proteção das rotas read-only.
- Manter rotas read-only sem autenticação até a fase de integração planejada.

- Criar usuários internos.
- Implementar senhas com Argon2id ou bcrypt.
- Endurecer access token JWT curto para uso fora do laboratório local.
- Revisar cookies `HttpOnly`, `Secure` e `SameSite` antes de qualquer produção.
- Promover sessões revogáveis e auditoria para desenho definitivo de produção.

### Fase 4: RBAC em Ações Críticas

Status: Fase 6B com RBAC experimental persistente aplicado somente ao router `/api/v1/auth/*` em development, ainda sem proteger produção.

- Conectar papéis/permissões ao banco experimental de autenticação.
- Criar helpers de autorização que listam permissões efetivas e checam uma ou múltiplas permissões.
- Negar por padrão quando usuário, papel, sessão futura ou permissão não existe.
- Exigir sessão válida em `/auth/me` e `/auth/logout`, e refresh/sessão válidos em `/auth/refresh`, apenas no fluxo experimental local.
- Manter `/health`, `/ofertas` e `/categorias` públicas.
- Manter produção sem RBAC ativo.
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
