# Checklist de Autenticacao para Producao

Este checklist define o que ainda falta antes de qualquer autenticacao do Promogg ser considerada pronta para producao.

As rotas experimentais `/api/v1/auth/*` da Fase 5A nao sao autenticacao de producao. Elas devem permanecer desativadas por padrao, retornar `404 Not Found` fora de `PROMOGG_ENV=development` com `PROMOGG_AUTH_EXPERIMENTAL_ENABLED=true`, nao emitir cookies em producao e nunca devem ser usadas para operar o sistema real.

## Condicoes Bloqueantes

- [ ] `PROMOGG_AUTH_EXPERIMENTAL_ENABLED` nao pode ser usado como controle unico de ativacao.
- [ ] Producao e staging devem continuar sem login experimental.
- [ ] Producao deve continuar sem `/api/v1/auth/*`, sem cookies e sem autenticacao ativa ate a fase de hardening final.
- [ ] Nenhuma rota read-only deve ser protegida por autenticacao parcial.
- [ ] Nenhuma rota privada deve entrar em producao sem teste de autenticacao, autorizacao e auditoria.
- [ ] `banco.db` operacional nao deve receber tabelas ou dados de autenticacao.
- [ ] Segredos, cookies, tokens, senhas e payloads sensiveis nao podem aparecer em logs.

## JWT

- [ ] Manter provider desacoplado por `CredentialProvider`; rotas nao devem depender diretamente de JWT.
- [ ] Garantir que toda emissao passe pela fachada de credenciais, nunca direto pelo provider concreto.
- [ ] Definir issuer, audience, algoritmo e politica de chaves.
- [ ] Emitir access token curto, preferencialmente entre 5 e 15 minutos.
- [ ] Incluir apenas claims necessarias: `sub`, `session_id`, `roles`/`permissions`, `iat`, `exp`, `iss`, `aud`.
- [ ] Validar expiracao, issuer, audience e assinatura em todas as rotas privadas.
- [ ] Criar estrategia de rotacao de chaves e invalidacao.

## Cookies HttpOnly

- [ ] Revisar a integracao experimental de cookies antes de qualquer promocao para producao.
- [ ] Enviar refresh token somente em cookie `HttpOnly`.
- [ ] Exigir `Secure` em producao.
- [ ] Definir `SameSite=Strict` ou `SameSite=Lax` conforme fluxo.
- [ ] Nunca expor refresh token em resposta JSON de producao.
- [ ] Limpar cookie em logout e revogacao de sessao.

## Refresh Rotativo Persistente

- [ ] Persistir somente hash do refresh token.
- [ ] Rotacionar refresh token a cada uso.
- [ ] Detectar reuso de token antigo.
- [ ] Revogar familia inteira em caso de reuso.
- [ ] Registrar auditoria de refresh usado, refresh reusado e revogacao.

## MFA

- [ ] Implementar TOTP com segredo criptografado.
- [ ] Armazenar recovery codes somente em hash.
- [ ] Exigir MFA para administradores.
- [ ] Exigir MFA para acoes criticas: deploy, rollback, secrets, papeis e desativacao de MFA.
- [ ] Auditar ativacao, desativacao e falhas de MFA sem registrar codigos.

## OAuth Google/GitHub

- [ ] Usar Authorization Code Flow com PKCE.
- [ ] Validar `state`, `nonce`, `redirect_uri`, `iss`, `aud` e expiracao.
- [ ] Vincular identidade externa a usuario interno existente.
- [ ] Nao conceder papel administrativo apenas pelo provedor OAuth.
- [ ] Nunca persistir access token ou refresh token do provedor sem cofre/criptografia.

## RBAC Conectado ao Banco

- [ ] Persistir usuarios, papeis e permissoes em banco de producao.
- [ ] Garantir permissoes explicitas por rota e acao.
- [ ] Criar testes para cada permissao critica.
- [ ] Revogar ou exigir reautenticacao apos alteracao critica de papel.
- [ ] Registrar auditoria de mudancas de papel/permissao.

## CSRF

- [ ] Integrar helpers passivos de CSRF somente quando rotas mutaveis privadas existirem.
- [ ] Ativar protecao CSRF para mutacoes quando cookies forem usados.
- [ ] Separar rotas idempotentes de rotas mutaveis.
- [ ] Validar origem e host em rotas privadas.
- [ ] Testar bloqueio de requisicoes cross-site indevidas.

## Auditoria Definitiva

- [ ] Tornar eventos criticos append-only.
- [ ] Registrar login, falha, logout, refresh, reuso, MFA, RBAC, deploy, secrets e exportacoes.
- [ ] Usar `request_id`, `user_id`, `session_id`, recurso, resultado e motivo sanitizado.
- [ ] Nunca registrar senha, token, cookie, secret, TOTP, recovery code ou payload bruto sensivel.
- [ ] Definir retencao e acesso a auditoria.

## Rate Limiting e Lockout

- [ ] Rate limit por IP, usuario, rota e acao sensivel.
- [ ] Lockout progressivo por tentativas de login.
- [ ] Nao revelar se e-mail existe.
- [ ] Auditar falhas agregaveis sem expor senha ou payload.
- [ ] Criar alertas para tentativas anormais.

## Sessoes Revogaveis

- [ ] Regenerar `session_id` apos login para prevenir session fixation.
- [ ] Persistir sessoes com status, expiracao, ultimo uso e motivo de revogacao.
- [ ] Revogar sessoes em logout, troca de senha, reuso de refresh, suspeita de incidente e mudanca critica de papel.
- [ ] Validar sessao ativa no servidor mesmo quando o access token ainda nao expirou.
- [ ] Expirar sessoes por tempo absoluto e, se necessario, por inatividade.

## Rotacao de Secrets

- [ ] Definir cofre ou mecanismo seguro para segredos.
- [ ] Criar processo de rotacao de chaves JWT, OAuth, cookies e integracoes.
- [ ] Auditar alteracao de secrets sem registrar valores.
- [ ] Testar rollback e recuperacao apos rotacao.

## Migracao PostgreSQL

- [ ] Planejar schema de producao para usuarios, sessoes, refresh tokens, RBAC, MFA e auditoria.
- [ ] Criar migracoes versionadas e revisadas.
- [ ] Garantir backups e restore testado.
- [ ] Usar criptografia em repouso no provedor ou volume.
- [ ] Separar banco operacional atual de dados de identidade ate migracao aprovada.

## Criterio Minimo de Aprovacao

- [ ] Testes unitarios, integracao e seguranca passando.
- [ ] Threat model atualizado.
- [ ] Documentacao operacional de incidente, revogacao e recuperacao de conta.
- [ ] Revisao de logs para ausencia de segredos.
- [ ] Validacao em staging com dados nao sensiveis.
- [ ] Plano de rollback antes de qualquer exposicao externa.
