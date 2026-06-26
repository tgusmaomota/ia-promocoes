# Relatório de Correções Pós-Reconstrução

- Atualizado em: 2026-06-26 13:15:40
- Nenhum deploy, Telegram real, ONLINE, coleta agressiva, exclusão de histórico ou limpeza de perfil foi executado.

## Métricas atuais
- 401 registrados em logs: 2339
- Categorias vazias: 0
- Categorias genéricas `ofertas` sem breadcrumb: 537
- Grupos de item_id duplicados ativos: 0
- Afiliados falhos/pendentes: 75
- Catálogo site/: 751 ofertas, 751 páginas, links inválidos=0, imagens inválidas=0, preços inválidos=0
- Catálogo dist_site/: 751 ofertas, 751 páginas

## Última ação
- Ação: meli_auditar_api
- Dry-run: True

## Antes/depois da última ação
- 401: 2339 -> 2339
- Categorias vazias: 0 -> 0
- Categorias genéricas: 537 -> 537
- Duplicados: 0 -> 0
- Afiliados falhos: 75 -> 75

## Auditoria Mercado Livre API
- OAuth local configurado: sim
- `/users/me`: ok
- Item: ok
- Categoria: não testada/falhou
- Refresh automático: não necessário

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
