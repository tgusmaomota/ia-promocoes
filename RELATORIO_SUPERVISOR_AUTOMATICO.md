# Relatório do Supervisor Automático

- Gerado em: 2026-06-26 13:57:49
- Modo: dry-run

## Configuração
- PROMOGG_SUPERVISOR_PUBLICAR: True
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
- intervencao_humana_necessaria: cooldown ativo | dry_run=True
- login_mercado_livre_necessario: simulado | dry_run=True
- deploy_bloqueado: simulado | dry_run=True

## Bloqueios
- Mercado Livre/API/Playwright em modo degradado bloqueante

## Bloqueios de publicação
- Git possui alterações bloqueantes para publicação
- ciclo-automatico --publicar ainda não está homologado pelas travas de segurança

## Avisos não bloqueantes
- api_busca_403_fallback: API busca ML em 403, usando fallback Playwright.
- playwright_login_evento_resolvido: Evento anterior de login necessário não bloqueia: perfil Playwright está disponível/logado.
- playwright_nao_verificado_dry_run: Playwright não verificado no dry-run; perfil existe e não está bloqueado.

## Status Mercado Livre
- Problemas detectados: 2
- /users/me atual: não confirmado
- Item atual: não confirmado
- Categoria: não testada/falhou
- Modo ML: degradado
- Bloqueantes ML: 1
- Avisos ML: 3
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
- Segurança publicação: ok
- Segurança críticos: 0
- Segurança bloqueantes: 0

## Recomendação
Rode login-mercadolivre e testar-playwright-sessao antes de retomar coleta/afiliados.
