# Frontend

O frontend público é estático e gerado por Python. Existem dois fluxos:

- `gerar_site.py`: gera `site/` a partir do banco local.
- `gerar_site_publico.py`: gera `dist_site/` a partir do catálogo público sanitizado.

## Artefatos Públicos

- `index.html`
- `ofertas.json`
- páginas por produto
- páginas por categoria
- `sitemap.xml`
- `robots.txt`
- `assistente/`
- `assistente_dados.json`
- assets como `style.css`, `app.js`, `analytics.js`, `logo.*` e favicons

## Regras

- `site/` e `dist_site/` são artefatos gerados.
- O GitHub Pages deve receber `dist_site/` gerado em CI.
- O catálogo público não deve conter campos internos.
- A busca, categorias, paginação, imagens e SEO devem ser validados antes de publicar.
