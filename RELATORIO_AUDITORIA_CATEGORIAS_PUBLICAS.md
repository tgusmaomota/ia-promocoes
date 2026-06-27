# Relatório de auditoria de categorias públicas

Data: 26/06/2026 20:26

Escopo: auditoria somente leitura das categorias públicas geradas para o site estático. Banco, histórico, curadoria e status internos não foram alterados.

## Regra aplicada

- classificação por múltiplos sinais: categoria de origem, caminho/breadcrumb e título;
- correspondência por palavra/frase normalizada, não substring solta;
- termos negativos por categoria;
- redirecionamentos explícitos para casos críticos;
- fallback seguro para `Outros` quando a evidência é insuficiente.

## Correção crítica em Bebês

A palavra `carrinho` isolada deixou de classificar produtos como Bebês. Agora Bebês exige contexto infantil, como `bebê`, `infantil`, `mamadeira`, `fralda infantil`, `berço`, `bebê conforto`, `carrinho de bebê` ou termos equivalentes.

## Eletrônicos

- Quantidade de ofertas: 50

### Exemplos corretos

- Projetor Magcubic L018 LED Full HD 1080p, com Android 14 e Wi-Fi 6
- Projetor 4k Ultra Hd Hy320 Smart Wi-fi 6 Bluetooth Android Cor Preto
- Kit 2 Câmera Segurança Ip Interna Externa Wifi iCSee Infravermelho Prova D’Água - HW
- Smartwatch Aurafit G12 Gps Amoled 1.43 Bluetooth Resistente Água 3atm Laranja-escuro Mesh Preto Verde Exército Preto
- Kit Relógio Condor Masculino Speed Prata - Co2117aw/k4v Prata Verde
- TP-Link Tapo C320WS Câmera de Segurança Wifi 2K QHD Colorida IP66

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Celulares

- Quantidade de ofertas: 32

### Exemplos corretos

- Celular Samsung Galaxy A07 256gb, 8gb, Câmera 50mp, Tela 6.7 , Proteção Ip54, Processador 6nm - Preto
- Celular Samsung Galaxy A17 5g Com Ia, 128gb, 4gb Ram, Câm De 50mp, Tela De 6.7 , Nfc, Ip54 - Cinza
- Smartphone Motorola Moto G67 5g - 256gb 12gb (4gb Ram + 8gb Ram Boost) Camera 50mp Sony Lytia 600, Tela 1.5k Extreme Amoled 120hz, Ultrarresistente - Chumbo
- Smartphone Motorola Moto G35 5G 128GB Grafite
- Samsung Galaxy A06 5g Dual Sim 128gb preto
- Smartphone Samsung Galaxy A36 5G 128GB 6GB RAM Câmera Tripla de até 50MP Selfie de 12MP IP67 Super AMOLED 6.7&quot&quot NFC Recursos AI Android e Segurança Snapdragon - Branco

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Informática

- Quantidade de ofertas: 76

### Exemplos corretos

- Monitor Portatil Touch Screen Gamer15.6 Full Hd 100% Rgb Ips
- Impressora Brother Inkbenefit DCP-T530DW cor preto
- Unidade de estado sólido Kingston M.2 NVMe PCIe 4.0 NV3 de 1 TB, azul escuro
- Impressora Epson Multifuncional L3250 Wifi Econtank Color Cor Preto 110 240V (Bivolt)
- NOTEBOOK ACER ASPIRE GO 15 I5-13420H, RAM 8GB, SSD 256GB, 15,6" FULL HD, LINUX – AG15-71P-54J6
- Notebook Lenovo Ideapad Slim 3 15irh10 Intel Core i5-13420h 8gb 512gb Ssd Linux 15.3 - 83nss00000 Luna Grey

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## TVs

- Quantidade de ofertas: 30

### Exemplos corretos

- Smart TV LG UHD AI UA75 50 polegadas HDR10 Pro Processador α7 AI Ger8 webOS 25
- Amazon Fire TV Stick 4K MAX 16GB Wi-Fi 6E Alexa Controle por Voz
- Smart TV Profissional 4K 50" LG UHD 50AU801 Processador α7 AI Ger8 Super Upscaling Google Cast Alexa Integrado Controle AI Smart Magic WebOS 25
- Smart Tv 43 Aoc Led Roku Full Hd Wi-fi 60hz Hdmi Usb 43s5155/78g
- Smart Tv Toshiba 43 Polegadas 43v35rs Full Hd
- Smart TV Weyon 32WDSNMX 32&quot&quot HD LED

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Áudio

- Quantidade de ofertas: 28

### Exemplos corretos

