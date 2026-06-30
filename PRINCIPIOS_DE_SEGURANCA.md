# Principios de Seguranca

## Pilares

- Confidencialidade.
- Integridade.
- Disponibilidade.
- Autenticidade.
- Auditoria.
- Rastreabilidade.

## Regras de Plataforma

- Segredos fora do Git.
- Tokens, cookies, senhas e URLs sensiveis nunca devem aparecer em logs.
- Auth, RBAC, MFA e sessoes devem nascer desligados por padrao em producao ate liberacao explicita.
- Refresh tokens devem ser opacos, rotacionados e persistidos somente como hash.
- JWT deve ser curto e conter apenas claims necessarias.
- Cookies sensiveis devem usar `HttpOnly`, `Secure` em producao e `SameSite` adequado.
- Toda acao critica deve ter permissao explicita.
- Auditoria deve registrar ator, acao, recurso, resultado e contexto sanitizado.

## Dados Publicos e Privados

O padrao do Promogg de separar banco operacional privado de catalogo publico sanitizado deve ser mantido como referencia de plataforma.

Nenhum cliente deve publicar artefatos que dependam de `.env`, banco local, logs, cookies, perfis de navegador ou secrets.

## Ambientes

- Desenvolvimento pode ativar features experimentais por flags.
- Producao deve negar rotas experimentais.
- Configuracao de CORS, hosts e origens deve ser restritiva por padrao.
- Deploy deve falhar fechado quando dados publicos estiverem vazios, invalidos ou suspeitos.

