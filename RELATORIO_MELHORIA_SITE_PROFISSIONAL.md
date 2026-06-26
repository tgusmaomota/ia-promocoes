# Relatório de Melhoria Profissional do Site Promogg

- Data: 2026-06-26
- Escopo: UX, conversão, confiança, performance, SEO e assistente público seguro.
- Restrições respeitadas: sem deploy real, sem Telegram real, sem `supervisor-loop`, sem `ONLINE`, sem `ciclo-automatico --publicar`, sem alteração destrutiva no banco e sem remoção de histórico.

## Melhorias visuais implementadas

- Hero principal reposicionado para valor/conversão: histórico, link seguro e decisão com contexto.
- Métricas públicas no hero:
  - total de ofertas;
  - ofertas no menor preço;
  - selo de links `meli.la`.
- Trilhos automáticos baseados no catálogo:
  - Maiores descontos;
  - Menor preço histórico;
  - Recém verificadas.
- Cards mais profissionais:
  - badges “Link seguro meli.la”;
  - desconto;
  - menor preço/preço caiu;
  - economia estimada;
  - CTA “Ver oferta no Mercado Livre”.
- Botão fixo de voltar ao topo.
- Responsividade reforçada para mobile/tablet/desktop.

## Melhorias de UX

- Busca instantânea mantida e ampliada para título/categoria.
- Novos filtros:
  - categoria;
  - desconto mínimo;
  - histórico: “no menor preço” e “preço caiu”.
- Novas ordenações:
  - mais recentes;
  - maior desconto;
  - maior economia;
  - menor preço;
  - maior preço;
  - menor preço histórico.
- Paginação continua rolando para o topo da seção de ofertas.
- Estados vazios preservados com mensagem clara.

## Páginas individuais de produto

- CTA principal reforçado.
- Bloco “Análise Promogg” com explicação baseada apenas em:
  - preço atual;
  - variação pública;
  - desconto público;
  - economia pública;
  - menor preço histórico.
- Produtos relacionados por categoria pública.
- Histórico de preços preservado e sanitizado.
- Schema.org Product preservado.

## Assistente IA/Ollama e camada pública segura

- Assistente Promogg adicionado à home.
- Respostas são locais e estáticas, baseadas no catálogo público carregado em `ofertas.json`.
- A página `/assistente/` continua usando `assistente_dados.json` sanitizado.
- Nenhum endpoint local, privado ou `localhost` é chamado no frontend público.
- Nenhum token, log, banco, score interno ou motivo de curadoria é exposto.
- Ollama permanece como camada local/opcional fora do GitHub Pages público.

## SEO e performance

- Meta description e Open Graph da home melhorados.
- Twitter Card mantido.
- Canonical preservado.
- Sitemap/robots preservados.
- Imagens continuam com `loading="lazy"`.
- JS sem bibliotecas pesadas.
- Renderização paginada em 20 ofertas por página.
- Trilhos renderizam apenas pequenas listas de destaques.

## Segurança

- `auditar-seguranca-publicacao` executado com status `ok`.
- `site/` e `dist_site/` verificados sem `localhost` no HTML/JS principal.
- Frontend público não chama endpoint privado.
- Analytics público continua sem cookies, IP explícito, user-agent completo, email ou identificador pessoal.

## Arquivos alterados principais

- `gerar_site.py`
- `site/`
- `dist_site/`
- Relatórios operacionais atualizados pelas validações

## Validações executadas

- `python3 -m py_compile *.py`
- `python3 ia_promocoes.py gerar-site`
- `python3 ia_promocoes.py preparar-publicacao`
- `python3 ia_promocoes.py validar --somente-leitura`
- `python3 ia_promocoes.py auditar-qualidade-catalogo`
- `python3 ia_promocoes.py auditar-seguranca-publicacao`
- `python3 ia_promocoes.py preparar-publicacao --dry-run`
- `python3 ia_promocoes.py supervisor --dry-run`
- `git status --short`

## Resultados

- Site gerado: 751 ofertas.
- Páginas individuais: 751.
- `site/`: 751 ofertas / 751 páginas.
- `dist_site/`: 751 ofertas / 751 páginas.
- Validação somente leitura: aprovada.
- Qualidade: APROVADO COM RESSALVAS NÃO BLOQUEANTES.
- Segurança de publicação: ok, 0 críticos, 0 bloqueantes, 0 alertas.

## Limitações atuais

- O supervisor dry-run está bloqueando no momento porque a auditoria atual do Mercado Livre retornou `/users/me: falhou` e `Item: falhou`. Isso é uma trava operacional correta, não um problema do frontend.
- Git possui muitas alterações porque o site e `dist_site` foram regenerados. A publicação real segue bloqueada até revisão/commit das mudanças.

## Decisão

- Seguro para commit: sim, após revisar o volume de artefatos gerados em `site/` e `dist_site/`.
- Seguro para deploy: ainda não, porque Git está com alterações pendentes e o supervisor está bloqueando por falha atual de ML/OAuth/item.
- Seguro do ponto de vista de frontend/segurança: sim.
