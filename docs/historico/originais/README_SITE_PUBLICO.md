# Publicação do IA-Promocoes no GitHub Pages

Este projeto gera um site estático em `dist_site/` e publica essa pasta no GitHub Pages usando GitHub Actions.

O fluxo não altera coleta, Telegram, score nem banco. Ele só gera o site público, prepara `dist_site/`, cria `CNAME` quando houver domínio configurado e envia as mudanças para o GitHub.

## Arquivos envolvidos

```text
site/                         # site gerado localmente
dist_site/                    # site pronto para publicação
dist_site/CNAME               # domínio próprio do GitHub Pages
.github/workflows/pages.yml   # workflow que publica dist_site/
deploy_site.py                # script de deploy
ia_promocoes.py               # comando principal
```

## Configurar domínio no projeto

No arquivo `.env`, adicione seu domínio:

```bash
IA_PROMOCOES_DOMINIO=ofertas.seudominio.com.br
```

Também é possível informar na hora do deploy:

```bash
python3 ia_promocoes.py subir-site --dominio ofertas.seudominio.com.br
```

Quando o domínio estiver configurado, o deploy cria automaticamente:

```text
dist_site/CNAME
```

com o conteúdo:

```text
ofertas.seudominio.com.br
```

## Criar o repositório no GitHub

1. Acesse `https://github.com/new`.
2. Crie um repositório, por exemplo `ia-promocoes`.
3. Deixe como público ou privado. GitHub Pages funciona nos dois, dependendo do plano da conta.
4. Não precisa criar README pelo GitHub se você já vai enviar este projeto local.

Na pasta do projeto, inicialize o Git se ainda não existir:

```bash
git init
git branch -M main
git add .
git commit -m "Publica IA-Promocoes"
git remote add origin https://github.com/SEU_USUARIO/ia-promocoes.git
git push -u origin main
```

Se já existir repositório/remoto, confira:

```bash
git status
git remote -v
git branch --show-current
```

## Configurar GitHub Pages

Depois do primeiro push:

1. Abra o repositório no GitHub.
2. Vá em `Settings > Pages`.
3. Em `Build and deployment`, selecione `GitHub Actions`.
4. Salve, se o GitHub pedir confirmação.
5. Vá em `Actions` e confira o workflow `Publicar site IA-Promocoes`.

O arquivo `.github/workflows/pages.yml` publica a pasta `dist_site/` sempre que houver push na branch `main` ou `master`.

## Subir o site

Use o comando principal:

```bash
python3 ia_promocoes.py subir-site
```

Esse comando faz:

1. inicializa/prepara a base local;
2. gera o site;
3. atualiza `site/`;
4. copia o site para `dist_site/`;
5. cria `dist_site/CNAME`, se `IA_PROMOCOES_DOMINIO` estiver configurado;
6. adiciona os arquivos no Git;
7. cria commit quando houver mudanças;
8. envia a branch atual para `origin`;
9. dispara o GitHub Actions para atualizar o GitHub Pages.

Também é possível chamar o script diretamente:

```bash
python3 deploy_site.py github-actions
```

## Configurar DNS no Registro.br

Use uma destas opções.

### Opção A: subdomínio recomendado

Exemplo:

```text
ofertas.seudominio.com.br
```

No Registro.br:

1. Entre no painel do domínio.
2. Vá em `DNS`.
3. Ative/edite a zona DNS do Registro.br.
4. Crie um registro `CNAME`:

```text
Nome: ofertas
Tipo: CNAME
Valor: SEU_USUARIO.github.io
```

5. Salve as alterações.

No `.env`, use:

```bash
IA_PROMOCOES_DOMINIO=ofertas.seudominio.com.br
```

### Opção B: domínio raiz

Exemplo:

```text
seudominio.com.br
```

No Registro.br, crie registros `A` apontando para os IPs oficiais do GitHub Pages:

```text
Nome: @
Tipo: A
Valor: 185.199.108.153

Nome: @
Tipo: A
Valor: 185.199.109.153

Nome: @
Tipo: A
Valor: 185.199.110.153

Nome: @
Tipo: A
Valor: 185.199.111.153
```

Para `www`, crie também:

```text
Nome: www
Tipo: CNAME
Valor: SEU_USUARIO.github.io
```

No `.env`, use:

```bash
IA_PROMOCOES_DOMINIO=seudominio.com.br
```

## Configurar domínio no GitHub

1. Abra `Settings > Pages`.
2. Em `Custom domain`, informe o domínio configurado no `.env`.
3. Clique em `Save`.
4. Aguarde o GitHub validar o DNS.
5. Depois que a validação passar, marque `Enforce HTTPS`.

O arquivo `dist_site/CNAME` mantém essa configuração quando o site é publicado novamente.

## Validar HTTPS

Depois de configurar DNS e Pages, aguarde a propagação. Normalmente leva alguns minutos, mas pode demorar mais.

Teste:

```bash
curl -I https://ofertas.seudominio.com.br
```

O esperado é receber uma resposta `HTTP/2 200` ou `HTTP/2 301/302` redirecionando para HTTPS.

No GitHub:

1. Vá em `Settings > Pages`.
2. Confira se aparece que o domínio está válido.
3. Marque `Enforce HTTPS`.
4. Se a opção estiver desabilitada, aguarde e recarregue a página depois.

## Testar o domínio

Teste DNS:

```bash
dig ofertas.seudominio.com.br
```

Teste HTTP:

```bash
curl -I http://ofertas.seudominio.com.br
```

Teste HTTPS:

```bash
curl -I https://ofertas.seudominio.com.br
```

Abra no navegador:

```text
https://ofertas.seudominio.com.br
```

Confira se:

- a página abre com cadeado/HTTPS;
- as ofertas aparecem;
- `ofertas.json` carrega;
- os botões de oferta abrem os links afiliados;
- o domínio exibido é o seu domínio próprio.

## Operação diária

Quando quiser atualizar o site publicado:

```bash
python3 ia_promocoes.py subir-site
```

Para apenas gerar localmente:

```bash
python3 ia_promocoes.py gerar-site
python3 ia_promocoes.py publicar-site
```

Para testar local:

```bash
python3 ia_promocoes.py servir-site
```

Acesse:

```text
http://localhost:8000/
```

## Erros comuns

### Esta pasta ainda não é um repositório Git

Execute:

```bash
git init
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/ia-promocoes.git
```

Depois faça o primeiro commit e push.

### O remoto origin não está configurado

Execute:

```bash
git remote add origin https://github.com/SEU_USUARIO/ia-promocoes.git
```

### Workflow não publicou

Confira:

1. `Settings > Pages` está em `GitHub Actions`;
2. a branch enviada é `main` ou `master`;
3. existe conteúdo em `dist_site/`;
4. o workflow aparece em `Actions`;
5. o GitHub Pages está habilitado no repositório.

### Domínio não valida

Confira:

1. `dist_site/CNAME` tem exatamente o domínio, sem `https://`;
2. o DNS do Registro.br aponta para `SEU_USUARIO.github.io` no caso de subdomínio;
3. o domínio informado em `Settings > Pages` é o mesmo do `CNAME`;
4. a propagação DNS já ocorreu.

## Segurança

- Não publique `.env`, tokens, cookies ou credenciais.
- O site público deve conter apenas HTML, CSS, JSON público e `CNAME`.
- `ofertas.json` deve conter somente dados públicos de ofertas e links afiliados.
- Telegram e WhatsApp continuam independentes do GitHub Pages.
