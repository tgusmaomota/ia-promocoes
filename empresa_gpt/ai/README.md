# AI Contract

## Responsabilidades

- Definir contrato para IA local-first, com Ollama como prioridade inicial.
- Separar prompt, contexto, provider e resposta.
- Tratar resposta como sugestao, nao como decisao final.
- Permitir provedores futuros sem mudar produtos.

## Entradas

- Prompt sanitizado.
- Contexto minimo.
- Provider desejado, inicialmente `ollama`.
- Modelo opcional.

## Saidas

- Texto gerado.
- Provider/modelo usados.
- Indicacao se a resposta pode ser persistida.

## Erros

- `AIError`: provider indisponivel, prompt invalido, contexto inseguro ou falha de geracao.

## Regras de Seguranca

- Nao chamar provider em import.
- Nao enviar dados privados sem sanitizacao.
- Nao persistir prompt ou resposta sensivel por padrao.
- Nao permitir que IA execute acoes operacionais diretamente.

## Uso Futuro pelo Promogg

O assistente e a revisora do Promogg poderao usar `AIContract` por adaptador, mantendo regras atuais de curadoria e validacao como autoridade final.

