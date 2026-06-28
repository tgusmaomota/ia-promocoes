# Backend

O backend atual é composto por scripts Python, serviços locais e painel Streamlit. A entrada principal é `ia_promocoes.py`, que expõe comandos de operação, validação, curadoria, publicação e manutenção.

Ainda não existe uma API autenticada própria do Promogg. A autenticação e autorização internas serão criadas em paralelo ao backend atual, sem interromper CLI, Streamlit local, geração estática e GitHub Pages.

## Áreas Principais

- Coleta e captura: `coletor_mercadolivre.py`, `coletor_mercadolivre_api.py`, `captura_hibrida.py`.
- Curadoria e score: `curadoria_automatica.py`, `ia_revisora.py`, `auditoria_score.py`.
- Afiliados: `gerador_afiliados_oficial.py`, `gerador_link_mercadolivre.py`.
- Catálogo e integridade: `catalogo_integridade.py`, `qualidade_catalogo.py`, `integridade_paginas_produto.py`.
- Assistente local: `promogg_assistente.py`, documentado originalmente em `docs/historico/originais/README_ASSISTENTE_OLLAMA.md`.
- Analytics: `analytics_promogg.py`, `servidor_analytics.py`.
- Serviços locais: `servicos_promogg.py`, `servidor_site.py`, `painel.py`, `painel_remoto.py`.

## Estado Atual

- A operação é local e comandada por CLI/Streamlit.
- O banco operacional é SQLite em `banco.db`.
- O painel Streamlit deve rodar localmente ou atrás de Cloudflare Tunnel + Cloudflare Access.
- O site público é estático e gerado a partir de catálogo sanitizado.
- A auditoria atual registra eventos operacionais, mas ainda não há identidade forte por usuário interno.

## API Autenticada Planejada

A API será criada em paralelo, começando por `/api/v1`. A primeira etapa é read-only e usa somente `catalogo_publico/ofertas.json`, sem consultar `banco.db` e sem implementar autenticação real.

Objetivos:

- preservar o backend atual durante a transição;
- iniciar com rotas somente leitura e health checks;
- adicionar autenticação JWT e refresh token seguro;
- aplicar RBAC em ações críticas;
- padronizar validação, erros, logs, auditoria e rate limiting;
- permitir que o painel futuro consuma a API em vez de executar comandos diretamente.

Endurecimento atual da API read-only:

- testes automatizados em `tests/test_api_readonly.py`;
- headers de segurança em todas as respostas JSON;
- logs mínimos com `request_id`, método, path, status code e duração;
- CORS restrito por allowlist, sem wildcard na configuração padrão;
- erros padronizados com `request_id`.

Comando local planejado para a API read-only:

```bash
uvicorn api_promogg.main:app --host 127.0.0.1 --port 8001 --reload
```

Rotas iniciais:

- `GET /api/v1/health`
- `GET /api/v1/health/detalhada`
- `GET /api/v1/ofertas`
- `GET /api/v1/ofertas/{oferta_id}`
- `GET /api/v1/categorias`

Validação de testes:

```bash
python3 -m pytest tests/test_api_readonly.py
```

## Assistente

O assistente usa dados públicos e regras locais para responder perguntas sobre ofertas. A documentação original foi preservada em `docs/historico/originais/README_ASSISTENTE_OLLAMA.md`.

## Boas Práticas

- Não logar tokens, senhas, cookies, secrets ou URLs sensíveis.
- Usar consultas parametrizadas no SQLite.
- Validar dados antes de publicar.
- Manter comandos destrutivos protegidos por simulação, backup ou aprovação explícita.
- Não expor Streamlit diretamente na internet.
- Não adicionar autenticação parcial como remendo antes da base de sessões, usuários, RBAC e auditoria.
