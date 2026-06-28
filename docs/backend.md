# Backend

O backend é composto por scripts Python e serviços locais. A entrada principal é `ia_promocoes.py`, que expõe comandos de operação, validação, curadoria, publicação e manutenção.

## Áreas Principais

- Coleta e captura: `coletor_mercadolivre.py`, `coletor_mercadolivre_api.py`, `captura_hibrida.py`.
- Curadoria e score: `curadoria_automatica.py`, `ia_revisora.py`, `auditoria_score.py`.
- Afiliados: `gerador_afiliados_oficial.py`, `gerador_link_mercadolivre.py`.
- Catálogo e integridade: `catalogo_integridade.py`, `qualidade_catalogo.py`, `integridade_paginas_produto.py`.
- Assistente local: `promogg_assistente.py`, documentado originalmente em `docs/historico/originais/README_ASSISTENTE_OLLAMA.md`.
- Analytics: `analytics_promogg.py`, `servidor_analytics.py`.

## Assistente

O assistente usa dados públicos e regras locais para responder perguntas sobre ofertas. A documentação original foi preservada em `docs/historico/originais/README_ASSISTENTE_OLLAMA.md`.

## Boas Práticas

- Não logar tokens, senhas, cookies, secrets ou URLs sensíveis.
- Usar consultas parametrizadas no SQLite.
- Validar dados antes de publicar.
- Manter comandos destrutivos protegidos por simulação, backup ou aprovação explícita.
