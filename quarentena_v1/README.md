# Quarentena V1

Esta pasta guarda itens removidos do fluxo oficial da Versao Estavel 1.0 sem exclusao definitiva.

Nesta primeira passada, nenhum modulo Python operacional foi movido automaticamente, porque alguns arquivos com cara de legado ainda sao referenciados por geracao, restauracao ou homologacao do site.

Itens candidatos a quarentena futura:

- `telegram.txt`
- `whatsapp.txt`
- `whatsapp_posts.txt`
- `instagram.txt`
- `promobit.txt`
- `site_promocoes.html`
- `relatorio_auditoria_ofertas.txt`

Motivo para manter no lugar por enquanto: referencias em `publicador_telegram.py`, `agente_publicador.py`, `restauracao_catalogo.py`, `recuperacao_base.py`, `recuperacao_banco_catalogo.py` e `homologacao_publicacao.py`.
