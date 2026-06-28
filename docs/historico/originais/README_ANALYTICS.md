# Analytics próprio do Promogg

O Promogg registra somente `item_id`, título do produto, categoria, origem, página de origem, tipo de evento e data/hora do servidor. Não registra IP, cookie, conta, token, e-mail ou user-agent.

O GitHub Pages é estático: um servidor escutando em `127.0.0.1` no Mac só recebe testes locais. Para visitantes reais, configure um endpoint HTTPS público.

## Ativação

1. Para homologação local, execute:

```bash
python3 ia_promocoes.py gerar-site
python3 ia_promocoes.py analytics-teste
python3 ia_promocoes.py analytics-status
```

2. Para visitantes reais, hospede `servidor_analytics.py` em uma máquina sob seu controle, atrás de proxy HTTPS, ou use o modelo `analytics_cloudflare_worker.js` com o schema `analytics_cloudflare_d1.sql` e `wrangler.analytics.example.toml`.
3. Publique-o atrás de HTTPS em uma URL como `https://analytics.seudominio.com/api/cliques`.
4. Configure no `.env` local:

```env
PROMOGG_ANALYTICS_URL=https://analytics.seudominio.com/api/cliques
PROMOGG_ANALYTICS_ORIGINS=https://promogg.com.br
```

5. Inicie o processo localmente ou no servidor:

```bash
venv/bin/python servidor_analytics.py
```

O servidor escuta apenas em `127.0.0.1:8787`; use um proxy HTTPS para expor somente `/api/cliques`. Restrinja CORS a `https://promogg.com.br` e aplique rate limiting no proxy/Worker. Nunca exponha o SQLite, `.env` ou o painel.

6. Gere e publique o catálogo para incluir apenas a URL pública do endpoint:

```bash
python3 ia_promocoes.py subir-site
```

## Dashboard

Abra o painel com `python3 ia_promocoes.py painel`. A seção **Analytics de cliques** mostra produtos, categorias, dias e meses mais clicados.

No modo Cloudflare Worker, os eventos ficam no D1; a sincronização com o painel SQLite é uma etapa futura autenticada. O dashboard local reflete o modo local/VPS que usa este banco.
