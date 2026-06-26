# Relatório de Score Adaptativo

- Gerado em: 2026-06-26 11:59:25
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
- rejeitado | final=45 | integridade=23, preço=7, histórico=10, vendedor=0, categoria=0, publicação=4.958 | MLB110450509600 | sem meli.la válido
- rejeitado | final=48.6 | integridade=23, preço=10, histórico=10, vendedor=0, categoria=0, publicação=5.6 | MLB110309278792 | sem meli.la válido
- aprovado_auto | final=52.6 | integridade=30, preço=7, histórico=10, vendedor=0, categoria=0, publicação=5.6 | MLB64311324 | aprovado automaticamente: score 52.6; desconto real 27%, menor preço histórico
- rejeitado | final=45.6 | integridade=23, preço=7, histórico=10, vendedor=0, categoria=0, publicação=5.6 | MLB107423882380 | sem meli.la válido
- rejeitado | final=45.6 | integridade=23, preço=7, histórico=10, vendedor=0, categoria=0, publicação=5.6 | MLB108664426620 | sem meli.la válido
- rejeitado | final=40.6 | integridade=23, preço=10, histórico=2, vendedor=0, categoria=0, publicação=5.6 | MLB111980096054 | sem meli.la válido
- rejeitado | final=45.6 | integridade=23, preço=7, histórico=10, vendedor=0, categoria=0, publicação=5.6 | MLB112255156838 | sem meli.la válido
- rejeitado | final=47.9 | integridade=23, preço=10, histórico=10, vendedor=0, categoria=0, publicação=4.88 | MLB109984301767 | sem meli.la válido
- rejeitado | final=47.2 | integridade=23, preço=10, histórico=10, vendedor=0, categoria=0, publicação=4.16 | MLB89577951557 | sem meli.la válido
- rejeitado | final=46.4 | integridade=23, preço=10, histórico=10, vendedor=0, categoria=0, publicação=3.44 | MLB112262976279 | sem meli.la válido
- rejeitado | final=47.2 | integridade=23, preço=10, histórico=10, vendedor=0, categoria=0, publicação=4.16 | MLB94666747899 | sem meli.la válido
- rejeitado | final=37.2 | integridade=23, preço=0, histórico=10, vendedor=0, categoria=0, publicação=4.16 | MLB110279250919 | sem meli.la válido
- rejeitado | final=40.7 | integridade=23, preço=7, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB111511186345 | sem meli.la válido
- rejeitado | final=46.4 | integridade=23, preço=10, histórico=10, vendedor=0, categoria=0, publicação=3.44 | MLB86042333083 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB111832138337 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB109355770469 | sem meli.la válido
- rejeitado | final=44.2 | integridade=23, preço=7, histórico=10, vendedor=0, categoria=0, publicação=4.16 | MLB111290422903 | sem meli.la válido
- rejeitado | final=47.2 | integridade=23, preço=10, histórico=10, vendedor=0, categoria=0, publicação=4.16 | MLB89082574569 | sem meli.la válido
- rejeitado | final=46.4 | integridade=23, preço=10, histórico=10, vendedor=0, categoria=0, publicação=3.44 | MLB108256614970 | sem meli.la válido
- rejeitado | final=39.2 | integridade=23, preço=10, histórico=2, vendedor=0, categoria=0, publicação=4.16 | MLB112597015639 | sem meli.la válido
- rejeitado | final=39.4 | integridade=23, preço=3, histórico=10, vendedor=0, categoria=0, publicação=3.44 | MLB111905641910 | sem meli.la válido
- rejeitado | final=36.7 | integridade=23, preço=3, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB110987031417 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB60837142 | sem meli.la válido
- rejeitado | final=36.4 | integridade=23, preço=0, histórico=10, vendedor=0, categoria=0, publicação=3.44 | MLB69217610082 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB108437862583 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB89126587023 | sem meli.la válido
- rejeitado | final=40.7 | integridade=23, preço=7, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB111965758938 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB50118079 | sem meli.la válido
- rejeitado | final=43.7 | integridade=23, preço=10, histórico=8, vendedor=0, categoria=0, publicação=2.72 | MLB96893788270 | sem meli.la válido
