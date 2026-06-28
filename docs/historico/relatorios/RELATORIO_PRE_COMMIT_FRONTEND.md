# Relatório pré-commit front-end Promogg

Data: 2026-06-26

## Resumo executivo

O front-end regenerado está validado, mas o repositório **não está limpo** e há mudanças de múltiplos escopos misturadas, inclusive mudanças já staged de rodadas anteriores.

Recomendação objetiva: **não fazer `git add .` e não commitar tudo em um único commit**. O commit de front-end é seguro apenas se for seletivo e revisar/stagear somente os arquivos do escopo de front-end e artefatos estáticos esperados.

## Bloqueio atual da publicação

`python3 ia_promocoes.py preparar-publicacao` continua bloqueando por Git:

- Git permitido: 2128 alterações
- Git bloqueante: 10 alterações
- Bloqueio: `Git possui alterações bloqueantes`

Arquivos classificados como bloqueantes pela regra atual do Promogg:

- `.env.example`
- `.gitignore`
- `banco.py`
- `ciclo_automatico.py`
- `gerar_site.py`
- `ia_promocoes.py`
- `painel.py`
- `supervisor_promogg.py`
- `painel_remoto.py`
- `seguranca_publicacao.py`

Observação: `gerar_site.py` pertence ao escopo desta melhoria de front-end. Os demais arquivos vieram de outras melhorias recentes e devem ser revisados/commitados em escopo separado ou incluídos conscientemente em outro commit.

## Estado Git resumido

Resumo por status:

- Modificados: 1535
- Novos/untracked ou adicionados: 103
- Removidos: 500
- Arquivos no escopo front/site/dist estimados: 2118

Há arquivos já staged:

- `.env.example`
- relatórios operacionais diversos
- `dist_site/app.js`
- `gerar_site.py`
- `site/app.js`

Risco operacional: se o usuário executar `git commit` sem revisar o stage, pode commitar mudanças de escopos anteriores junto com o front-end.

## Arquivos modificados relevantes ao front-end

Principais arquivos do escopo:

- `gerar_site.py`
- `site/app.js`
- `site/style.css`
- `site/index.html`
- `site/ofertas.json`
- `site/sitemap.xml`
- `site/404.html`
- `site/assistente_dados.json`
- `site/produto/**/index.html`
- `site/categoria/**/index.html`
- `dist_site/app.js`
- `dist_site/index.html`
- `dist_site/ofertas.json`
- `dist_site/sitemap.xml`
- `dist_site/404.html`
- `dist_site/assistente_dados.json`
- `dist_site/produto/**/index.html`
- `dist_site/categoria/**/index.html`
- `RELATORIO_MELHORIAS_FRONTEND.md`
- `RELATORIO_PRE_COMMIT_FRONTEND.md`

## Arquivos removidos

Remoções em categorias:

- `site/categoria/`: 221 páginas antigas removidas
- `dist_site/categoria/`: 221 páginas antigas removidas

Essas remoções são esperadas: a geração foi normalizada para 19 categorias públicas principais, substituindo centenas de categorias específicas, marcas e modelos.

Categorias públicas atuais:

- `audio`
- `automotivo`
- `bebes`
- `beleza`
- `casa`
- `celulares`
- `cozinha`
- `eletronicos`
- `esportes`
- `ferramentas`
- `games`
- `informatica`
- `jardim`
- `moda`
- `moveis`
- `outros`
- `pets`
- `saude`
- `tvs`

## Arquivos novos

Novos esperados no escopo front-end:

- 19 categorias novas em `site/categoria/`
- 19 categorias novas em `dist_site/categoria/`
- novas páginas de produto com slug saneado quando títulos antes vinham com entidades HTML
- `RELATORIO_MELHORIAS_FRONTEND.md`
- `RELATORIO_PRE_COMMIT_FRONTEND.md`

Novos fora do escopo front-end identificados:

- `painel_remoto.py`
- `seguranca_publicacao.py`
- relatórios de outras rodadas

Esses arquivos podem ser válidos, mas devem entrar em commit separado ou ser revisados explicitamente antes de um commit global.

## Segurança e arquivos sensíveis

Verificações feitas contra:

