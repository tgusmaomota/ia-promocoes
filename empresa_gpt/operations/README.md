# EmpresaGPT Operations Center

## Responsabilidade

O EmpresaGPT Operations Center, ou EGOC, e o centro operacional unico da EmpresaGPT. Ele modela produtos, saude, servicos, backups, alertas, auditorias, qualidade, riscos e uso de recursos sem conhecer Promogg ou qualquer outro produto especifico.

## Entradas

As entradas sao snapshots explicitos fornecidos por contratos: status do produto, health, servicos, backups, auditorias, alertas, metricas e risco. Cada produto futuro devera adaptar seus dados para estes contratos.

## Saidas

As saidas sao modelos neutros para dashboard, relatorios operacionais e Quality Engine. O EGOC nao publica, nao coleta, nao agenda tarefas e nao executa deploy.

## Erros

Erros contratuais devem ser representados por `OperationsContractError` ou por estados `UNKNOWN`, `DEGRADED` e alertas explicitos. O EGOC nao deve mascarar falhas como sucesso operacional.

## Seguranca

O EGOC nao acessa secrets, banco, APIs externas, cookies, tokens ou runtimes de produtos. Adaptadores futuros devem enviar apenas dados sanitizados e suficientes para operacao.

## Uso futuro

Promogg, Prefeitura GPT, Juridico GPT, Saude GPT, RH GPT, Educacao GPT e demais produtos deverao registrar estado atraves dos contratos. Nenhum produto deve ser considerado em producao sem integracao operacional com o EGOC.

