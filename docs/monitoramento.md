# Monitoramento

O projeto possui monitoramento local de serviços e analytics próprio.

## Componentes

- `servicos_promogg.py`
- `analytics_promogg.py`
- `servidor_analytics.py`
- `monitor_precos.py`
- `saude_sistema.py`
- `operacao_sistema.py`
- Cloudflare Worker: `analytics_cloudflare_worker.js`
- Cloudflare D1: `analytics_cloudflare_d1.sql`

## Comandos Úteis

```bash
python3 ia_promocoes.py status
python3 ia_promocoes.py saude
python3 ia_promocoes.py saude-detalhada
python3 ia_promocoes.py analytics-status
python3 ia_promocoes.py monitorar-precos
```

## Regras

- Logs não devem conter segredos.
- Logs operacionais ficam fora do Git.
- Alertas devem ser acionáveis e evitar ruído.
- Eventos críticos devem registrar quem fez o quê, quando e de onde quando houver autenticação.

## Documento Original

Preservado em `docs/historico/originais/README_ANALYTICS.md`.
