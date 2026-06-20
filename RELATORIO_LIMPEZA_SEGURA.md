# Relatório de Limpeza Segura

Data da auditoria: 2026-06-19

## Mantidos

- **Núcleo de operação:** `ia_promocoes.py`, `banco.py`, `scheduler.py`, `coletor_mercadolivre.py`, `mercadolivre_api.py`, `fila_postagens.py`, `publicador_telegram.py` e `controle_ofertas.py`.
- **Site e GitHub Pages:** `gerar_site.py`, `deploy_site.py`, `publicar_site_git.py`, `servidor_site.py`, `site/`, `dist_site/`, `.github/` e `README_GITHUB_PAGES.md`.
- **Dados e histórico:** `banco.db`, `posts_prontos.csv`, `produtos.csv`, `historico_precos.csv`, `backups/`, perfis de navegador e `.env`. Esses itens não entram na quarentena.
- **Painel, analytics e IA:** `painel.py`, `servidor_analytics.py`, `promogg_assistente.py`, `ia_revisora.py`, `consulta_precos.py`, `saude_sistema.py` e `operacao_sistema.py`.
- **Módulos ainda utilizados indiretamente:** `agente_ofertas.py` é importado pela coleta atual; os demais módulos de análise e CSV permanecem para compatibilidade e migração.

## Produção e Painel

- Produção: coleta Mercado Livre, fila de aprovação, monitoramento, geração do site, deploy estático e publicação controlada no Telegram.
- Painel: `painel.py`, `controle_ofertas.py`, analytics, saúde, assistentes e revisora.
- Histórico/preços: `banco.py`, `monitor_precos.py`, `consulta_precos.py` e `historico_precos.csv` legado.
- Site: `site/` é a fonte estática; `dist_site/` é a cópia pronta para GitHub Pages. Ambos devem ser preservados.

## Candidatos Confirmados para Quarentena

| Caminho | Motivo | Decisão |
| --- | --- | --- |
| `backup_remocao/` | Scripts, testes, imagens e cópias históricas sem referências no fluxo atual. | Mover mantendo a estrutura. |
| `relatorio_homologacao.txt` | Relatório histórico sem consumidores ativos. | Mover mantendo o conteúdo. |
| `relatorio_limpeza.txt` | Relatório antigo, substituído por este documento. | Mover mantendo o conteúdo. |

## Em Dúvida: Mantidos

- `agente_afiliado.py`, `agente_curadoria.py`, `agente_publicador.py`, `agente_site.py`, `agente_telegram.py`, `app.py`, `dashboard_receita.py` e utilitários antigos: não são chamados pelo comando principal, mas podem ser usados manualmente.
- CSVs `produtos_afiliados.csv`, `produtos_busca.csv`, `produtos_filtrados.csv`, `historico_produtos.csv` e `historico_telegram.csv`: possíveis dados legados; não serão movidos sem exportação/revisão funcional.
- Arquivos `telegram.txt`, `whatsapp.txt`, `instagram.txt`, `promobit.txt`, `site_promocoes.html` e `whatsapp_posts.txt`: saídas legadas ou manuais; alguns ainda são atualizados pelo publicador, portanto ficam mantidos.

## Segurança

- A limpeza não apaga arquivos: usa `quarentena_remocao/<data>/` com estrutura original.
- Antes da movimentação é criado backup do SQLite, CSVs, fontes Python, `site/` e `dist_site/` em `backups/limpeza_segura/`.
- `.env`, banco, perfis de navegador, `venv/`, backups existentes e arquivos públicos não são candidatos.

## Execução da Limpeza

- Backup pré-limpeza: `backups/limpeza_segura/20260619_172951/`.
- Quarentena reversível: `quarentena_remocao/20260619_172952/`.
- Movidos: `backup_remocao/`, `relatorio_homologacao.txt` e `relatorio_limpeza.txt`.
- Nenhum arquivo foi apagado.

## Validação Antes e Depois

Os comandos abaixo passaram antes e depois da movimentação:

```bash
python3 ia_promocoes.py validar
python3 ia_promocoes.py gerar-site
python3 ia_promocoes.py simular
python3 ia_promocoes.py status
python3 -m py_compile *.py
```

A simulação executou em modo `DRY-RUN`, sem enviar Telegram. Os erros exibidos em `status` são falhas antigas de rede do monitoramento e não foram criados pela limpeza.

## Tamanho

- Antes: `512 MB` no diretório do projeto.
- Depois: `515 MB`, incluindo `4,4 MB` de backups e `1,4 MB` em quarentena.
- A raiz operacional foi reduzida pelos candidatos movidos; o aumento total é proposital para manter reversibilidade.
