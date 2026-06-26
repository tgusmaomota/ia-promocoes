# Relatório de Auditoria Geral do Promogg

## Escopo e segurança
- Auditoria executada sem deploy, sem Telegram real, sem ONLINE, sem coleta real e sem limpeza de perfil.
- Banco aberto em modo somente leitura durante as análises de integridade.
- Checkpoints, perfil Playwright, catálogo estático, histórico e backups foram preservados.

## Arquitetura encontrada
- cli_master: `ia_promocoes.py`
- persistencia: `banco.py + SQLite banco.db`
- coleta: `coletor_mercadolivre_api.py -> coletor_mercadolivre.py -> coleta_confiavel.py/Playwright`
- historico: `historico_precos + metricas_historico.py`
- curadoria: `analisador_promocao.py + fila_postagens.py + ia_revisora.py`
- publicacao: `gerar_site.py + catalogo_integridade.py + publicar_site_git.py`
- engajamento: `publicador_telegram.py + whatsapp_posts.txt`
- assistente: `promogg_assistente.py + memoria_produtos`
- analytics: `analytics_promogg.py + servidor_analytics.py + cliques`
- operacao: `estado_sistema.py + scheduler.py + producao_promogg.py + saude_sistema.py`

## Métricas do código
- Arquivos Python analisados: 75
- Linhas Python analisadas: 14822
- `except Exception`: 92
- `except:` amplo: 14
- Módulos com Playwright: 9
- Módulos com chamadas HTTP: 11

### Maiores módulos
- `ia_promocoes.py`: 1674 linhas, 93 funções
- `gerar_site.py`: 1536 linhas, 40 funções
- `banco.py`: 1366 linhas, 44 funções
- `saude_sistema.py`: 455 linhas, 20 funções
- `promogg_assistente.py`: 452 linhas, 25 funções
- `painel.py`: 411 linhas, 2 funções
- `agente_ofertas.py`: 407 linhas, 9 funções
- `auditoria_sistema.py`: 360 linhas, 12 funções

## Banco SQLite e histórico
- Integridade SQLite: `ok`
- Tabelas: 17
- Produtos: 974
- Postagens: 882
- Histórico de preços: 4868
- Produtos sem histórico válido: 0
- Postagens elegíveis sem meli.la: 0
- Duplicidades por item_id: 0
- Histórico inconclusivo/API: 26

### Fontes de preço
- indisponivel: 2856
- coletado: 905
- recuperacao_catalogo_estatico: 619
- playwright_fallback: 206
- playwright_cache_api_403: 188
- baseline_local: 68
- api_item: 23
- erro_api: 3

## Catálogo público
- `site/`: 45 ofertas, 45 páginas, erro=``
- `dist_site/`: 45 ofertas, 45 páginas, erro=``
- Proteção aprovada: não
  - Bloqueio: queda de catálogo de 92.77% em relação a backups/ultimo_catalogo_aprovado.json (622 -> 45); limite é 20%

## Segurança
- `.gitignore` presente: sim
- `.env.example` com valor sensível preenchido: não
- Ignorado no Git `.env`: sim
- Ignorado no Git `banco.db`: sim
- Ignorado no Git `backups/`: sim
- Ignorado no Git `logs/`: sim
- Ignorado no Git `perfil_mercadolivre/`: sim
- Ignorado no Git `.coleta_confiavel_checkpoint.json`: sim
- JSON público com marcadores sensíveis em `site/`: 0
- JSON público com marcadores sensíveis em `dist_site/`: 0

## Problemas encontrados
- `ia_promocoes.py` concentra muitas responsabilidades e comandos; recomenda-se fatiar comandos por domínio.
- `gerar_site.py` é monolítico; HTML, CSS, dados e validação ficam acoplados.
- Existem agentes legados CSV/Playwright paralelos ao pipeline atual, aumentando risco de uso acidental.
- Muitos `except Exception` dificultam distinguir erro temporário, erro de autenticação e indisponibilidade real.
- O catálogo local atual está degradado em relação à referência aprovada quando a proteção acusa queda.
- Há múltiplos pontos de Playwright; o fluxo novo deve virar caminho oficial e os legados devem ser descontinuados.

## Melhorias implementadas nesta auditoria
- Adicionado `metricas_historico.py` para tendência, confiabilidade, origem e estatísticas reutilizáveis.
- IA consultiva passou a expor origem do preço e confiabilidade sem inventar dados.
- Adicionado comando `auditar-sistema` com relatório geral somente-leitura.
- Auditoria de segurança verifica `.gitignore`, JSON público e marcadores sensíveis.
- Auditoria consolida banco, histórico, catálogo, módulos grandes, exceções amplas e candidatos à remoção.

## Arquivos candidatos à remoção ou quarentena futura
- `agente_afiliado.py`
- `agente_curadoria.py`
- `agente_publicador.py`
- `agente_site.py`
- `agente_telegram.py`
- `app.py`
- `corrigir_posts.py`
- `gerar_token.py`
- `limpar_invalidos.py`
- `trocar_code.py`

## Recomendações próximas
- Transformar `ia_promocoes.py` em roteador fino, movendo comandos para módulos `commands/`.
- Separar templates/assets do `gerar_site.py` e criar testes de contrato para `ofertas.json`.
- Marcar agentes legados como deprecated antes de qualquer remoção física.
- Criar tabela/evento de pipeline por execução para rastrear API -> Playwright -> histórico -> curadoria -> site -> Telegram.
- Evoluir `except Exception` críticos para exceções de domínio: `ErroTemporario`, `LoginNecessario`, `IndisponibilidadeConfirmada`.
- Restaurar ou proteger o catálogo público antes de qualquer produção se a validação continuar abaixo da referência.

## Impacto esperado
- Desempenho: auditoria evita varreduras manuais e identifica módulos grandes/gargalos sem coleta remota.
- Segurança: reforça conferência de segredos, Git e JSON público antes de produção.
- Manutenção: centraliza métricas de histórico e reduz duplicação conceitual entre assistente/relatórios.
- Automação: cria diagnóstico único para decidir se o pipeline pode avançar ou deve pausar.

## Status para commit e produção
- Commit: seguro apenas revisando junto as alterações pré-existentes do workspace, que são numerosas.
- Produção: não seguro enquanto o catálogo local estiver degradado ou a validação somente leitura falhar.
