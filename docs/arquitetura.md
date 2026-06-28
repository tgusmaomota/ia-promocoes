# Arquitetura

O Promogg é organizado em quatro camadas práticas:

1. Operação local: coleta, curadoria, banco, painel, serviços e automações.
2. Integridade: validações, auditorias, proteção contra catálogo vazio e saneamento.
3. Publicação: geração de site estático e GitHub Pages.
4. Documentação e governança: comandos oficiais, segurança, manutenção e histórico.

## Componentes

- `ia_promocoes.py`: CLI principal e orquestração operacional.
- `banco.py`: SQLite local, migrações e registro operacional.
- `gerar_site.py`: geração local a partir do banco.
- `gerar_site_publico.py`: geração pública a partir de `catalogo_publico/ofertas.json`.
- `validar_catalogo_publico.py`: validação do contrato público sanitizado.
- `deploy_site.py`: preparação de deploy local/Pages com bloqueio de catálogo vazio.
- `servicos_promogg.py`: status e controle de serviços.
- `painel.py` e `painel_remoto.py`: interfaces operacionais.
- `.github/workflows/pages.yml`: publicação no GitHub Pages.

## Contratos de Segurança

- O site público deve ser gerável sem `.env`, `banco.db`, CSVs, `site/` local ou secrets.
- `dist_site/` é artefato gerado e não deve ser rastreado no Git.
- `catalogo_publico/ofertas.json` é a fonte pública versionada para CI.
- `banco.db`, logs, perfis de navegador e backups operacionais são locais.
