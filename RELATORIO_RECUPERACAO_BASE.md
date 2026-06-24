# Relatório de Recuperação da Base - Promogg

- Data/hora: 2026-06-24 12:41:27
- Resultado: homologado localmente
- Modo: execução
- Backup: backups/reconstrucao_base/20260624_122600

## Proteções aplicadas
- A fila global de postagens não é executada durante a reconstrução.
- O monitoramento completo não é forçado durante a reconstrução.
- Falhas transitórias de API preservam o status anterior.
- O catálogo novo precisa respeitar mínimo, páginas, links e queda máxima.

## Base antes/depois
- Produtos: 875 -> 900
- Histórico de preços: 3544 -> 3588
- Novas ofertas coletadas: 25
- Itens atualizados: 19
- Linhas-base de histórico criadas: 0
- Fila global executada: não

## Catálogo
- Referência: 622 ofertas
- Candidato: 622 ofertas
- Páginas candidatas: 622
- Queda: 0.00%
- Bloqueios: nenhum

## Situação final
Base atualizada e catálogo local preservado/validado. Deploy permanece uma ação manual.
