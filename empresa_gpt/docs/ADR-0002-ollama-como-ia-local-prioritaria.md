# ADR-0002: Ollama como IA local prioritaria

## Status

Aceita.

## Contexto

O Promogg ja possui assistente e revisao por IA local em carater operacional. Para a EmpresaGPT, a prioridade inicial e permitir IA local, privada e controlavel antes de depender de provedores remotos.

## Decisao

Ollama sera a opcao local prioritaria para contratos de IA da EmpresaGPT. O contrato deve permitir outros provedores no futuro, mas o desenho inicial deve funcionar bem com execucao local, sem trafegar dados sensiveis para terceiros por padrao.

## Consequencias

- O contrato de IA deve separar prompt, contexto, politicas de seguranca e resposta.
- Nenhum provider deve ser chamado durante import.
- O uso futuro pelo Promogg deve passar por sanitizacao de contexto e limites de dados.
- Provedores remotos poderao existir depois, com consentimento/configuracao explicita.

## Regras

- IA local por padrao quando disponivel.
- Sem envio automatico de dados privados.
- Logs devem remover prompts sensiveis, tokens, cookies e URLs privadas.
- Respostas de IA devem ser tratadas como sugestao ate passarem por regras de negocio.

