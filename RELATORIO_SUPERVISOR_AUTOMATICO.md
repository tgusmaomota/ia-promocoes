# Relatório do Supervisor Automático

- Gerado em: 2026-06-26 13:12:40
- Modo: execução real

## Configuração
- PROMOGG_SUPERVISOR_PUBLICAR: False
- PROMOGG_SUPERVISOR_TELEGRAM_ALERTAS: True
- PROMOGG_SUPERVISOR_INTERVALO_MINUTOS: 60
- PROMOGG_SUPERVISOR_MAX_ERROS_SEGUIDOS: 3
- PROMOGG_SUPERVISOR_ALERTA_COOLDOWN_MINUTOS: 60

## Último ciclo
- Status final: ok
- Modo atual: degradado_nao_bloqueante
- Ofertas públicas: 751
- Páginas: 751
- Pendentes: 1
- Aprovadas auto: 703
- Rejeitadas: 137

## Alertas enviados/simulados
- intervencao_humana_necessaria: cooldown ativo | dry_run=False
- telegram_ofertas_bloqueado: cooldown ativo | dry_run=False
- ciclo_concluido: cooldown ativo | dry_run=False

## Bloqueios
- nenhum

## Bloqueios de publicação
- Git possui alterações bloqueantes para publicação
- PROMOGG_SUPERVISOR_PUBLICAR=false

## Avisos não bloqueantes
- api_busca_403_fallback: API busca ML em 403, usando fallback Playwright.
- playwright_login_evento_resolvido: Evento anterior de login necessário não bloqueia: perfil Playwright está disponível/logado.

## Status Mercado Livre
- Problemas detectados: 2
- /users/me atual: ok
- Item atual: ok
- Categoria: não testada/falhou
- Modo ML: degradado_nao_bloqueante
- Bloqueantes ML: 0
- Avisos ML: 2
- api_401_403: API Mercado Livre respondeu HTTP 403; fallback/degradação pode ser necessária.
- playwright_logout: Playwright/Mercado Livre registrou login necessário.

## Status Playwright
- OK: True
- Modo: normal
- Motivo: sessão validada via venv/bin/python

## Status catálogo
- Qualidade: APROVADO COM RESSALVAS NÃO BLOQUEANTES
- Ressalvas bloqueantes: 0
- Ressalvas informativas: 2

## Recomendação
Supervisor pronto. Publicação real segue protegida por validação, Git, catálogo, qualidade e PROMOGG_SUPERVISOR_PUBLICAR=true.
