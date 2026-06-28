# Relatório de Auditoria de Score

- Gerado em: 2026-06-20 07:50:06
- Pendentes auditadas: 462

## Fórmula atual

- Preço válido: +25.
- Faixa de preço R$30-R$500: +20; outros preços válidos: +10.
- `oferta_do_dia` ou `oferta_relampago`: +20.
- Desconto: +8 a +20 conforme a faixa de 15% a 50%.
- Palavras-chave (frete, promoção/oferta, kit/combo): +5 cada.
- Internacional: -20.
- Aprovação automática atual: score >= 65.

## Diagnóstico

- O campo `tipo_promocao` não está disponível nas postagens reprocessadas; por isso o bônus de +20 normalmente não é aplicado.
- Produtos acima de R$500 recebem só +10 pela faixa de preço, mesmo quando têm sinais de qualidade completos.
- O score atual não considera diretamente link `meli.la`, imagem, categoria real, disponibilidade, histórico, economia ou queda de preço.
- Após o saneamento, palavras promocionais removidas do título deixam de conceder pontos, o que é correto para a limpeza, mas reduz a pontuação dependente de texto.

## Distribuição do score atual

- 35: 13
- 40: 4
- 45: 1
- 50: 274
- 55: 129
- 58: 2
- 63: 37
- 70: 2
- sem ofertas

## Motivos de baixa pontuação
- revisão recomendada: 50 < 65; categoria real ausente: 274
- revisão recomendada: 55 < 65; categoria real ausente: 129
- revisão recomendada: 63 < 65; categoria real ausente: 37
- score insuficiente: 35 < 45; categoria real ausente: 13
- score insuficiente: 40 < 45; categoria real ausente: 4
- revisão recomendada: 58 < 65; categoria real ausente: 2
- aprovado para fila pendente; categoria real ausente: 2
- revisão recomendada: 45 < 65; categoria real ausente: 1
- sem dados

## Campos ou sinais ausentes
- nenhum

## Simulação sem alteração no banco
### A - regra atual
- Aprovadas automaticamente: 2
- Revisão manual: 460
- Rejeitadas: 0
- Exemplo aprovado_auto: score 70 | Fritadeira E Forno Elétrico Style Oven Fry Elgin 10l Preto
- Exemplo revisao_manual: score 55 | Smart Tv Samsung 32 Ls32h5000fgxzd Hd Led Wifi Hdmi 110/220v
### B - auto >= 70 / revisão >= 50
- Aprovadas automaticamente: 2
- Revisão manual: 443
- Rejeitadas: 17
- Exemplo aprovado_auto: score 75 | Fritadeira E Forno Elétrico Style Oven Fry Elgin 10l Preto
- Exemplo revisao_manual: score 60 | Smart Tv Samsung 32 Ls32h5000fgxzd Hd Led Wifi Hdmi 110/220v
- Exemplo rejeitado: score 40 | Smart Tv Samsung Led 55 Lh55befh4ggxzd Led Crystal Processor 4k Uhd Tizen 110v/220v
### C - auto >= 65 / revisão >= 45
- Aprovadas automaticamente: 39
- Revisão manual: 410
- Rejeitadas: 13
- Exemplo aprovado_auto: score 68 | Câmera Inteligente Im7 + 3mp De Resolução Branca Intelbras
- Exemplo revisao_manual: score 60 | Smart Tv Samsung 32 Ls32h5000fgxzd Hd Led Wifi Hdmi 110/220v
- Exemplo rejeitado: score 40 | Smart Tv Samsung Led 55 Lh55befh4ggxzd Led Crystal Processor 4k Uhd Tizen 110v/220v
### D - auto >= 60 / revisão >= 45
- Aprovadas automaticamente: 170
- Revisão manual: 279
- Rejeitadas: 13
- Exemplo aprovado_auto: score 60 | Smart Tv Samsung 32 Ls32h5000fgxzd Hd Led Wifi Hdmi 110/220v
- Exemplo revisao_manual: score 55 | Celular Samsung Galaxy A17 Com Ia, 128gb, 4gb Ram, Câm De 50mp, Tela De 6.7 , Nfc, Ip54 - Preto
- Exemplo rejeitado: score 40 | Smart Tv Samsung Led 55 Lh55befh4ggxzd Led Crystal Processor 4k Uhd Tizen 110v/220v

## Top 50 pendentes por score proposto

