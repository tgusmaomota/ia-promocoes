# Relatório de Recuperação do Banco a partir do Catálogo

- Gerado em: 2026-06-24 11:15:23
- Modo: execução real
- Fontes: site/ofertas.json, dist_site/ofertas.json
- Backup: backups/recuperacao_banco_catalogo/20260624_111521

## Total analisado
- Catálogo restaurado: 622
- Itens do catálogo existentes no banco: 622
- Produtos indisponíveis: 619
- Postagens aprovado_auto/manual/publicado: 464/118/40
- Com meli.la válido: 622
- Com preço válido: 622
- Recuperáveis com segurança: 619
- Precisam permanecer pendentes/não elegíveis: 3

## Resultado da recuperação
- Recuperados nesta execução: 619
- Movidos para `pendente_revisao` nesta execução: 2
- Mantidos indisponíveis entre os itens analisados: 0
- Motivos pendentes/não elegíveis: evidência registrada de anúncio finalizado/404/pausado; item_id inválido

## Banco antes/depois
- Produtos indisponíveis: 872 -> 253
- Postagens elegíveis: 655 -> 655
- Histórico de preços (preservado e acrescido): 2920 -> 3539

## Catálogo gerado após recuperação
- Ofertas: 622
- Páginas: 622
- Queda: 0.00%
- Protegido/abortado: não
- Bloqueios: nenhum

## Motivos
- Recuperação somente para itens do catálogo estático com página, meli.la, preço, imagem e título válidos, sem evidência local de finalização.
- Itens incertos são mantidos/convertidos para pendente_revisao; nenhum item fora do catálogo foi promovido.
- Não houve coleta, monitoramento, Telegram, ONLINE, deploy ou alteração de dist_site.
