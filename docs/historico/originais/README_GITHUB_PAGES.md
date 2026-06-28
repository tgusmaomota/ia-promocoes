# GitHub Pages do IA-Promocoes

Este guia publica o site estático do IA-Promocoes em:

```text
https://promogg.com.br
```

O site publicado vem da pasta:

```text
dist_site/
```

O comando operacional é:

```bash
python3 ia_promocoes.py subir-site
```

Esse comando gera o site, atualiza `dist_site/`, cria `dist_site/CNAME`, executa `git add`, `git commit` quando houver mudanças e `git push`.

## Arquivos de publicação

```text
publicar_site_git.py
dist_site/CNAME
.github/workflows/pages.yml
README_GITHUB_PAGES.md
```

O arquivo `dist_site/CNAME` deve conter exatamente:

```text
promogg.com.br
```

## Criar o repositório no GitHub

1. Acesse `https://github.com/new`.
2. Crie um repositório, por exemplo `ia-promocoes`.
3. Na pasta local do projeto, rode:

```bash
git init
git branch -M main
git add .
git commit -m "Configura GitHub Pages do IA-Promocoes"
git remote add origin https://github.com/SEU_USUARIO/ia-promocoes.git
git push -u origin main
```

Se o repositório local já existir, confira:

```bash
git status
git remote -v
git branch --show-current
```

## Conectar o GitHub Pages

1. Abra o repositório no GitHub.
2. Vá em `Settings > Pages`.
3. Em `Build and deployment`, selecione `GitHub Actions`.
4. Salve.
5. Vá em `Actions` e confirme que o workflow `Publicar site IA-Promocoes` aparece.

O workflow `.github/workflows/pages.yml` publica a pasta `dist_site/`.

## Configurar domínio personalizado no GitHub

1. No repositório, vá em `Settings > Pages`.
2. Em `Custom domain`, informe:

```text
promogg.com.br
```

3. Clique em `Save`.
4. Aguarde a validação do DNS.
5. Quando a opção estiver disponível, marque `Enforce HTTPS`.

## DNS no Registro.br

Como `promogg.com.br` é domínio raiz, crie registros `A` apontando para os IPs oficiais do GitHub Pages.

No painel do Registro.br:

1. Entre em `https://registro.br`.
2. Abra o domínio `promogg.com.br`.
3. Vá em `DNS`.
4. Use a zona DNS do Registro.br.
5. Crie estes registros:

```text
Tipo: A
Nome: @
Valor: 185.199.108.153

Tipo: A
Nome: @
Valor: 185.199.109.153

Tipo: A
Nome: @
Valor: 185.199.110.153

Tipo: A
Nome: @
Valor: 185.199.111.153
```

Se o Registro.br não aceitar `@` no campo `Nome`, deixe o campo de nome vazio para representar o domínio raiz.

Opcional, mas recomendado para redirecionar `www.promogg.com.br`:

```text
Tipo: CNAME
Nome: www
Valor: SEU_USUARIO.github.io
```

Troque `SEU_USUARIO` pelo seu usuário ou organização do GitHub. Não inclua o nome do repositório nesse CNAME.

Não crie registro curinga como:

```text
*.promogg.com.br
```

## Atualizar o site publicado

Depois de GitHub Pages e DNS configurados, use:

```bash
python3 ia_promocoes.py subir-site
```

O comando executa:

```bash
git add dist_site .github/workflows/pages.yml README_GITHUB_PAGES.md publicar_site_git.py ia_promocoes.py
git commit -m "Atualiza site IA-Promocoes"
git push origin BRANCH_ATUAL
```

Se não houver alteração, o commit não é criado, mas o push ainda é executado.

## Validar DNS

Teste os registros `A`:

```bash
dig promogg.com.br +noall +answer -t A
```

O resultado deve mostrar:

```text
promogg.com.br.  IN A  185.199.108.153
promogg.com.br.  IN A  185.199.109.153
promogg.com.br.  IN A  185.199.110.153
promogg.com.br.  IN A  185.199.111.153
```

Teste o `www`, se tiver criado:

```bash
dig www.promogg.com.br +noall +answer
```

O resultado deve apontar para:

```text
SEU_USUARIO.github.io
```

## Validar HTTPS

Depois que o DNS propagar e o GitHub validar o domínio:

```bash
curl -I https://promogg.com.br
```

O esperado é receber `200`, `301` ou `302` em HTTPS.

Também teste:

```bash
curl -I http://promogg.com.br
```

Depois de ativar `Enforce HTTPS`, o HTTP deve redirecionar para HTTPS.

## Teste final

Abra no navegador:

```text
https://promogg.com.br
```

Confira:

- a página abre com HTTPS;
- o domínio exibido é `promogg.com.br`;
- as ofertas carregam;
- `https://promogg.com.br/ofertas.json` abre;
- os botões de oferta abrem os links de afiliado.

## Referência oficial

Os registros acima seguem a documentação oficial do GitHub Pages para domínio apex, que usa estes IPs:

```text
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

Documentação: `https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site`
