# Mapa do Projeto IA-Promocoes / Promogg

## Entrada e comandos

- `ia_promocoes.py`: CLI principal (`producao`, `iniciar`, `reiniciar`, `parar`, `publicar`, `painel`, saúde e manutenção).
- `scheduler.py`: ciclo programado de coleta, fila, monitoramento e publicação controlada.

## Coleta e curadoria

- `coletor_mercadolivre.py`, `coletor_mercadolivre_api.py`, `mercadolivre_api.py`, `agente_ofertas.py`, `coleta_confiavel.py`: coleta Mercado Livre, fallback e checkpoint.
- `gerador_afiliados_oficial.py`, `gerador_link_mercadolivre.py`: geração e validação de links meli.la.
- `analisador_promocao.py`, `fila_postagens.py`, `controle_ofertas.py`: análise, fila e aprovação humana.

## Dados e histórico

- `banco.py`: SQLite, migrações, histórico de preços, eventos, analytics e auditoria.
- `monitor_precos.py`, `consulta_precos.py`: monitoramento diário e consultas locais.
- `recuperacao_indisponiveis.py`, `recuperacao_base.py`: recuperação segura com backup e relatórios.

## Site e GitHub Pages

- `gerar_site.py`: home, páginas de produto, SEO, sitemap, robots e 404.
- `deploy_site.py`, `publicar_site_git.py`: preparação e push do GitHub Pages.
- `site/`: fonte estática gerada. `dist_site/`: artefato publicado.

## Telegram e analytics

- `publicador_telegram.py`: validação e publicação controlada.
- `servidor_analytics.py`: endpoint local de cliques sem dados pessoais.

## IA e operação

- `promogg_assistente.py`: consulta local de preços com Ollama opcional.
- `ia_revisora.py`: parecer de ofertas sem aprovação automática.
- `saude_sistema.py`, `operacao_sistema.py`: saúde, backup e relatórios operacionais.
- `qualidade_catalogo.py`, `integridade_paginas_produto.py`: auditorias públicas de qualidade e integridade.

## Diretórios operacionais

- `site/`: fonte estática gerada; não contém banco, tokens ou logs.
- `dist_site/`: cópia pronta para GitHub Pages.
- `logs/`, `backups/`, perfis Playwright e `quarentena_remocao/`: locais, ignorados pelo Git.
- `RELATORIO_*.md`: evidências operacionais geradas localmente.

## Comandos essenciais

Consulte a lista atualizada em `python3 ia_promocoes.py comandos` e em `COMANDOS_PROMOGG.md`.
