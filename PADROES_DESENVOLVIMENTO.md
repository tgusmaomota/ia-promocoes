# Padroes de Desenvolvimento

## Regra Principal

Mudancas arquiteturais devem ser pequenas, reversiveis e testaveis. O Promogg nao deve ser quebrado para antecipar a EmpresaGPT.

## Antes de Alterar Codigo

- Identificar o dono do comportamento atual.
- Registrar o contrato esperado.
- Criar ou atualizar teste quando houver risco funcional.
- Confirmar que nao ha dependencia de banco, site, painel, deploy ou supervisor que sera afetada.

## Extracao de Modulos

- Nao mover codigo sem plano de migracao.
- Nao renomear modulo sem adaptador.
- Nao alterar imports em massa.
- Preferir wrappers/adaptadores primeiro.
- Manter compatibilidade enquanto o cliente Promogg estiver ativo.

## Testes

- Testes de caracterizacao antes de refatoracao.
- Testes unitarios para utilitarios e validadores.
- Testes de contrato para API, auth, storage e analytics.
- Testes de regressao para geracao publica, catalogo e comandos criticos.

## Configuracao

- Flags devem ser desligadas por padrao.
- Producao deve negar comportamento experimental.
- Segredos nunca devem ser versionados.
- Configuracoes de cliente devem ficar separadas das configuracoes de plataforma.

## Documentacao

- Toda decisao estrutural relevante deve gerar ADR ou nota em `empresa_gpt/docs/`.
- Relatorios devem separar fato observado, inferencia e recomendacao.
- Documentacao operacional do Promogg deve continuar em `docs/`.

