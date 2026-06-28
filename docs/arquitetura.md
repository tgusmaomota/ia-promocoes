# Arquitetura

O Promogg é organizado hoje em quatro camadas práticas:

1. Operação local: coleta, curadoria, banco, painel, serviços e automações.
2. Integridade: validações, auditorias, proteção contra catálogo vazio e saneamento.
3. Publicação: geração de site estático e GitHub Pages.
4. Documentação e governança: comandos oficiais, segurança, manutenção e histórico.

## Componentes Atuais

- `ia_promocoes.py`: CLI principal e orquestração operacional.
- `banco.py`: SQLite local, migrações e registro operacional.
- `gerar_site.py`: geração local a partir do banco.
- `gerar_site_publico.py`: geração pública a partir de `catalogo_publico/ofertas.json`.
- `validar_catalogo_publico.py`: validação do contrato público sanitizado.
- `deploy_site.py`: preparação de deploy local/Pages com bloqueio de catálogo vazio.
- `servicos_promogg.py`: status e controle de serviços.
- `painel.py` e `painel_remoto.py`: interfaces operacionais.
- `servidor_analytics.py` e `analytics_cloudflare_worker.js`: analytics público sem identificador pessoal.
- `.github/workflows/pages.yml`: publicação no GitHub Pages.

## Contratos de Segurança

- O site público deve ser gerável sem `.env`, `banco.db`, CSVs, `site/` local ou secrets.
- `dist_site/` é artefato gerado e não deve ser rastreado no Git.
- `catalogo_publico/ofertas.json` é a fonte pública versionada para CI.
- `banco.db`, logs, perfis de navegador e backups operacionais são locais.
- O painel remoto não deve ser exposto diretamente; quando usado remotamente, deve ficar atrás de Cloudflare Tunnel + Cloudflare Access.

## Arquitetura Futura Planejada

A arquitetura futura aprovada prevê uma aplicação pronta para produção, com API autenticada, autorização por RBAC, auditoria completa e workers isolados.

Estrutura sugerida:

```text
frontend/
api/
auth/
core/
models/
services/
workers/
integrations/
tests/
docs/
```

Responsabilidades:

- `frontend/`: painel administrativo autenticado.
- `api/`: rotas HTTP versionadas, começando por `/api/v1`.
- `auth/`: usuários, senhas, JWT, refresh tokens, sessões, OAuth2 e MFA.
- `core/`: configuração, segurança, logging, middlewares e policies.
- `models/`: entidades persistidas e contratos de dados.
- `services/`: regras de negócio de ofertas, curadoria, publicação e operação.
- `workers/`: coleta, monitoramento, publicação, analytics e tarefas assíncronas.
- `integrations/`: Mercado Livre, Telegram, GitHub, Cloudflare e outros provedores.
- `tests/`: testes automatizados de unidade, integração, API, autorização e segurança.
- `docs/`: documentação oficial, runbooks, decisões arquiteturais e histórico.

## Regra de Migração

Os arquivos Python atuais ainda não devem ser movidos para essa estrutura sem uma etapa de refatoração separada. A próxima arquitetura deve nascer em paralelo ao fluxo atual, preservando CLI, painel local, geração estática e publicação pública até que existam testes e equivalência funcional.

Refatorações futuras devem ser planejadas por etapa, com validações antes e depois, para evitar perda de operação, quebra do catálogo público ou mistura de dados privados com artefatos públicos.