- Microfone Hollyland Lark M2 Duo Combo Duplo Para 2 Pessoas USB-C, Lightning e Camera preto
- Monitor LG LED Home & Office 20U401A-B Tela 20” HD+, LG Switch, Modo leitura e Flicker Safe, HDMI, VGA, 2ms (GtG), 75Hz, Black Stabilizer, Dynamic Action Sync, Crosshair, saída fone de ouvido
- Caixa De Som Jbl Boombox 4 Bluetooth Som 210w Jbl Pro Ai Sound Boost Graves Personalizáveis Bateria De Até 34h Ip68 Áudio Lossless Azul
- EMEET C960 4K Webcam 1080P 60Fps Camera Para PC Streaming Com Microfone Automático Kit Videoconferencia
- Caixa De Som Bluetooth Joog One Hifi Jof01 200w C/ Microfone Preto 127/220v
- Caixa De Som Amplificada Bluetooth 600w Rms Tcs400 Cor Preto The Black Tools Com Rádio Fm Usb Pendrive Led Rgb Bivolt

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Games

- Quantidade de ofertas: 12

### Exemplos corretos

- Console Playstation 5 Slim Edição Digital 825 Gb
- Console PlayStation® 5 Slim Edição Digital 825 GB Branco - Sony
- Nintendo Switch Lite 32gb Standard Azul
- Playstation 5 Slim Cor Branco 1 Tb Versão Mídia Física
- Controle DualSense Sem Fio PlayStation 5 Joystick Starlight Blue Sony CFI-ZCT1W
- Controle Microsoft Xbox Wireless Series X/s Velocity Green Cor Verde

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Casa

- Quantidade de ofertas: 110

### Exemplos corretos

- Lava louças portátil Praxis cor preto
- Aquecedor de Água Versátil Elétrico Pia Lavatório Lorenzetti 5500w 220v
- Ar Condicionado Split Hq Hw Inv 9k Frio Viht9kco3s2s13
- Ar-condicionado Split Samsung Inverter Windfree Ai 12.000 Btus Frio Sem Vento Ar12dyfaawknaz
- Extratora de Sujeira Portátil WAP Spot Cleaner W3 Borrifa Esfrega e Extrai 1450W de Potência e Bico de Autolimpeza
- Aquecedor de água elétrico Lorenzetti versátil 3 temperaturas cor branco 220V 5500W

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Móveis

- Quantidade de ofertas: 27

### Exemplos corretos

- Guarda-roupa Casal 3 Portas Preto com Espelho Milão Yescasa MDF
- Sofá Mobly Beny 180 de 3 cuerpos tela linho color cru
- Guarda Roupa Casal Branco Paris 8 Portas 4 Gavetas Espresso Móveis
- Cadeira Escritório Ergonômica Genebra B500 Luvinco Cor Preto Com Suporte Lombar Estofado Mesh
- Sofá Retrátil Reclinável 3,00m Nivus Cinza Molas Ensacadas - King House
- Sofá Retrátil/reclinável King House Verona 1,50m Velut Cinza C/ Molas

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Cozinha

- Quantidade de ofertas: 47

### Exemplos corretos

- Fritadeira Air Fryer Philco PAF16A 4 Em 1 Painel Digital 16l
- Fritadeira Airfryer Digital Série 2000 Xl Na239 Preto
- Nescafé Dolce Gusto Arno Genio S Basic Branca Dgs1 Cor Branco
- Cooktop De Indução 1 Boca Preto Com Trava De Segurança Painel Touch Screen
- Fritadeira Airfryer Digital Série 2000 Xl Na239/00 Preto 127v
- Kit C/12 Utensílios De Cozinha Silicone Cabo Madeira

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Ferramentas

- Quantidade de ofertas: 62

### Exemplos corretos

- Máquina De Solda Inversora Mig 130a Sem Gás 220v Im130a Black Mig Cor Preto/amarelo Frequência 50hz/60hz The Black Tools
- Furadeira Parafusadeira Sem Fio A Bateria Tb-12e 12v 3/8 10mm Com Maleta E Acessórios The Black Tools
- Parafusadeira Furadeira C/ 2 Baterias Maleta Kit Completo Led Eixo Flexível Vários Níveis Torque Simake
- Furadeira De Impacto Bosch 450w 10mm Gsb 450 Re Com Jogo De Brocas Bits 300 Peças Azul 127v 50/60hz
- Profissional Martelete Rompedor Furadeira 1300w Sds Plus
- Máquina Inversora Solda Portatil C/acessórios Dobevi Branco/preto 127/220v

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Automotivo

- Quantidade de ofertas: 25

### Exemplos corretos

- Carrinho Tipo Esteira Para Mecânico Profissional Com Encosto BTE2000 The Black Tools
- Som rádio automotivo bluetooth usb card sd aux fm mp3 H-tech
- Compressor De Ar Elétrico Portátil 120w Encher Pneu Carro Moto Bicicleta Tcm100 The Black Tools
- Pneu 185/65R15 Continental PowerContact 2 88H Aro 15
- Capa De Chuva Moto Com Capuz Impermeável Motoqueiro
- Auxiliar De Partida De Bateria Veicular Portátil Com Compressor De Ar Para Carro E Moto

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Moda

- Quantidade de ofertas: 38

### Exemplos corretos

