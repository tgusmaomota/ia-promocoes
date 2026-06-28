# Deploy

O deploy público é feito via GitHub Pages. O workflow gera `dist_site/` dentro do GitHub Actions usando `catalogo_publico/ofertas.json`.

## Fluxo Atual

```bash
python3 validar_catalogo_publico.py
python3 gerar_site_publico.py --fonte catalogo_publico/ofertas.json --destino dist_site --dominio promogg.com.br
python3 validar_catalogo_publico.py --arquivo dist_site/ofertas.json
test "$(cat dist_site/CNAME)" = "promogg.com.br"
```

## GitHub Pages

O workflow está em `.github/workflows/pages.yml`. Ele:

1. baixa o repositório;
2. configura Python;
3. valida o catálogo público;
4. gera `dist_site/`;
5. valida o `ofertas.json` gerado;
6. valida `CNAME`;
7. publica o artefato no GitHub Pages.

## Proteções

- `deploy_site.py` bloqueia catálogo vazio.
- `gerar_site_publico.py` não depende de `.env`, `banco.db`, CSVs, `site/` local ou secrets.
- `dist_site/` fica fora do Git.
- `catalogo_publico/ofertas.json` é a fonte pública versionada.

## Documentos Originais

Preservados em:

- `docs/historico/originais/README_GITHUB_PAGES.md`
- `docs/historico/originais/README_SITE_PUBLICO.md`
- `docs/historico/originais/PRODUCAO_PROMOGG.md`
