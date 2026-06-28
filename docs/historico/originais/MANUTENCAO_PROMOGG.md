# Manutenção do Promogg

## Modo Econômico

O Promogg deve operar em Modo Econômico por padrão. Antes de qualquer manutenção ou homologação:

```bash
python3 ia_promocoes.py modo-economico
python3 ia_promocoes.py servicos
```

Serviços externos/custosos devem aparecer OFF, incluindo Playwright, supervisor loop, monitor contínuo, scheduler, Telegram, deploy e Cloudflare Tunnel.

Para iniciar manualmente um serviço específico:

```bash
python3 ia_promocoes.py iniciar supervisor
python3 ia_promocoes.py parar supervisor
```

O painel possui a aba `Serviços` para iniciar, parar e reiniciar serviços com um clique, exibindo PID, CPU, memória, tempo ligado, requisições e custo estimado.

Não configure LaunchAgent, cron, login item ou autostart no Mac para serviços do Promogg.

## Rotina segura

1. Entre em manutenção: `python3 ia_promocoes.py manutencao`.
2. Crie backup: `python3 ia_promocoes.py backup`.
3. Faça alterações locais e rode `python3 -m py_compile *.py`.
4. Gere o site: `python3 ia_promocoes.py gerar-site`.
5. Valide: `python3 ia_promocoes.py validar`.
6. Revise `python3 ia_promocoes.py status`.
7. Publique apenas após aprovação: `python3 ia_promocoes.py subir-site`.

## Recuperação

- Perfil Playwright bloqueado: `python3 ia_promocoes.py diagnosticar-playwright`, depois `reparar-playwright`.
- API inconclusiva: mantenha o status do produto; `403` não significa indisponibilidade.
- Produtos indevidamente indisponíveis: execute primeiro `recuperar-indisponiveis --dry-run`.
- Recuperação de arquivos: consulte `python3 ia_promocoes.py restaurar`.

## Playwright Mercado Livre com pausa e retomada

Fluxo recomendado quando a sessão começa a ficar instável:

```bash
python3 ia_promocoes.py pausar-playwright
python3 ia_promocoes.py login-mercadolivre
python3 ia_promocoes.py testar-playwright-sessao
python3 ia_promocoes.py retomar-coleta
python3 ia_promocoes.py validar --somente-leitura
```

Parâmetros de ritmo humano no `.env`:

```env
PLAYWRIGHT_LOTE_TAMANHO=25
PLAYWRIGHT_PAUSA_MIN=1.5
PLAYWRIGHT_PAUSA_MAX=4.0
PLAYWRIGHT_PAUSA_LOTE_MIN=20
PLAYWRIGHT_PAUSA_LOTE_MAX=45
```

Garantias desses comandos:

- `login-mercadolivre` só abre o navegador, espera login manual e preserva `perfil_mercadolivre`.
- `testar-playwright-sessao` apenas confirma a sessão; não coleta, não gera afiliado e não altera banco.
- `retomar-coleta` usa `.coleta_confiavel_checkpoint.json`, evita repetir itens já salvos e não aciona Telegram/deploy.
- Se houver logout, a coleta ou afiliados pausam com `login_necessario`, fecham o navegador e preservam o checkpoint.
- `pausar-playwright` coloca o sistema em `MANUTENCAO`, para o scheduler local, fecha Chrome for Testing, remove locks temporários e não apaga cookies.

## Quarentena

Arquivos só podem ser movidos para `quarentena_remocao/` após auditoria e validação. Esta limpeza não removeu arquivos porque os candidatos existentes não eram inequívocos.
