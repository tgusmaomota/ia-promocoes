# Relatório de Recuperação do Banco a partir do Catálogo

- Gerado em: 2026-06-26 07:40:12
- Modo: execução real
- Fontes: site/ofertas.json, dist_site/ofertas.json
- Backup: backups/recuperacao_banco_catalogo/20260626_074010

## Total analisado
- Catálogo restaurado: 632
- Itens do catálogo existentes no banco: 632
- Produtos indisponíveis: 0
- Postagens aprovado_auto/manual/publicado: 468/118/46
- Com meli.la válido: 632
- Com preço válido: 632
- Recuperáveis com segurança: 629
- Precisam permanecer pendentes/não elegíveis: 3

## Resultado da recuperação
- Recuperados nesta execução: 629
- Movidos para pendente_revisao nesta execução: 0
- Mantidos indisponíveis entre os itens analisados: 0
- Motivos pendentes/não elegíveis: evidência registrada de anúncio finalizado/404/pausado; item_id inválido

## Banco antes/depois
- Produtos indisponíveis: 258 -> 258
- Postagens elegíveis: 665 -> 665
- Histórico de preços (preservado e acrescido): 5500 -> 6129

## Catálogo gerado após recuperação
- Ofertas: 632
- Páginas: 632
- Queda: 0.00%
- Protegido/abortado: não
- Bloqueios: nenhum

## Motivos
- Recuperação somente para itens do catálogo estático com página, meli.la, preço, imagem e título válidos, sem evidência local de finalização.
- Itens incertos são mantidos/convertidos para pendente_revisao; nenhum item fora do catálogo foi promovido.
- Não houve coleta, monitoramento, Telegram, ONLINE, deploy ou alteração de dist_site.
