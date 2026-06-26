# Relatório de Score Adaptativo

- Gerado em: 2026-06-26 16:43:18
- Fonte: banco local, histórico de preços, dados comerciais coletados e analytics local quando disponível.
- Aprendizado por clique: aguardando volume público suficiente; nenhum dado foi inventado.

## Componentes
- `score_integridade`: item_id, meli.la, preço, imagem, título, permalink e disponibilidade.
- `score_preco`: desconto atual e economia real.
- `score_historico`: menor preço, queda recente e observações históricas.
- `score_vendedor`: avaliação, vendidos, vendedor confiável, loja oficial e mais vendido.
- `score_categoria`: categoria real/confiável.
- `score_publicacao`: confiabilidade da fonte, histórico e aptidão de publicação.
- `score_final`: soma normalizada usada na decisão.

## Amostras
- pendente_revisao | final=61 | integridade=30, preço=10, histórico=2, vendedor=11, categoria=1, publicação=8 | MLB55027309 | incerteza real: score 61; sinais insuficientes
- aprovado_auto | final=52.6 | integridade=30, preço=7, histórico=10, vendedor=0, categoria=0, publicação=5.6 | MLB64311324 | aprovado automaticamente: score 52.6; desconto real 27%, menor preço histórico
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB60837142 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB89126587023 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB96893788270 | sem meli.la válido
- rejeitado | final=40.7 | integridade=23, preço=7, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB61673959 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB61092987 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB100970278151 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB46021350 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB69793413447 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB20712717 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB48955757 | sem meli.la válido
- rejeitado | final=40.7 | integridade=23, preço=7, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB62061354 | sem meli.la válido
