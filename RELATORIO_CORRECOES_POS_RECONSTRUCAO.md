# Relatório de Correções Pós-Reconstrução

- Atualizado em: 2026-06-26 11:22:29
- Nenhum deploy, Telegram real, ONLINE, coleta agressiva, exclusão de histórico ou limpeza de perfil foi executado.

## Métricas atuais
- 401 registrados em logs: 2339
- Categorias vazias: 0
- Categorias genéricas `ofertas` sem breadcrumb: 525
- Grupos de item_id duplicados ativos: 0
- Afiliados falhos/pendentes: 67
- Catálogo site/: 632 ofertas, 632 páginas, links inválidos=0, imagens inválidas=0, preços inválidos=0
- Catálogo dist_site/: 622 ofertas, 622 páginas

## Última ação
- Ação: auditar_duplicados
- Dry-run: True

## Antes/depois da última ação
- 401: 2339 -> 2339
- Categorias vazias: 0 -> 0
- Categorias genéricas: 525 -> 525
- Duplicados: 0 -> 0
- Afiliados falhos: 67 -> 67

## Arquivos alterados
- `mercadolivre_api.py`
- `meli_oauth.py`
- `correcoes_pos_reconstrucao.py`
- `gerador_afiliados_oficial.py`
- `gerar_site.py`
- `ia_promocoes.py`
- filtros auxiliares que ocultam `duplicado_oculto`

## Comandos criados
- `python3 ia_promocoes.py meli-auditar-api`
- `python3 ia_promocoes.py corrigir-categorias-vazias --dry-run`
- `python3 ia_promocoes.py corrigir-categorias-vazias`
- `python3 ia_promocoes.py auditar-duplicados`
- `python3 ia_promocoes.py corrigir-duplicados --dry-run`
- `python3 ia_promocoes.py corrigir-duplicados`
- `python3 ia_promocoes.py reprocessar-afiliados-falhos --dry-run`
- `python3 ia_promocoes.py reprocessar-afiliados-falhos`

## Status
- Seguro para commit: depende da validação final e revisão do worktree, que contém alterações pré-existentes.
- Seguro para deploy: somente se `validar --somente-leitura`, qualidade do catálogo e estado MANUTENCAO/ONLINE planejado estiverem corretos.
