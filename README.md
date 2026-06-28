# IA-Promoções / Promogg

Promogg é um sistema de curadoria, validação e publicação de ofertas com foco em segurança operacional. O projeto coleta e qualifica ofertas, mantém histórico local, gera um site estático público e publica o conteúdo pelo GitHub Pages a partir de um catálogo público sanitizado.

## Visão Geral

O fluxo atual separa dados operacionais privados do artefato público:

1. A operação local mantém banco, logs, sessões e automações fora do Git.
2. O catálogo público sanitizado fica em `catalogo_publico/ofertas.json`.
3. O site público é gerado por `gerar_site_publico.py` sem depender de `.env`, `banco.db`, CSVs, `site/` local ou secrets.
4. O GitHub Actions gera `dist_site/` no runner e publica no GitHub Pages.

## Arquitetura

- CLI principal: `ia_promocoes.py`
- Serviços locais: `servicos_promogg.py`, `servidor_site.py`, `servidor_analytics.py`
- Banco local: `banco.py` e `banco.db` ignorado
- Geração privada/local: `gerar_site.py`
- Geração pública/CI: `gerar_site_publico.py`
- Catálogo público: `catalogo_publico/ofertas.json`
- Deploy Pages: `.github/workflows/pages.yml`

## Estrutura do Projeto

```text
.
├── README.md
├── catalogo_publico/
├── docs/
├── .github/
├── *.py
├── requirements.txt
└── .env.example
```

Artefatos como `site/`, `dist_site/`, `logs/`, `backups/`, `banco.db`, perfis de navegador e relatórios operacionais ficam fora do Git.

## Instalação

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

## Configuração

Copie `.env.example` para `.env` e preencha somente localmente. Nunca envie `.env`, tokens, cookies, perfis de navegador, banco local ou logs para o Git.

## Segurança

Princípios do projeto:

- publicar somente dados sanitizados;
- manter segredos fora do Git;
- bloquear deploy com catálogo vazio;
- validar o catálogo antes de publicar;
- separar operação local de geração pública;
- não expor tokens, cookies, sessões, banco ou logs.

## Deploy

O GitHub Pages usa `catalogo_publico/ofertas.json` e gera `dist_site/` dentro do GitHub Actions:

```bash
python3 validar_catalogo_publico.py
python3 gerar_site_publico.py --fonte catalogo_publico/ofertas.json --destino dist_site --dominio promogg.com.br
python3 validar_catalogo_publico.py --arquivo dist_site/ofertas.json
```

## Comandos Principais

```bash
python3 ia_promocoes.py comandos
python3 ia_promocoes.py validar --somente-leitura
python3 ia_promocoes.py checklist-divulgacao
python3 validar_catalogo_publico.py
python3 gerar_site_publico.py --fonte catalogo_publico/ofertas.json --destino /tmp/promogg_dist_teste --dominio promogg.com.br
```

## Documentação

- [Documentação](docs/README.md)
- [Comandos](docs/comandos.md)
- [Deploy](docs/deploy.md)
- [Segurança](docs/seguranca.md)
- [Monitoramento](docs/monitoramento.md)
- [Manutenção](docs/manutencao.md)
- [Roadmap](docs/roadmap.md)
- [Changelog](docs/changelog.md)

## Roadmap

Os próximos marcos incluem autenticação JWT, RBAC, OAuth2 Google/GitHub, MFA, bcrypt/Argon2, criptografia em repouso, CSP, CORS restritivo, auditoria completa, SIEM/logs, rate limiting, testes automatizados, Docker e CI/CD completo.
