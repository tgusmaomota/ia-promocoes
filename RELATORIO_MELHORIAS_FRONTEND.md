# Relatório de melhorias front-end do Promogg

Gerado em: 2026-06-26

## Escopo

Auditoria e correções seguras no front-end estático do Promogg, preservando publicação, curadoria, histórico de preços, Telegram, deploy, banco e regras de segurança já homologadas.

## Backup

Antes das alterações foi criado backup dos principais arquivos afetados em:

- `backups/frontend_auditoria_20260626_161745/`

Arquivos preservados no backup:

- `gerar_site.py`
- `site/app.js`
- `dist_site/app.js`
- `site/index.html`
- `dist_site/index.html`
- `.env.example`

## Problemas encontrados

1. Categorias públicas excessivamente específicas, com marcas/modelos e subcategorias virando navegação principal.
2. JavaScript do catálogo com referência a variáveis inexistentes em cards (`badges`/`economiaBadge`), risco real de quebrar renderização.
3. Busca sem normalização de acentos, prejudicando pesquisa por termos como “tenis”/“tênis”.
4. Filtros sem botão de limpeza, sem contagem por categoria e sem persistência na URL.
5. Títulos longos ocupando espaço demais nos cards.
6. Histórico de preços com mensagem ambígua: “sem variação” podia aparecer mesmo quando preço atual estava acima do menor histórico.
7. Páginas de categoria usando classe visual antiga em cards.
8. Textos vindos já escapados do banco podiam ser escapados novamente, gerando `&amp;amp;quot` no HTML público.

## Melhorias implementadas

### HTML e acessibilidade

- Mantida geração com um único `<!DOCTYPE html>`, `<html>`, `<head>` e `<body>` por página.
- Adicionado botão “Limpar filtros” com semântica de botão real.
- Mantidos `aria-live`, skip link, labels e foco visível já existentes.
- Cards de categoria alinhados ao mesmo padrão estrutural dos cards da home.

### SEO técnico

- Preservados `title`, `description`, canonical, Open Graph, Twitter Cards, favicon, robots e sitemap.
- Mantidas páginas de produto e categoria indexáveis.
- Categorias públicas foram normalizadas para URLs mais estáveis e úteis.

### Escape de texto

- Títulos e categorias passam por `html.unescape()` antes da geração pública.
- O HTML continua escapando na saída, mas agora evita dupla codificação.
- Auditoria posterior encontrou `escape_duplo=0`.

### Títulos longos

- Títulos dos cards agora são truncados visualmente com `line-clamp`.
- O título completo é preservado no conteúdo/SEO e no `title` do elemento para tooltip.

### Categorias

- Criado sistema de normalização pública com 19 categorias principais:
  - Eletrônicos
  - Celulares
  - Informática
  - TVs
  - Áudio
  - Games
  - Casa
  - Móveis
  - Cozinha
  - Ferramentas
  - Automotivo
  - Moda
  - Esportes
  - Bebês
  - Saúde
  - Beleza
  - Jardim
  - Pets
  - Outros
- A normalização é aplicada somente na camada pública gerada, sem alterar banco, curadoria ou histórico.

### Filtros

- Busca instantânea preservada.
- Busca agora ignora acentos e diferenças de maiúsculas/minúsculas.
- Select de categorias mostra contador por categoria.
- Filtros são persistidos na URL (`q`, `categoria`, `desconto`, `historico`, `ordem`, `pagina`).
- Adicionado botão para limpar filtros.

### Cards

- Corrigida renderização de badges.
- Imagens continuam com lazy loading.
- Títulos têm altura visual padronizada.
- Cards de categorias usam as mesmas classes modernas da home.

### Histórico de preços

- Cards agora distinguem:
  - preço atual igual ao menor histórico;
  - preço atual acima do menor histórico;
  - novo menor preço registrado.
- A variação recente continua visível, mas não substitui a comparação com o menor histórico.

### Performance

- Lazy loading mantido para imagens.
- Filtros continuam client-side e rápidos.
- Categoria normalizada reduz explosão de páginas de categoria e melhora navegação.
- Persistência por URL evita estado extra em cookies/localStorage.

## Arquivos alterados

- `gerar_site.py`
- `site/app.js`
- `site/style.css`
- `site/index.html`
- `site/ofertas.json`
- páginas geradas em `site/produto/`
- páginas geradas em `site/categoria/`
- `dist_site/` sincronizado a partir de `site/` pela rotina protegida
- `RELATORIO_MELHORIAS_FRONTEND.md`

## Validações executadas

```bash
python3 -m py_compile gerar_site.py
python3 -m py_compile *.py
python3 ia_promocoes.py gerar-site
python3 ia_promocoes.py preparar-publicacao
python3 ia_promocoes.py validar --somente-leitura
python3 ia_promocoes.py auditar-qualidade-catalogo
```

Resultado:

- `site/`: 751 ofertas / 751 páginas de produto
- `dist_site/`: 751 ofertas / 751 páginas de produto
- Validação somente leitura: aprovada
- Auditoria de qualidade: `APROVADO COM RESSALVAS NÃO BLOQUEANTES`
- Links `meli.la`: 751
- Imagens válidas: 751
- Preços inválidos: 0
- Páginas quebradas: 0
- SEO sem título: 0
- SEO sem descrição: 0

Auditoria estrutural adicional:

- HTMLs auditados por pasta: 775
- Problemas estruturais de `doctype/head/body`: 0
- IDs duplicados: 0
- Escape duplo detectado: 0
- Categorias públicas finais: 19

## Problemas que permaneceram

- `preparar-publicacao` finalizou com código de bloqueio porque o Git possui alterações bloqueantes já existentes fora deste escopo.
- A auditoria de qualidade ainda informa ressalvas não bloqueantes herdadas da base, como `item_id_duplicado` deduplicado e dados de categoria interna vazia em parte dos registros.
- `node --check` não pôde ser executado porque Node.js não está disponível no ambiente atual.

## Recomendações futuras

1. Adicionar validação automatizada de JavaScript no pipeline quando Node.js estiver disponível.
2. Criar teste específico para impedir regressão de variáveis JS inexistentes.
3. Evoluir a normalização de categorias com telemetria de cliques/conversão.
4. Adicionar relatório visual Lighthouse/Web Vitals em ambiente local ou CI.
5. Reduzir ressalvas de categoria interna no banco sem afetar a categoria pública normalizada.

## Segurança

- Nenhum deploy foi executado.
- Nenhum Telegram real foi enviado.
- Nenhum fluxo `ONLINE` foi acionado.
- Banco, histórico, curadoria, tokens, `.env`, Playwright e publicação homologada foram preservados.
- `dist_site/` foi preparado pela rotina protegida, mas publicação permaneceu bloqueada por Git conforme esperado.
