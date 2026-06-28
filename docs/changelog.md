# Changelog

## 2026-06-27

### Organização e Segurança do Git

- Limpeza inicial do índice Git para remover artefatos gerados.
- Remoção de relatórios, CSVs, TXT operacionais e `site/` do índice.
- `dist_site/` removido do Git após validação do workflow verde.
- `.gitignore` reforçado para artefatos gerados, banco local, logs, backups, perfis de navegador e estados locais.

### Catálogo Público

- Criação de `catalogo_publico/ofertas.json` como fonte pública sanitizada.
- Criação de `validar_catalogo_publico.py`.
- Validação de campos públicos obrigatórios e bloqueio de campos sensíveis.

### Geração Estática

- Criação de `gerar_site_publico.py`.
- Geração de `dist_site/` sem depender de `.env`, `banco.db`, CSVs, `site/` local ou secrets.
- Preservação de layout, busca, categorias, paginação, imagens, SEO, sitemap e CNAME.

### Proteção Contra Deploy Vazio

- `deploy_site.py` passou a validar catálogo gerado.
- Deploy local/GitHub Pages é bloqueado se o catálogo estiver vazio ou abaixo do mínimo configurado.

### GitHub Pages

- Workflow atualizado para gerar `dist_site/` a partir do catálogo público no GitHub Actions.
- Publicação validada com `promogg.com.br`.

### Documentação

- Criação da estrutura `docs/`.
- Consolidação de comandos, deploy, monitoramento, API, backend, segurança, manutenção, roadmap e changelog.
- Documentos originais preservados em `docs/historico/originais/`.
- Relatórios temporários movidos para `docs/historico/relatorios/`.
