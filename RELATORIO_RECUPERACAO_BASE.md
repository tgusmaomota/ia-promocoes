# Relatório de Recuperação da Base - Promogg

- Data/hora: 2026-06-19 22:04:52
- Resultado: meta não atingida

## Causa raiz
Base ativa reduzida por itens indisponíveis e coleta Playwright bloqueada.

## Correções aplicadas
- Produtos indisponíveis foram preservados no SQLite e continuam excluídos do catálogo ativo.
- Coleta manual usa API/item_id quando disponível e Playwright com perfil reserva como fallback.

## Base antes/depois
- Produtos: 92 -> 119
- Ativos: 22 -> 2
- Indisponíveis preservados no histórico: 70 -> 117
- Novas ofertas coletadas: 27
- Ofertas recuperadas/atualizadas: 40
- Indisponíveis removidos do catálogo ativo: 70
- Ofertas públicas: 2
- Páginas de produto: 2
- Meta mínima (30/30): não atingida

## Situação final
Coleta concluída, mas a meta mínima de 30 ofertas/páginas não foi atingida.
