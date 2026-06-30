# ADR-0003: Seguranca e auditoria sanitizada

## Status

Aceita.

## Contexto

A EmpresaGPT lidara com operacoes, clientes, usuarios, integracoes e automacoes. O Promogg ja estabeleceu boas praticas: segredos fora do Git, catalogo publico sanitizado e logs sem dados sensiveis.

## Decisao

Seguranca e auditoria sao contratos centrais da plataforma. Eventos devem ser sanitizados antes de armazenamento, log ou exposicao. Auth, RBAC, cookies, CSRF, MFA e integracoes sensiveis devem nascer desligados por padrao ate habilitacao explicita.

## Consequencias

- Auditoria deve registrar ator, acao, recurso, resultado e contexto minimo.
- Tokens, senhas, cookies, secrets, chaves e URLs sensiveis nao podem aparecer em logs.
- Erros de seguranca devem ser genericos para usuarios e detalhados apenas em canal seguro.
- Eventos de cliente devem ser separados por escopo/tenant em fases futuras.

## Regras

- Sanitizar antes de persistir.
- Negar por padrao.
- Exigir permissao explicita para acoes criticas.
- Separar dados publicos de dados operacionais privados.

