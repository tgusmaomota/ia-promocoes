# Relatório UX Promogg — Home simplificada

Data: 2026-06-26

## Escopo

Ajuste fino de UX/UI da home pública do Promogg para remover seções com aparência artificial e deixar a página mais direta, compacta e parecida com uma vitrine profissional de ofertas.

A intervenção ficou limitada ao front gerado por `gerar_site.py`, aos artefatos estáticos em `site/` e `dist_site/`, e a este relatório. Não houve alteração de banco, histórico, curadoria operacional, Telegram, deploy, tokens ou credenciais.

## Decisão de produto

A home foi simplificada. A versão anterior tentava criar múltiplas vitrines, mas isso gerava sensação de protótipo e deixava espaços visuais vagos.

Nova estrutura:

1. Header
2. Hero compacto
3. Ofertas imperdíveis de hoje
4. Catálogo de ofertas com busca e filtros
5. Assistente, transparência e confiança
6. Rodapé

## Seções removidas

Foram removidas da home:

- Explore por categoria;
- Descubra mais;
- blocos por categoria na home;
- Melhor custo-benefício;
- Menor preço histórico como trilho de vitrine;
- Produtos populares;
- Recém-descobertas.

Também foram removidos CSS e JavaScript específicos dessas seções para evitar código visual morto na home.

## Motivo da remoção

- As seções intermediárias criavam distância demais entre a vitrine principal e o catálogo.
- Os blocos por categoria pareciam artificiais na home.
- A seção “Descubra mais” parecia uma anotação de produto, não uma área de marketplace.
- A página ficava conceitual demais e direta de menos.

A nova abordagem prioriza: menos seções, mais ofertas reais e fluxo mais claro.

## Vitrine única

A seção “Ofertas imperdíveis de hoje” agora é a única vitrine antes do catálogo.

Ela mostra 10 produtos reais em cards uniformes:

- 4 colunas no desktop;
- 2 colunas em telas intermediárias;
- carrossel horizontal no mobile.

Não há mais card destaque gigante. Isso reduz buracos visuais e mantém a grade equilibrada.

## Seleção automática

A seleção não usa os primeiros registros do JSON. A vitrine considera:

- desconto;
- economia estimada;
- menor preço/histórico;
- queda recente;
- sinais de popularidade;
- loja oficial, quando disponível;
- preço válido;
- imagem válida;
- link público válido;
- página individual existente.

Também há diversidade para evitar:

- produtos muito parecidos;
- concentração excessiva em uma única categoria;
- ranking puro por desconto.

## Classificação pública de categorias

Após homologação visual, foi identificado um problema grave de confiança: produtos como carrinho de mão, purificador de água e carrinho mecânico apareciam em `Bebês`.

A causa principal era a classificação por termo solto e substring. Exemplo: `carrinho` classificava como Bebês sem exigir contexto infantil.

Correções aplicadas:

- Bebês agora exige contexto claro: bebê, infantil, mamadeira, fralda infantil, berço, bebê conforto, carrinho de bebê, bomba de tirar leite ou equivalentes.
- Termos negativos impedem Bebês em casos como carrinho de mão, carrinho mecânico, purificador, filtro de água, ferramentas, obra e produtos adultos.
- O matcher deixou de usar substring solta e passou a usar palavra/frase normalizada.
- Redirecionamentos explícitos foram criados para categorias críticas:
  - carrinho de mão → Ferramentas;
  - carrinho mecânico → Automotivo;
  - purificador/filtro de água → Casa;
  - Smart TV/Roku/Fire TV → TVs;
  - notebook/Galaxy Book/SSD → Informática;
  - ração → Pets;
  - perfume → Beleza;
  - whey/creatina → Esportes.
- Produtos ambíguos ficam em `Outros` em vez de serem forçados para uma categoria errada.

Relatório específico criado:

- `RELATORIO_AUDITORIA_CATEGORIAS_PUBLICAS.md`

Resultado em `Bebês` após a correção:

- 4 ofertas;
- nenhum carrinho de mão;
- nenhum purificador/filtro de água;
- nenhum carrinho mecânico;
- itens restantes com contexto real de bebê/infantil.

## Textos públicos

Hero:

```text
Ofertas do Mercado Livre com histórico de preços.
```

Subtítulo:

```text
Compare descontos, veja quedas reais e compre com mais confiança.
```

Vitrine:

```text
Ofertas imperdíveis de hoje
```

Subtítulo:

```text
Selecionamos oportunidades com bom desconto, economia e histórico de preço.
```

Catálogo:

```text
Catálogo de ofertas
```

Subtítulo:

```text
Use a busca e os filtros para encontrar outras oportunidades.
```

Foram removidas da interface pública expressões como “vitrines”, “trilhos”, “sensação de descoberta”, “critérios diferentes” e textos com aparência de anotação interna.

## Arquivos alterados

- `gerar_site.py`
- `site/index.html`
- `site/style.css`
- `site/app.js`
- `dist_site/index.html`
- `dist_site/style.css`
- `dist_site/app.js`
- `RELATORIO_UX_PROMOGG.md`
- `RELATORIO_AUDITORIA_CATEGORIAS_PUBLICAS.md`

Relatórios operacionais também podem ter sido atualizados pelas validações:

- `RELATORIO_HOMOLOGACAO_PUBLICACAO_AUTOMATICA.md`
- `RELATORIO_QUALIDADE_CATALOGO.md`

## Validações

Executadas:

```bash
python3 -m py_compile gerar_site.py
python3 ia_promocoes.py gerar-site
python3 ia_promocoes.py validar --somente-leitura
python3 ia_promocoes.py auditar-qualidade-catalogo
python3 ia_promocoes.py preparar-publicacao
```

Resultado esperado após esta revisão:

- home sem “Explore por categoria”;
- home sem “Descubra mais”;
- home sem trilhos de custo-benefício, histórico, populares ou recém-descobertas;
- 10 cards uniformes em “Ofertas imperdíveis de hoje”;
- catálogo exibido imediatamente após a vitrine;
- `site/` e `dist_site/` sincronizados.

## Pendências visuais

- Homologar em navegador real no desktop.
- Homologar em celular físico.
- Avaliar se 10 cards é a quantidade ideal ou se a vitrine deve cair para 8 em telas menores.
- Avaliar se a seção do assistente deve permanecer na home ou migrar para uma página separada no futuro.

## Segurança

Não foram executados:

- deploy;
- push;
- Telegram real;
- ONLINE;
- supervisor-loop;
- publicação automática.

## Conclusão

A home foi simplificada para parecer uma vitrine confiável e direta de ofertas. A experiência agora reduz ruído, remove blocos artificiais e leva o usuário da proposta de valor para ofertas reais e, em seguida, para o catálogo completo.
