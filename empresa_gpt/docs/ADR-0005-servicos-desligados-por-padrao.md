# ADR-0005: Servicos desligados por padrao

## Status

Aceita.

## Contexto

O repositorio possui scripts capazes de coletar, publicar, enviar Telegram, iniciar supervisor e alterar artefatos. A Fase 2 nao pode acionar nada disso.

## Decisao

Servicos da EmpresaGPT devem nascer desligados por padrao. Stubs, contratos e imports nao podem iniciar loop, worker, coleta, deploy, publicacao, Telegram, servidor ou conexao externa.

## Consequencias

- Importar `empresa_gpt.*` deve ser seguro.
- Execucao operacional futura precisara de comando explicito, ambiente correto e flags.
- Testes de contrato podem importar stubs sem efeitos colaterais.

## Regras

- Sem side effects em import.
- Sem rede por padrao.
- Sem escrita em banco por padrao.
- Sem envio de mensagem por padrao.
- Sem loop persistente por padrao.