- `.env`
- bancos `.db`/`.sqlite`
- `venv/`
- `__pycache__/`
- `backups/`
- `logs/`
- perfis de navegador
- tokens
- credenciais
- cookies
- caches
- checkpoints

Resultado:

- Nenhum arquivo sensível apareceu como untracked versionável.
- Nenhum arquivo sensível apareceu como alteração rastreada.
- `.gitignore` já cobre `.env`, bancos, backups, logs, perfis Playwright/Mercado Livre, checkpoints, cookies, sessões, caches e venv.
- Não foi necessário alterar `.gitignore` nesta etapa.

## Validações executadas

```bash
git status --short
git diff --stat
git diff --check
git diff -- gerar_site.py
git diff -- site/app.js
git diff -- site/style.css
git diff -- site/index.html
git diff -- site/ofertas.json
git diff -- RELATORIO_MELHORIAS_FRONTEND.md
python3 -m py_compile gerar_site.py
python3 -m py_compile *.py
python3 ia_promocoes.py gerar-site
python3 ia_promocoes.py preparar-publicacao
python3 ia_promocoes.py validar --somente-leitura
python3 ia_promocoes.py auditar-qualidade-catalogo
```

Resultados:

- `git diff --check`: sem problemas reportados.
- `py_compile`: aprovado.
- `gerar-site`: 751 ofertas e 751 páginas em `site/`.
- `preparar-publicacao`: `site/` e `dist_site/` com 751 ofertas e 751 páginas; publicação bloqueada por Git bloqueante.
- `validar --somente-leitura`: aprovado.
- `auditar-qualidade-catalogo`: `APROVADO COM RESSALVAS NÃO BLOQUEANTES`.
- Links `meli.la`: 751.
- Imagens válidas: 751.
- Preços inválidos: 0.
- Páginas quebradas: 0.

## Riscos encontrados

1. **Mistura de escopos no Git**
   - Existem alterações de painel remoto, supervisor, segurança, banco e ciclo automático junto com front-end.

2. **Stage já contém mudanças anteriores**
   - Há arquivos staged antes desta auditoria. Um commit direto pode incluir escopo maior que o desejado.

3. **Muitas alterações estáticas**
   - A normalização de categorias gera grande volume de deleções/adições em `site/` e `dist_site/`. Isso é esperado, mas exige revisão de commit.

4. **Publicação ainda bloqueada**
   - O bloqueio é correto enquanto houver arquivos de código fora dos artefatos permitidos.

## Recomendação objetiva

Pode commitar?

- **Commit global de tudo: não recomendado.**
- **Commit seletivo de front-end: seguro**, desde que o usuário revise o stage e inclua apenas o escopo de front-end + relatórios correspondentes.

Sugestão de commit front-end:

- `gerar_site.py`
- `site/`
- `dist_site/`
- `RELATORIO_MELHORIAS_FRONTEND.md`
- `RELATORIO_PRE_COMMIT_FRONTEND.md`
- opcionalmente `RELATORIO_QUALIDADE_CATALOGO.md` e `RELATORIO_HOMOLOGACAO_PUBLICACAO_AUTOMATICA.md`, se quiser registrar os resultados operacionais atualizados.

Evitar neste commit, salvo decisão consciente:

- `.env.example`
- `.gitignore`
- `banco.py`
- `ciclo_automatico.py`
- `ia_promocoes.py`
- `painel.py`
- `painel_remoto.py`
- `seguranca_publicacao.py`
- `supervisor_promogg.py`
- relatórios de outras rodadas não relacionados ao front-end.

## Mensagem recomendada

```text
Melhora front-end estático e normaliza categorias públicas
```

## Comandos manuais recomendados

Antes de commitar, revisar o stage atual:

```bash
git diff --cached --stat
git diff --cached --name-only
```

Se quiser fazer commit seletivo de front-end, montar o stage conscientemente:

```bash
git add gerar_site.py site/ dist_site/ RELATORIO_MELHORIAS_FRONTEND.md RELATORIO_PRE_COMMIT_FRONTEND.md
git diff --cached --stat
git diff --cached --check
git commit -m "Melhora front-end estático e normaliza categorias públicas"
```

Não executar automaticamente deploy/push/publicação após o commit.
