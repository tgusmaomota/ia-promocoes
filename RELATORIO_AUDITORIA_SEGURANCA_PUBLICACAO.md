# Relatório de Auditoria de Segurança de Publicação

- Gerado em: 2026-06-27 19:12:37
- Status final: **ok**
- Críticos: 0
- Bloqueantes: 0
- Alertas: 0

## Métricas
- dist_site_arquivos: 1542
- git_nomes_suspeitos: 44
- git_versionados: 3238
- gitignore_faltantes: 0
- python_auditados: 84
- relatorios_auditados: 50
- site_arquivos: 1541

## Achados críticos
- nenhum

## Achados bloqueantes
- nenhum

## Alertas
- nenhum

## Correções/garantias aplicadas
- `.gitignore` reforçado para banco, SQLite, sessões, cookies, checkpoints, storage state, perfil Playwright, backups, logs e relatórios privados.
- Auditoria automática criada no comando `python3 ia_promocoes.py auditar-seguranca-publicacao`.
- Gate integrado ao supervisor e ao ciclo automático antes de liberar publicação.
- Nenhum token, cookie ou segredo foi impresso neste relatório.

## Decisão
- Publicação automática é segura apenas quando não houver achados críticos nem bloqueantes.
- Seguro para publicar automaticamente agora: sim
