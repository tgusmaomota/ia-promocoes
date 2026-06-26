# Relatório do Supervisor Automático

- Gerado em: 2026-06-26 12:44:44
- Modo: dry-run

## Configuração
- PROMOGG_SUPERVISOR_PUBLICAR: False
- PROMOGG_SUPERVISOR_TELEGRAM_ALERTAS: True
- PROMOGG_SUPERVISOR_INTERVALO_MINUTOS: 60
- PROMOGG_SUPERVISOR_MAX_ERROS_SEGUIDOS: 3
- PROMOGG_SUPERVISOR_ALERTA_COOLDOWN_MINUTOS: 60

## Último ciclo
- Status final: bloqueado
- Modo atual: degradado
- Ofertas públicas: 751
- Páginas: 751
- Pendentes: 1
- Aprovadas auto: 703
- Rejeitadas: 137

## Alertas enviados/simulados
- login_mercado_livre_necessario: simulado | dry_run=True
- telegram_ofertas_bloqueado: simulado | dry_run=True

## Bloqueios
- Git possui alterações bloqueantes para publicação
- Mercado Livre/API/Playwright em modo degradado

## Status Mercado Livre
- Problemas detectados: 2
- api_401_403: API Mercado Livre respondeu HTTP 403; fallback/degradação pode ser necessária.
- playwright_logout: Playwright/Mercado Livre registrou login necessário.

## Status Playwright
- OK: True
- Modo: nao_verificado_em_dry_run
- Motivo: perfil existe e não está bloqueado

## Status catálogo
- Qualidade: APROVADO COM RESSALVAS NÃO BLOQUEANTES
- Ressalvas bloqueantes: 0
- Ressalvas informativas: 2

## Recomendação
Rode login-mercadolivre e testar-playwright-sessao antes de retomar coleta/afiliados.
