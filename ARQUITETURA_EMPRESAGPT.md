# Arquitetura EmpresaGPT

## Decisao Arquitetural

EmpresaGPT nasce em paralelo ao Promogg. A pasta `empresa_gpt/` representa a arquitetura alvo, mas nao recebe codigo operacional nesta fase.

O Promogg continua executando pelos modulos atuais. A plataforma sera extraida progressivamente por adaptadores, contratos e testes.

## Camadas Oficiais

```text
empresa_gpt/
├── core/
├── ai/
├── analytics/
├── security/
├── storage/
├── services/
├── product_intelligence/
├── operations/
├── monitoring/
├── deployment/
├── integrations/
├── shared/
└── docs/
```

## Responsabilidades

| Camada | Responsabilidade |
|---|---|
| `core` | Configuracao central, erros, logging, request id, policies e contratos base. |
| `ai` | Abstracoes de IA, revisao, recomendacao, prompts e memoria. |
| `analytics` | Coleta, normalizacao, consulta e exposicao de metricas. |
| `security` | Auth, RBAC, sessoes, tokens, CSRF, origem, validadores e auditoria sensivel. |
| `storage` | Repositorios, migracoes, conexoes, contratos de persistencia e adaptadores. |
| `services` | Casos de uso e regras de negocio reaproveitaveis. |
| `product_intelligence` | Produtos, categorias, sinais, metricas, ranking, aprendizado e recomendacoes consultivas. |
| `operations` | EGOC: painel operacional unico para produtos, saude, servicos, backups, alertas, auditorias, qualidade, riscos e uso de recursos. |
| `monitoring` | Saude, alertas, supervisao, incidentes e disponibilidade. |
| `deployment` | Validacoes, publicacao, rollback, ambientes e pipelines. |
| `integrations` | APIs externas, marketplaces, mensageria, Cloudflare, GitHub e OAuth. |
| `shared` | Utilitarios puros, parsing, formatacao e helpers sem dominio. |
| `docs` | ADRs, runbooks, contratos internos e notas de migracao. |

## Arquitetura de Transicao

1. O Promogg continua como sistema fonte.
2. Modulos candidatos sao identificados, mas ficam no lugar.
3. Contratos de plataforma sao documentados antes de extrair codigo.
4. Testes de equivalencia devem preceder qualquer movimento.
5. Adaptadores Promogg -> EmpresaGPT devem ser criados antes de substituir chamadas.

## Fronteiras

- Codigo com dependencia direta de Mercado Livre, afiliados, catalogo de ofertas ou site Promogg e dominio do cliente.
- Codigo de auth, seguranca, request id, validacao, analytics generico e monitoramento pode virar plataforma.
- Codigo de inteligencia de produto deve depender apenas de produtos, categorias, sinais, comportamento, metricas e recomendacoes, sem conhecer Mercado Livre ou afiliados.
- Codigo legado ou experimental so migra depois de estabilizacao e teste.

## Product Intelligence

O Product Intelligence Engine nasce como camada contratual reutilizavel para transformar sinais de produto em score e recomendacao.

Pipeline oficial:

```text
Produto
-> Visualizacao
-> Clique
-> Tempo na pagina
-> Categoria
-> Popularidade
-> Historico
-> Score Inteligente
-> Recomendacao
```

O Promogg podera usar esta camada futuramente para Home, UX, confianca, IA local, SEO e performance, sempre por adaptadores e sem mover codigo nesta fase.

## EmpresaGPT Operations Center

O EmpresaGPT Operations Center, ou EGOC, e a camada oficial de operacao da plataforma. Ele nao conhece Promogg; conhece apenas produtos registrados por contratos.

Fluxo alvo:

```text
EmpresaGPT
-> Produtos
-> Saude
-> Servicos
-> Backups
-> Alertas
-> Auditorias
-> Qualidade
-> Riscos
-> Uso de recursos
```

Cada produto devera informar nome, versao, status, disponibilidade, ultima atualizacao, ultimo backup, ultima auditoria, ultima validacao, Health Score, Risk Score, Quality Score e Deployment Status.

Regra arquitetural: nenhum produto deve ser considerado em producao sem integracao futura ao EGOC por contratos neutros e sem dependencia direta do runtime do produto.
