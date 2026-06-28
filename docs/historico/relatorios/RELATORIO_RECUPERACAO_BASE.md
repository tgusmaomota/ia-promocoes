# Relatório de Recuperação da Base - Promogg

- Data/hora: 2026-06-26 08:14:56
- Resultado: homologado localmente
- Modo: execução
- Backup: backups/reconstrucao_base/20260626_074013

## Proteções aplicadas
- A fila global de postagens não é executada durante a reconstrução.
- O monitoramento completo não é forçado durante a reconstrução.
- Falhas transitórias de API preservam o status anterior.
- O catálogo novo precisa respeitar mínimo, páginas, links e queda máxima.

## Base antes/depois
- Produtos: 984 -> 1023
- Histórico de preços: 6129 -> 6192
- Novas ofertas coletadas: 39
- Itens atualizados: 24
- Linhas-base de histórico criadas: 0
- Fila global executada: não

## Catálogo
- Referência: 632 ofertas
- Candidato: 632 ofertas
- Páginas candidatas: 632
- Queda: 0.00%
- Bloqueios: nenhum

## Situação final
Base atualizada e catálogo local preservado/validado. Deploy permanece uma ação manual.
