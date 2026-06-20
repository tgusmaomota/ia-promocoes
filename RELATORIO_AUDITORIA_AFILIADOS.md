# Relatório de Auditoria de Afiliados - Promogg

- Gerado em: 2026-06-19 21:04:03
- MERCADO_LIVRE_AFFILIATE_ID não é necessário para links oficiais https://meli.la/...
- A variável permanece opcional apenas para o método legado de acrescentar campanha a um permalink comum.

## Uso no código
- gerador_link_mercadolivre.py aceita meli.la diretamente e só usa MERCADO_LIVRE_AFFILIATE_ID para permalink mercadolivre.com.
- fila_postagens.py, gerar_site.py e publicador_telegram.py exigem link válido, não exigem a variável diretamente.
- recuperacao_base.py não bloqueia mais a reconstrução pela ausência da variável.
- agente_ofertas.py passa a preferir meli.la quando esse link existir no card.

## Contagens
- produtos: meli.la=86; campanha=0; sem afiliação=6; inválido=0
- postagens: meli.la=86; campanha=0; sem afiliação=1; inválido=0
- historico: meli.la=200; campanha=0; sem afiliação=32; inválido=0

## Impacto
- Coleta: links meli.la encontrados são preservados como afiliados.
- Curadoria: só candidatos sem link válido permanecem fora da aprovação/publicação.
- Site: ofertas com meli.la válido continuam publicáveis; dados internos não são expostos.
- Falhas históricas na geração oficial: 37.
- Motivo de bloqueio atual: Novos candidatos sem meli.la continuam sem aprovação até receberem um link afiliado válido.
