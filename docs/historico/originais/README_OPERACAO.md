# Operação do IA-Promocoes

Este projeto está configurado nesta fase para trabalhar somente com Mercado Livre.

## Configurar `.env`

Crie um arquivo `.env` na raiz do projeto usando `.env.example` como base:

```bash
cp .env.example .env
```

Preencha:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
MERCADO_LIVRE_AFFILIATE_ID=
INTERVALO_COLETA_MINUTOS=30
INTERVALO_POSTAGEM_MINUTOS=20
LIMITE_POSTS_DIA=10
```

Não coloque tokens, senhas ou cookies diretamente no código.

## Comando principal

Use o arquivo `ia_promocoes.py` para operar o sistema:

```bash
venv/bin/python ia_promocoes.py servicos
venv/bin/python ia_promocoes.py modo-economico
venv/bin/python ia_promocoes.py iniciar scheduler
venv/bin/python ia_promocoes.py parar scheduler
venv/bin/python ia_promocoes.py status
venv/bin/python ia_promocoes.py painel
venv/bin/python ia_promocoes.py simular
venv/bin/python ia_promocoes.py publicar-um
venv/bin/python ia_promocoes.py coletar
venv/bin/python ia_promocoes.py relatorio
```

## Modo Econômico

```bash
venv/bin/python ia_promocoes.py modo-economico
```

O Modo Econômico é o padrão operacional recomendado. Ele mantém disponíveis os recursos locais e deixa desligado tudo que pode gerar custo, requisições externas ou automação contínua.

Permitido automaticamente:

- painel local;
- banco SQLite;
- IA local/Ollama;
- site local;
- consultas locais;
- histórico;
- relatórios;
- logs.

Desligado até ativação manual:

- Playwright;
- supervisor loop;
- monitor contínuo;
- scheduler;
- Telegram real;
- deploy automático;
- Cloudflare Tunnel;
- analytics externos;
- geração automática de afiliados;
- coletas contínuas;
- verificações periódicas de API.

## Gerenciar serviços

```bash
venv/bin/python ia_promocoes.py servicos
venv/bin/python ia_promocoes.py iniciar supervisor
venv/bin/python ia_promocoes.py parar supervisor
venv/bin/python ia_promocoes.py iniciar monitor
venv/bin/python ia_promocoes.py parar monitor
venv/bin/python ia_promocoes.py iniciar scheduler
venv/bin/python ia_promocoes.py parar scheduler
```

Serviços controlados têm PID, logs, timeout de parada e status no painel.

## Iniciar produção manualmente

```bash
venv/bin/python ia_promocoes.py modo-producao
```

Use somente quando quiser habilitar os recursos de produção. O comando é manual e não deve ser configurado para iniciar com o Mac.

O comando legado abaixo continua existindo por compatibilidade, mas não é o fluxo recomendado para economia:

```bash
venv/bin/python ia_promocoes.py iniciar
```

Esse fluxo contínuo pode:

- coleta ofertas do Mercado Livre;
- aplica curadoria e score já existentes;
- exige link afiliado válido;
- atualiza fila;
- atualiza o site;
- gera texto para WhatsApp manual;
- publica no Telegram respeitando limite diário, intervalo mínimo e anti-spam.

## Parar o robô

Em outro terminal:

```bash
venv/bin/python ia_promocoes.py parar
```

O sistema cria uma flag de parada e encerra com segurança ao final do passo atual.

## Ver status

```bash
venv/bin/python ia_promocoes.py status
```

Mostra se o robô está rodando, pendentes, publicados hoje, última coleta, última publicação e erros recentes.

## Abrir painel

```bash
venv/bin/python ia_promocoes.py painel
```

Também é possível abrir diretamente:

```bash
streamlit run painel.py
```

## Simular próxima publicação

```bash
venv/bin/python ia_promocoes.py simular
```

Esse comando mostra qual post seria publicado, atualiza site/WhatsApp e não envia mensagem ao Telegram.

## Publicar somente 1 oferta

```bash
venv/bin/python ia_promocoes.py publicar-um
```

Publica no máximo 1 post pendente e respeita:

- link afiliado válido;
- não duplicidade;
- intervalo mínimo;
- limite diário;
- regras anti-spam.

## Rodar somente coleta e fila

```bash
venv/bin/python ia_promocoes.py coletar
```

Executa coleta, curadoria, fila, site e WhatsApp, sem publicar no Telegram.

## Ver site público local

Arquivos gerados:

- `site_promocoes.html`
- `site/index.html`

Abra no navegador:

```bash
open site/index.html
```

O site exibe somente ofertas com link afiliado válido.

## Usar WhatsApp manualmente

Arquivos gerados:

- `whatsapp_posts.txt`
- `site/whatsapp.html`

Abra:

```bash
open site/whatsapp.html
```

Copie manualmente as ofertas aprovadas. Não há disparo automático para grupos.

## Conferir logs

Os logs ficam na tabela `logs` do SQLite `banco.db`.

Para relatório resumido:

```bash
venv/bin/python ia_promocoes.py relatorio
```

Para consultar erros diretamente:

```bash
sqlite3 banco.db "select criado_em, etapa, mensagem from logs where nivel = 'error' order by id desc limit 10;"
```

## Observações

- Shopee está desativada nesta fase.
- Promobit/Pelando não são usados.
- WhatsApp fica apenas em modo manual/seguro.
- As regras de score não foram alteradas por esta camada operacional.
