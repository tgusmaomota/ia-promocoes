# EmpresaGPT Operations Center

## Objetivos

O EGOC e o painel unico de operacao da EmpresaGPT. Ele foi desenhado para operar dezenas de produtos simultaneamente por anos, sem acoplar a plataforma ao Promogg ou a qualquer produto individual.

Objetivos principais:

- consolidar saude operacional por produto;
- padronizar status, servicos, backups, auditorias, alertas, metricas e riscos;
- permitir que novos produtos entrem em operacao com o mesmo contrato;
- tornar a decisao de producao dependente de visibilidade operacional.

## Arquitetura

A arquitetura inicial vive em `empresa_gpt/operations/` e e composta por:

- `models.py`: modelos neutros de Product, Service, Metric, Health, Risk, Audit, Backup e Alert;
- `contracts.py`: contratos publicos para ProductHealth, ProductStatus, Service, Risk, Backup, Audit, Alert e Metrics;
- `dashboard.py`: arvore declarativa do painel EGOC;
- `health.py`, `risk.py`, `services.py`, `alerts.py`, `metrics.py`, `status.py`, `backup.py`, `audit.py`, `report.py`: superficies especificas, sem runtime.

O EGOC conhece apenas produtos. Produtos conhecem seus proprios detalhes e reportam snapshots sanitizados para os contratos.

## Fluxos

1. Um produto calcula seu proprio estado localmente.
2. Um adaptador futuro converte esse estado para os modelos do EGOC.
3. O EGOC agrega produtos e exibe saude, servicos, backups, alertas, auditorias, qualidade, riscos e uso de recursos.
4. O Quality Engine valida se o EGOC esta documentado, importavel, neutro e sem dependencia do Promogg.

## Contratos

Contratos criados:

- `ProductHealthContract`
- `ProductStatusContract`
- `ServiceContract`
- `RiskContract`
- `BackupContract`
- `AuditContract`
- `AlertContract`
- `MetricsContract`

O contrato composto `ProductOperationsContract` representa a integracao completa de um produto.

## Responsabilidades

O EGOC deve:

- manter linguagem operacional comum;
- receber snapshots explicitos;
- preservar independencia entre produtos;
- permitir auditoria e comparacao;
- apoiar decisao de producao.

O EGOC nao deve:

- iniciar servicos;
- consultar banco de produto;
- alterar deploy;
- publicar;
- coletar dados;
- acionar Telegram, scheduler, supervisor ou automacoes.

## Escalabilidade

A estrutura e orientada a produtos e snapshots. Isso permite operar Promogg, Prefeitura GPT, Juridico GPT, Saude GPT, RH GPT, Educacao GPT e outros produtos sem criar paineis isolados. A mesma matriz de saude, risco e qualidade vale para todos.

## Integracao futura

Promogg futuramente devera criar um adaptador que implemente os contratos do EGOC usando somente dados ja sanitizados por seus validadores e relatorios. Produtos futuros devem nascer com o contrato EGOC desde o primeiro ciclo de producao.

Regra operacional: nenhum produto deve ser considerado em producao sem reportar estado ao EGOC.

