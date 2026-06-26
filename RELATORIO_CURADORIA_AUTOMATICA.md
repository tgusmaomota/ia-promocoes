# Relatório de Curadoria Automática

- Gerado em: 2026-06-26 16:43:16
- Modo: dry-run
- Backup: não aplicável
- Pendentes antes: 1
- Pendentes depois: 1
- Pendentes estimados após aplicar: 1
- Total analisado: 13
- Aprovados automaticamente: 1
- Rejeitados automaticamente: 11
- Mantidos pendentes: 1

## Regras usadas
- Rejeição automática para item_id inválido, ausência de `meli.la`, preço inválido, imagem inválida, título sujo/vazio, permalink inválido ou indisponibilidade confirmada.
- Aprovação automática exige requisitos mínimos íntegros, score >= 45, pelo menos 2 sinais positivos de preço e pelo menos 2 sinais positivos totais.
- Pendência fica restrita a conflito/incerteza: histórico fraco, categoria duvidosa ou sinais comerciais insuficientes sem erro crítico.
- Pesos: integridade=30, preco=30, historico=15, comercial=15, confiabilidade=10.

## Distribuição de score
- Menor: 40.7
- Médio: 45.3
- Maior: 61

## Motivos principais
- sem meli.la válido: 11
- incerteza real: score 61; sinais insuficientes: 1
- aprovado automaticamente: score 52.6; desconto real 27%, menor preço histórico: 1

## Exemplos aprovados
- #novo MLB64311324 | score=52.6 | Monitor LG Ultragear 27g411a-b 27 ,fhd, 144hz, 1ms (mbr), Nvidia G-sync, Amd Freesync, Hdr10 Preto 127/220v | aprovado automaticamente: score 52.6; desconto real 27%, menor preço histórico

## Exemplos rejeitados
- #novo MLB60837142 | score=43.7 | Kit Vibrador Concreto 1500w Com Mangote Mangueira 1,45mx35mm Com Acessorios Tvc650 The Black Tools 220v | sem meli.la válido
- #novo MLB89126587023 | score=43.7 | Autoclave 5 Litros B5 Bless Manicure Podologia Estética | sem meli.la válido
- #novo MLB96893788270 | score=43.7 | Toalha De Banho Feminina Microfibra Macia E Secagem Rápida | sem meli.la válido
- #novo MLB61673959 | score=40.7 | Barraca Auto-armável Pop Up Forestdog 4 Pessoas Impermeável 1000mm Verde-escuro-2 | sem meli.la válido
- #novo MLB61092987 | score=43.7 | Hub Usb C 7 Portas Em 1 Anker Adaptador Multiporta Para Notebook, Hdmi 4k@60hz, Até 85w, 3 Portas Usb-a E Usb-c 3.0,... Prateado | sem meli.la válido
- #novo MLB100970278151 | score=43.7 | Kit 6 Pares Meias Soquete Cano Curto Algodão Oferta Polo Fit | sem meli.la válido
- #novo MLB46021350 | score=43.7 | Furadeira Parafusadeira De Impacto 21v Com 2 Baterias Velocidade Ajustável 3/8 10mm Maleta E Acessorios Profissional The Black Tools Amarelo E Preto 127/220v 60hz | sem meli.la válido
- #novo MLB69793413447 | score=43.7 | Bicicleta Aro 29 Mtb Ksw 21v Shimano Com Freios Hidráulico | sem meli.la válido

## Exemplos pendentes
- #446 MLB55027309 | score=61 | Celular Samsung Galaxy A17 5g Com Ia, 128gb, 4gb Ram, Câm De 50mp, Tela De 6.7 , Nfc, Ip54 - Cinza | incerteza real: score 61; sinais insuficientes

## Segurança
- Histórico de preços não foi apagado.
- Telegram, deploy, ONLINE e geração de site não são chamados por este comando.
- O dry-run é somente leitura; a execução real cria backup antes de aplicar decisões.
