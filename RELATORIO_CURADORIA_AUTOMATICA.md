# Relatório de Curadoria Automática

- Gerado em: 2026-06-26 11:59:25
- Modo: dry-run
- Backup: não aplicável
- Pendentes antes: 1
- Pendentes depois: 1
- Pendentes estimados após aplicar: 1
- Total analisado: 48
- Aprovados automaticamente: 1
- Rejeitados automaticamente: 46
- Mantidos pendentes: 1

## Regras usadas
- Rejeição automática para item_id inválido, ausência de `meli.la`, preço inválido, imagem inválida, título sujo/vazio, permalink inválido ou indisponibilidade confirmada.
- Aprovação automática exige requisitos mínimos íntegros, score >= 45, pelo menos 2 sinais positivos de preço e pelo menos 2 sinais positivos totais.
- Pendência fica restrita a conflito/incerteza: histórico fraco, categoria duvidosa ou sinais comerciais insuficientes sem erro crítico.
- Pesos: integridade=30, preco=30, historico=15, comercial=15, confiabilidade=10.

## Distribuição de score
- Menor: 36.4
- Médio: 43.3
- Maior: 61

## Motivos principais
- sem meli.la válido: 46
- incerteza real: score 61; sinais insuficientes: 1
- aprovado automaticamente: score 52.6; desconto real 27%, menor preço histórico: 1

## Exemplos aprovados
- #novo MLB64311324 | score=52.6 | Monitor LG Ultragear 27g411a-b 27 ,fhd, 144hz, 1ms (mbr), Nvidia G-sync, Amd Freesync, Hdr10 Preto 127/220v | aprovado automaticamente: score 52.6; desconto real 27%, menor preço histórico

## Exemplos rejeitados
- #novo MLB110450509600 | score=45 | Kit 10 Cuecas Boxer Box Masculina Algodão Atacado Polo Fit | sem meli.la válido
- #novo MLB110309278792 | score=48.6 | Daily T-shirt Insider | sem meli.la válido
- #novo MLB107423882380 | score=45.6 | Kit 3 Shorts 2 Em 1 Duplo Bolso Para Academia Treino Corrida | sem meli.la válido
- #novo MLB108664426620 | score=45.6 | Kit 4 Shorts 2 Em 1 Duplo Dryfit Masculino Compressão Térmic | sem meli.la válido
- #novo MLB111980096054 | score=40.6 | Capa De Chuva Roupa Conjunto Para Motoqueiro Reforçada Kit | sem meli.la válido
- #novo MLB112255156838 | score=45.6 | Bota Pegada Feminina Confortável Couro Original 282014 | sem meli.la válido
- #novo MLB109984301767 | score=47.9 | Torneira Bancada De Banheiro Luxo Inox Bica Baixa Lavatório | sem meli.la válido
- #novo MLB89577951557 | score=47.2 | Profissional Martelete Rompedor Furadeira 1300w Sds Plus | sem meli.la válido

## Exemplos pendentes
- #446 MLB55027309 | score=61 | Celular Samsung Galaxy A17 5g Com Ia, 128gb, 4gb Ram, Câm De 50mp, Tela De 6.7 , Nfc, Ip54 - Cinza | incerteza real: score 61; sinais insuficientes

## Segurança
- Histórico de preços não foi apagado.
- Telegram, deploy, ONLINE e geração de site não são chamados por este comando.
- O dry-run é somente leitura; a execução real cria backup antes de aplicar decisões.
