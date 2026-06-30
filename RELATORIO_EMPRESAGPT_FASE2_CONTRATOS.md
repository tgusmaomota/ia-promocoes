# Relatorio EmpresaGPT Fase 2: Contratos e ADRs do Core

Data: 2026-06-30

## Escopo

Fase 2 da EmpresaGPT criada com contratos documentais, ADRs e stubs inertes. Nenhum codigo do Promogg foi movido. Nenhum import do Promogg foi alterado. Nenhum comportamento runtime foi conectado aos novos contratos.

## ADRs Criados

- `empresa_gpt/docs/ADR-0001-core-sem-dependencia-do-promogg.md`
- `empresa_gpt/docs/ADR-0002-ollama-como-ia-local-prioritaria.md`
- `empresa_gpt/docs/ADR-0003-seguranca-e-auditoria-sanitizada.md`
- `empresa_gpt/docs/ADR-0004-produtos-como-modulos.md`
- `empresa_gpt/docs/ADR-0005-servicos-desligados-por-padrao.md`

## Contratos Criados

| Area | Arquivos |
|---|---|
| Core Config | `empresa_gpt/core/config/README.md`, `empresa_gpt/core/config/contract.py` |
| Security | `empresa_gpt/security/README.md`, `empresa_gpt/security/contract.py` |
| AI | `empresa_gpt/ai/README.md`, `empresa_gpt/ai/contract.py` |
| Storage | `empresa_gpt/storage/README.md`, `empresa_gpt/storage/contract.py` |
| Analytics | `empresa_gpt/analytics/README.md`, `empresa_gpt/analytics/contract.py` |
| Monitoring | `empresa_gpt/monitoring/README.md`, `empresa_gpt/monitoring/contract.py` |
| Services | `empresa_gpt/services/README.md`, `empresa_gpt/services/contract.py` |

## Caracteristicas dos Stubs

- Importaveis.
- Sem side effects em import.
- Sem rede.
- Sem banco.
- Sem leitura automatica de `.env`.
- Sem deploy, coleta, publicacao, Telegram ou supervisor-loop.
- Defaults seguros: servicos desligados, autorizacao negada, `dry_run=True`.

## Testes de Caracterizacao

Criado `tests/test_empresagpt_contracts_phase2.py` para validar apenas propriedades dos stubs:

- contratos importam sem dependencias runtime do Promogg;
- configuracao nasce com servico desligado;
- seguranca nega por padrao;
- servicos usam `dry_run=True`;
- IA prioriza `ollama` como provider default.

## Verificacao Executada

`pytest` nao estava instalado no `venv`, entao a suite nova nao foi executada por esse runner. Para manter a verificacao sem alterar ambiente ou instalar dependencias, foram executadas checagens locais equivalentes:

- `venv/bin/python -m py_compile` nos contratos e no teste novo;
- import direto dos contratos com asserts dos defaults seguros.

Resultado: `EMPRESAGPT_FASE2_CONTRATOS_OK`.

## Uso Futuro pelo Promogg

O Promogg podera usar estes contratos somente por adaptadores futuros. A ordem recomendada e:

1. Testes de caracterizacao do comportamento atual.
2. Adaptador sem substituir chamadas existentes.
3. Execucao paralela em modo observacao.
4. Comparacao de resultados.
5. Troca gradual de chamadas quando houver equivalencia funcional.

## Riscos Controlados

- Stubs sao codigo novo, mas nao sao importados pelo runtime atual do Promogg.
- Testes novos nao executam operacao externa.
- Relatorio e ADRs sao documentais.

## Proibicoes Mantidas

- Nao mover codigo do Promogg.
- Nao alterar imports existentes.
- Nao alterar banco.
- Nao alterar site.
- Nao executar deploy.
- Nao enviar Telegram.
- Nao iniciar supervisor-loop.
- Nao executar online/coleta/publicacao.
