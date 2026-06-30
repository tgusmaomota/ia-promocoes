# Security Contract

## Responsabilidades

- Definir contratos de autenticacao, autorizacao, RBAC, sessoes e auditoria.
- Negar acoes criticas por padrao.
- Sanitizar eventos antes de log ou persistencia.
- Separar seguranca da plataforma das regras de cada produto.

## Entradas

- Ator.
- Acao.
- Recurso.
- Contexto sanitizavel.
- Politicas e permissoes explicitas em fases futuras.

## Saidas

- Decisao de seguranca.
- Evento de auditoria sanitizado.
- Erros genericos para consumidores.

## Erros

- `SecurityError`: violacao de contrato, politica ausente ou contexto invalido.

## Regras de Seguranca

- Negar por padrao.
- Nao emitir tokens em imports.
- Nao escrever cookies por padrao.
- Nao persistir auditoria sem sanitizacao.
- Nao registrar token, senha, cookie, secret ou URL sensivel.

## Uso Futuro pelo Promogg

O Promogg podera substituir validacoes locais por chamadas a um adaptador de `SecurityContract`, inicialmente em rotas experimentais e depois em acoes criticas como publicacao, aprovacao, deploy e operacao de workers.

