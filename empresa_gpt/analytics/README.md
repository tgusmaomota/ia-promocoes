# Analytics Contract

## Responsabilidades

- Definir eventos, metricas e relatorios sanitizados.
- Separar analytics publico de dados operacionais privados.
- Permitir provedores/adaptadores sem acoplamento a cliente.
- Evitar identificadores pessoais por padrao.

## Entradas

- Evento sanitizado.
- Nome de recurso.
- Propriedades minimas.
- Nome de relatorio.

## Saidas

- Evento aceito pelo adaptador.
- Relatorio agregado.
- Erros de analytics sem payload sensivel.

## Erros

- `AnalyticsError`: evento invalido, provider indisponivel ou propriedade sensivel bloqueada.

## Regras de Seguranca

- Nao emitir evento em import.
- Nao coletar IP, cookie, token, e-mail ou identificador pessoal por padrao.
- Nao misturar dados privados com relatorios publicos.

## Uso Futuro pelo Promogg

O analytics atual do Promogg pode ser adaptado para `AnalyticsContract`, preservando o modelo publico sem identificador pessoal e os bloqueios de dados sensiveis.

