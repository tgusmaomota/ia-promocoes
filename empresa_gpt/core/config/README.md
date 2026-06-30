# Core Config Contract

## Responsabilidades

- Definir configuracao explicita da plataforma.
- Manter servicos desligados por padrao.
- Separar configuracao de plataforma e configuracao de cliente.
- Evitar leitura automatica de `.env` ou arquivos operacionais durante import.

## Entradas

- Fonte nomeada de configuracao.
- Pares chave/valor ja carregados por um chamador explicito.
- Identificador futuro de cliente/produto.

## Saidas

- Objeto de configuracao resolvida.
- Flags com defaults seguros.
- Erros de configuracao sem expor secrets.

## Erros

- `ConfigError`: configuracao ausente, invalida ou insegura.

## Regras de Seguranca

- Nao ler secrets automaticamente.
- Nao logar valores sensiveis.
- Nao habilitar servicos por default.
- Nao depender de variaveis especificas do Promogg.

## Uso Futuro pelo Promogg

O Promogg podera fornecer um adaptador que converte suas variaveis atuais para `PlatformConfig`, mantendo o fluxo atual intacto ate os testes de equivalencia.

