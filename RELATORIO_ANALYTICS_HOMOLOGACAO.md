# Relatório de Homologação do Analytics

- Gerado em: 2026-06-20 13:30:18
- Dados pessoais: não coletados.

## Arquitetura atual
- O site estático usa `analytics.js` e envia somente eventos mínimos quando há endpoint HTTPS configurado.
- O servidor local escuta em `127.0.0.1`; por design, não é alcançável por visitantes externos.
- URL configurada no catálogo: não.
- Cliques externos podem ser recebidos agora: não.

## Métricas locais
- Total de cliques reais: 0
- Cliques reais hoje: 0
- Eventos de teste: 1
- Servidor local ativo: não
- JavaScript de analytics gerado: sim

## Teste local
- HTTP: 202 confirmado anteriormente
- Evento salvo: sim
- Tipo: teste
- Última execução: 2026-06-20 13:28:15

## Conclusão
- O modo local é homologado para testes e painel no mesmo ambiente.
- Para o GitHub Pages registrar visitantes reais, configure um endpoint HTTPS público com CORS restrito a `https://promogg.com.br`.
- Há um modelo opcional de Cloudflare Worker com D1 no repositório; ele não expõe SQLite, tokens, IPs ou cookies.