1. [MLB51436469] atual=70 proposto=75 | Fritadeira E Forno Elétrico Style Oven Fry Elgin 10l Preto | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
2. [MLB67509529] atual=70 proposto=75 | Kit Relógio Condor Masculino Dourado Co2115ncg/k4a Dourado Azul | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
3. [MLB47535705] atual=63 proposto=68 | Câmera Inteligente Im7 + 3mp De Resolução Branca Intelbras | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
4. [MLB17411744] atual=63 proposto=68 | Cadeira De Escritório Giratória Com Altura Ajustável Begônia Cor Preto | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
5. [MLB22335179] atual=63 proposto=68 | Lorenzetti Loren Shower ULTRA multitemperaturas chuveiro Branco | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
6. [MLB44212011] atual=63 proposto=68 | DeckCasa Escova elétrica de limpeza JY-6010 Branco Unidade 1 | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
7. [MLB18363110] atual=63 proposto=68 | Micro-ondas Electrolux 31L cor Inox Espelhado com Painel Integrado e Função Tira Odor MI41S | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
8. [MLB22647624] atual=63 proposto=68 | Purificador De Água Ibbl E-due Prata 79073001 | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
9. [MLB44898097] atual=63 proposto=68 | Micro-ondas 33l Philco Teclas Fáceis Limpa Fácil 1400w Pm36 127V | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
10. [MLB25708528] atual=63 proposto=68 | Shampoo Redutor de Grisalhos Grecin Control GX Para Todas os Tons Cabelo 118ml | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
11. [MLB37314383] atual=63 proposto=68 | Impressora Epson Multifuncional L3250 Wifi Econtank Color Cor Preto 110 240V (Bivolt) | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
12. [MLB51857000] atual=63 proposto=68 | Guarda-roupa Casal 3 Portas Preto com Espelho Milão Yescasa MDF | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
13. [MLB15388664] atual=63 proposto=68 | Batedeira Planetária, Mondial, 700W - BP-01P-B | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
14. [MLB21710812] atual=63 proposto=68 | Hd Externo 2tb Seagate Expansion Portátil 2000gb Usb 3.0 Cor Preto | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
15. [MLB58858507] atual=63 proposto=68 | Purificador de Água Gelada Fria e Natural Elétrico Compacto Eletrônico placa Filtro refil 6 meses ou 3000l Painel Touch Bivolt Preto PE12B Electrolux | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
16. [MLB47115842] atual=63 proposto=68 | Smartphone Samsung Galaxy A36 5G 128GB 6GB RAM Câmera Tripla de até 50MP Selfie de 12MP IP67 Super AMOLED 6.7&amp;quot&amp;quot NFC Recursos AI Android e Segurança Snapdragon - Branco | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
17. [MLB32978518] atual=63 proposto=68 | Lavadora Alta Pressão 1400w Lav 1600 Vonder 220v | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
18. [MLB14489716] atual=63 proposto=68 | Panificadora Multipane 12 Programações Com Função Timer e Antiaderente Potência de 550 W Cor Preto Britânia | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
19. [MLB29187736] atual=63 proposto=68 | Lavadora De Alta Pressão Vonder 1400w Lav 1600 Amarelo 127 V | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
20. [MLB54245381] atual=63 proposto=68 | Kit Kemei Máquina de Corte KM-2299 e Acabamento KM-1102 Bivolt | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
21. [MLB24254286] atual=63 proposto=68 | Depurador e Exaustor De Ar Suggar Slim DPS181PT 80cm Cor Preto | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
22. [MLB27918094] atual=63 proposto=68 | Kit 2 Pneus 175/65R14 Firestone F-600 82T Aro 14 | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
23. [MLB29089153] atual=63 proposto=68 | Ração Golden Special Gatos Adultos Frango E Carne 10,1 Kg | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
24. [MLB23414010] atual=63 proposto=68 | Aspirador De Pó Vertical E Portátil Wap High Speed Plus 1350w 1,2 Litros Filtro Hepa Tecnologia Cyclone 3 Em 1 | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
25. [MLB47875114] atual=63 proposto=68 | Escrivaninha Mesa Office Estudo Estilo Industrial Cor Preto 1,10m Klm Store | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
26. [MLB25120687] atual=63 proposto=68 | Ração Gran Plus Choice Gatos Adulto Frango E Carne 10,1kg | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
27. [MLB61060284] atual=63 proposto=68 | Mala de Bordo Rígida Aj Shops, em ABS, com Rodas 360°, para Viagem | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
28. [MLB56408764] atual=63 proposto=68 | Creme Clareador para Axilas Virilha 60g | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
29. [MLB55868679] atual=63 proposto=68 | Espelho 100x50 Orgânico Corpo Inteiro Grande Moldur Caramelo Preto | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
30. [MLB35504239] atual=63 proposto=68 | Monitor 19 Preto Led Bm19k4hvw Bluecase - 75hz / Hdmi / Vga | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
31. [MLB51979690] atual=63 proposto=68 | Banheira Bebê Dobrável Com Suporte Termômetro E Almofada Cor Rosa | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
32. [MLB57082682] atual=63 proposto=68 | Caixa de Som JBL Boombox 4 Bluetooth Portátil 210W Bivolt Azul | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
33. [MLB68929675] atual=63 proposto=68 | Aquecedor Elétrico Portátil A Ar Ventilador Quente Preto Aq04 - Mimo Style | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
34. [MLB44844303] atual=63 proposto=68 | Câmera Lâmpada Intelbras Im6 Full Color 3mp 360 Wifi Interna Cor Branco | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
35. [MLB36943302] atual=63 proposto=68 | Cuba Pia de Apoio Sobrepor Oval 43x25 Branca Banheiro Lavabo Beltempo BT-2030 | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
36. [MLB51979690] atual=63 proposto=68 | Banheira Bebê Dobrável Com Suporte Termômetro E Almofada Cor Rosa | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
37. [MLB48711918] atual=63 proposto=68 | Air fryer Fritadeira Elétrica sem oleo Rita Lobo 5,6L 9 receitas funções pré-definidas Painel Digital timer 60min desligamento automático cesto removivel antiaderente 1400W Electrolux EAF45 Cinza | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
38. [MLB26884984] atual=63 proposto=68 | Ducha Lorenzetti Acqua Duo Ultra Eletrônica 7.800w Preto Fosco Cor Único Potência 7800 W | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
39. [MLB24287062] atual=63 proposto=68 | Macaco Jacaré Hidráulico 2 Ton Com Maleta 3081 Bremen | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
40. [MLB55027309] atual=58 proposto=63 | Celular Samsung Galaxy A17 5g Com Ia, 128gb, 4gb Ram, Câm De 50mp, Tela De 6.7 , Nfc, Ip54 - Cinza | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
41. [MLB55027309] atual=58 proposto=63 | Celular Samsung Galaxy A17 5g Com Ia, 128gb, 4gb Ram, Câm De 50mp, Tela De 6.7 , Nfc, Ip54 - Cinza | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
42. [MLB66191173] atual=55 proposto=60 | Smart Tv Samsung 32 Ls32h5000fgxzd Hd Led Wifi Hdmi 110/220v | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
43. [MLB36688353] atual=55 proposto=60 | Fritadeira Elétrica Air Fryer Antiaderente WAP Oven 12 Litros com Painel Digital | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
44. [MLB67444410] atual=55 proposto=60 | Smartphone Motorola Edge 70 Fusion 5g Fifa World Cup Collection - 256gb 24gb (8gb Ram + 16gb Ram Boost), Camera 50mp Sony Lytia 710, Tela 1.5k Extreme Amoled - Grafite | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
45. [MLB18572379] atual=55 proposto=60 | Secador De Cabelos Style Azul Tiffany 2000w Taiff Azul | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
46. [MLB45702954] atual=55 proposto=60 | Impressora 3d Bambu Lab A1 Mini - A1M | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
47. [MLB67270079] atual=55 proposto=60 | Smart Tv Philco 40 P40vik Led Roku Dolby Audio Wi-fi Hdmi Hdr Full Hd 110/220v | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
48. [MLB24804661] atual=55 proposto=60 | Purificador de Água Gelada Fria e Natural Eletrônico Placa Compacto Electrolux PE12G com Filtro Carvão 6 meses ou 3000L Painel Touch Cinza | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
49. [MLB53610161] atual=55 proposto=60 | Smart TV LG UHD AI UA75 50 polegadas HDR10 Pro Processador α7 AI Ger8 webOS 25 | preço válido, link meli.la válido, imagem pública, título limpo, categoria real
50. [MLB62276296] atual=55 proposto=60 | Jogo De Panelas Induçao Antiaderente Cerâmica 10 Peças Ppg Pfoa Free Baunilha | preço válido, link meli.la válido, imagem pública, título limpo, categoria real

## Fórmula sugerida para avaliação futura

- Base de integridade: link meli.la +10, imagem +5, título limpo +5, preço válido +10, categoria real +5, disponibilidade +5.
- Valor da oferta: desconto +8 a +25, economia +5, menor preço histórico +15 ou queda +10.
- Produto novo não é penalizado por histórico ausente, mas não recebe bônus que substitua evidência real de preço.
- Aprovação automática proposta exige o score do cenário e evidência verificável: desconto >= 25% com economia, menor preço histórico ou queda real.
- Sugestão segura: começar pelo cenário B, revisar uma amostra das aprovadas simuladas e só então decidir por qualquer mudança.
- Esta auditoria não altera a regra de produção, status, links, histórico, Telegram nem o site.
