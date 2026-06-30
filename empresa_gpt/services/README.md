# Services Contract

## Responsabilidades

- Definir comandos, casos de uso e resultados de servicos de plataforma.
- Manter execucao explicita e com `dry_run` como padrao.
- Separar servicos de plataforma de regras de produto.
- Preparar adaptadores para operacoes futuras.

## Entradas

- Comando nomeado.
- Payload validado.
- Flag `dry_run`.
- Contexto de cliente em fases futuras.

## Saidas

- Resultado aceito/negado.
- Status.
- Detalhes sanitizados.

## Erros

- `ServiceError`: comando invalido, servico desabilitado, permissao ausente ou payload inseguro.

## Regras de Seguranca

- Nao executar servico em import.
- `dry_run` deve ser o default em contratos.
- Nao disparar coleta, publicacao, deploy, Telegram ou supervisor sem comando explicito.
- Acoes criticas futuras devem passar por seguranca e auditoria.

## Uso Futuro pelo Promogg

Comandos do Promogg poderao ser embrulhados por `ServiceContract` gradualmente, preservando o CLI atual ate existir equivalencia funcional e autorizacao clara.

