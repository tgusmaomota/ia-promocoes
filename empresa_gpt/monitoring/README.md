# Monitoring Contract

## Responsabilidades

- Definir saude, disponibilidade, incidentes e alertas.
- Separar checagens pontuais de loops persistentes.
- Evitar envio automatico de alertas.
- Padronizar status para produtos.

## Entradas

- Nome da checagem.
- Alvo.
- Contexto futuro de cliente/ambiente.

## Saidas

- Status de saude.
- Detalhes sanitizados.
- Erros de monitoramento.

## Erros

- `MonitoringError`: alvo invalido, checagem indisponivel ou resultado inseguro.

## Regras de Seguranca

- Nao iniciar supervisor-loop em import.
- Nao enviar Telegram em import.
- Nao abrir servidor em import.
- Nao expor secrets em detalhes de saude.

## Uso Futuro pelo Promogg

`saude_sistema.py`, `alertas_telegram.py` e partes do supervisor poderao ser adaptados para este contrato, mas os comandos atuais continuam intactos.

