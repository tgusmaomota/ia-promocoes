# Guia de Contribuicao

## Escopo da Fase 1

Contribuicoes nesta fase devem ser documentais ou estruturais. Nao devem alterar comportamento do Promogg.

## Fluxo Recomendado

1. Leia `EMPRESAGPT_MASTER_PLAN.md`.
2. Confirme se a mudanca pertence a EmpresaGPT, Promogg ou transicao.
3. Documente a decisao antes de mover codigo.
4. Adicione testes antes de alterar comportamento.
5. Valide que site, banco, painel, deploy e supervisor nao foram afetados.

## Regras para Pull Requests Futuros

- Explicar impacto no Promogg.
- Listar arquivos operacionais tocados.
- Informar testes executados.
- Declarar se altera banco, site, painel, deploy, supervisor ou producao.
- Incluir plano de rollback quando houver risco operacional.

## Convencao de Documentos

- Documentos de plataforma ficam na raiz ou em `empresa_gpt/docs/`.
- Documentos operacionais do Promogg continuam em `docs/`.
- Relatorios de auditoria devem preservar data, escopo e conclusoes.

