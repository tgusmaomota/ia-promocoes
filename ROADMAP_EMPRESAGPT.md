# Roadmap EmpresaGPT

## Fase 1: Fundacao Arquitetural

Status: iniciada.

- Criar estrutura `empresa_gpt/`.
- Criar documentacao fundadora.
- Auditar modulos atuais.
- Classificar reutilizacao potencial.
- Definir principios de engenharia e seguranca.
- Preservar integralmente o Promogg.

## Fase 2: Contratos e Adaptadores

- Definir contratos minimos para `core`, `security`, `storage`, `analytics` e `monitoring`.
- Criar ADRs para cada extracao proposta.
- Escrever testes de caracterizacao dos modulos candidatos.
- Criar adaptadores sem substituir imports existentes.
- Escolher primeiro modulo de baixo risco para extracao.

## Fase 3: Primeiras Extracoes Controladas

- Extrair utilitarios puros e validadores sem dominio.
- Isolar contratos de erro, request id e configuracao.
- Criar camada de analytics reutilizavel.
- Manter Promogg consumindo adaptadores somente apos equivalencia testada.

## Fase 4: Plataforma Multi-Cliente

- Introduzir conceito formal de tenant/cliente.
- Separar configuracoes de cliente.
- Criar modelo comum de usuario, permissao e auditoria.
- Definir estrutura para novos clientes alem do Promogg.

## Fase 5: Operacao de Plataforma

- EGOC como painel operacional unico da EmpresaGPT.
- Contratos comuns para produtos, saude, servicos, backups, alertas, auditorias, metricas e riscos.
- Regra de producao: nenhum produto entra em producao sem integrar o EGOC.
- Pipeline de testes, validacao de seguranca e deploy por ambiente.
- Monitoramento central.
- Runbooks de incidente.
- Politica de versionamento e compatibilidade.

## Missao 004: EmpresaGPT Operations Center

Status: arquitetura inicial.

- Criar `empresa_gpt/operations/`.
- Definir contratos de ProductHealth, ProductStatus, Service, Risk, Backup, Audit, Alert e Metrics.
- Criar modelos Product, Service, Metric, Health, Risk, Audit, Backup e Alert.
- Projetar dashboard EmpresaGPT -> Produtos -> Saude -> Servicos -> Backups -> Alertas -> Auditorias -> Qualidade -> Riscos -> Uso de recursos.
- Garantir que o EGOC nao conhece Promogg nem acessa runtime, banco, APIs, coleta, deploy ou publicacao.
- Adicionar verificacoes do EGOC ao Quality Engine.
- Documentar objetivos, arquitetura, fluxos, contratos, responsabilidades, escalabilidade e integracao futura.

## Missao 003: Product Intelligence Engine

Status: contratos e arquitetura iniciais.

- Criar `empresa_gpt/product_intelligence/`.
- Definir modelos de produto, categoria, sinais, score e recomendacao.
- Definir contratos para ranking, metricas, aprendizado e recomendacoes.
- Projetar melhorias futuras para o Promogg sem implementar runtime.
- Preparar integracao futura com Ollama para explicacao de ofertas.
- Ampliar Quality Engine com verificacoes estaticas de produto, SEO, imagens, links, home e categorias.

## Proximas Frentes de Valor para o Promogg

- Home com Hero Banner, ofertas do dia, destaques e recomendacoes.
- UX mobile-first com skeleton loading, lazy loading e paginacao melhor.
- Confianca com historico de preco, ultima atualizacao e transparencia de afiliados.
- IA local para explicar se uma oferta vale a pena.
- SEO com Open Graph, Schema.org, sitemap, canonical, robots, titles e meta descriptions.
- Performance com auditoria de imagens, CSS, JavaScript, cache e Core Web Vitals.
