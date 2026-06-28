# Relatório de Recuperação de Indisponíveis

- Gerado em: 2026-06-20 12:36:49
- Modo: execução real
- Backup: backups/operacao/promogg_backup_20260620_123647.zip
- Total indisponíveis: 815
- Recuperáveis com segurança: 619
- Mantidos por item_id inválido: 0
- Mantidos por 404/finalização: 0
- Mantidos sem evidência: 196
- Recuperados nesta execução: 619

## Causa raiz

- Falhas HTTP 403 são inconclusivas e não representam indisponibilidade. O monitoramento foi ajustado para registrar erro_api/verificacao_inconclusiva e preservar o status anterior.
- Registros antigos sem motivo confiável só são recuperados quando possuem postagem aprovada, link meli.la, preço e imagem.

## Exemplos
- recuperar_seguro | MLB85461139997 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB93955563541 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB110805634459 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB83332404511 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB45532516 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB12465919 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB83357220054 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB110630239438 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB112810074435 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB28859007 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB21862682 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB111256104870 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB51586079 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB61105291 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB105511107400 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB31768611 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB98393158897 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB111287768550 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB41975964 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
- recuperar_seguro | MLB34801962 | postagem aprovada com meli.la, preço e imagem; indisponibilidade sem motivo confirmado