- Short Saia Jeans Feminino Cintura Alta Com Lycra Stillger
- Tênis Esportivo Masculino Delta Olympikus Liso
- Tênis Masculino Feminino Kappa Park 2.0 Original
- Kit 10 Cuecas Boxer Box Masculina Algodão Atacado Polo Fit
- Bota Pegada Feminina Confortável Couro Original 282014
- Short Duplo 2 Em 1 Fitness Bermuda Cintura Alta Feminino

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Esportes

- Quantidade de ofertas: 50

### Exemplos corretos

- Creatina Monohidratada Pura 120 cápsulas Dark Lab
- Bicicleta Spinning Com Roda De Inércia De 13kg Wct Fitness Cor Preto
- Creatina 1kg Suplemento Monohidratada em pó 100% Pura - Soldiers Nutrition
- Creatina Monohidratada 250g Growth Supplements - Sem sabor em Pó
- Creatina Monohidratada Pura 1kg Dark Lab Unidade Sem sabor
- Whey Isolate Protein Fuse Refil 900g - Dark Lab Sabor Creme De Avelã

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Bebês

- Quantidade de ofertas: 4

### Exemplos corretos

- Baba Eletronica Visão Noturna Vb603 Video Voz Camera S/ Fio Cor Branco 127/220V
- Carrinho Kansas Gold Premium Baby C/ Bebê Conforto E Base Cor Preto
- Bomba De Tirar Leite Materno Portátil Eletrica 24mm Sem BPA Não Precisa Segurar Ou Ficar Apertando Mãos Livres Amamentação Extratora Elétrica Sugador Bombinha Marca Fergusom
- Carrinho de Bebê Passeio Bambinelli Fox Reclinável Preto 2023

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Saúde

- Quantidade de ofertas: 18

### Exemplos corretos

- Kit Desintoxique Da Alwaysfit Pro3magnésio + Nac E Fits36 Sem Sabor
- Waterpulse Flosser Irrigador Oral Dental WP62- Elétrico Bocal Jato Limpador De Língua Água Dentes Boca Gengiva Mangueira 10 Modos Pressão Potente Silencioso 145 PSI 600ml 8 Bicos
- Seringa Insulina Medix 1ml Ag. Fixa 12,7x0,33mm 29g 100 Un.
- Pro3Magnésio da Always Fit L-Treonina, Quelato e Dimalato - 60 Cápsulas
- Inalador Nebulizador Portátil Sem Fio Usb Pilha Silencioso Aparelho Inalação Compacto Bivolt Nebulizador
- Umidificador Ultrassônico G-tech Allergy Free Hm Bivolt Branco

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Beleza

- Quantidade de ofertas: 31

### Exemplos corretos

- Prancha Lizze Chapinha Profissional 480 Extreme
- Kit Body Splash Masculino Barbarius + Enigma + Midtown 200ml
- Escova Alisadora Gd039 Gokoco Ptc 3 Million Negative Ions
- Perfume Patriota 1a Dama 100ml - Eau De Parfum
- Ferofire 100ml Perfume Masculino Sedutor
- Chapinha De Cabelo Mq Professional Titanium Pro 480 Cor Chumbo

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Jardim

- Quantidade de ofertas: 2

### Exemplos corretos

- Varal De Luzes 40m Externo Com Lâmpadas Gambiarra Cordão
- Perfurador Solo Trado Gasolina com 3 Brocas Extensão 1,20m Carbon Fak Laranja

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Pets

- Quantidade de ofertas: 9

### Exemplos corretos

- Cama Para Pet Porte Grande Gigante Fundo Impermeável Lavável
- Ração GranNature Super Premium para Filhote de Porte Médio e Grande com 32% Proteína e Whey Protein Sabor Frango 15 kg
- Ração Quatree Life Para Gatos Castrados Salmão E Arroz 10,1 kg
- Ração Gran Plus Choice Gatos Adulto Frango E Carne 10,1kg
- Ração Golden Special Gatos Adultos Frango E Carne 10,1 Kg
- Ração Seca Quatree Supreme Gatos Adultos Castrados Salmão Batata 10kg

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.

## Outros

- Quantidade de ofertas: 100

### Exemplos corretos

- Fechadura Digital Biometria Eletronica Wifi Tuya Vie Idéale Preto
- Kit 4 Refil Tintas Corante EPS T544 Amarelo Ciano Magenta Preto Epson L3110 L3250
- Multigroom Philips Mg3921/15 inclui 12 acessórios
- Vaso Sanitário Monobloco Caixa Acoplada Completo - Privada Cor Branco - VAB0002
- Bomba Centrífuga Eurobombas EB2000M 2CV 220V Monofásica 36m 8100 L/h
- Refletor Led 200w Avant Slim 200 Branco Frio 6500k

### Exemplos suspeitos

- Nenhum alerta óbvio encontrado.

### Motivo do erro/regra aplicada

- Aplicadas regras positivas, negativas e redirecionamentos por categoria; itens ambíguos permanecem ou caem em `Outros` em vez de forçar categoria errada.
