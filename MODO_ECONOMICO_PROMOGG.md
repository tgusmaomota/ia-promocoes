# Modo Econômico do Promogg

O Promogg inicia por padrão em Modo Econômico: nada que use APIs externas, alto volume de requisições, Playwright, Telegram, deploy, túnel remoto ou automação contínua deve ser iniciado automaticamente.

## Permitido no Modo Econômico

- Painel local.
- Banco SQLite.
- Ollama/local AI.
- Site local.
- Consultas locais.
- Histórico de preços.
- Relatórios.
- Dashboard e logs.

## Desligado até ativação manual

- Playwright.
- Supervisor Loop.
- Monitor contínuo.
- Scheduler.
- Deploy automático.
- Publicação automática.
- Telegram de ofertas.
- Cloudflare Tunnel.
- Analytics externos.
- Geração automática de afiliados.
- Coletas contínuas.
- Verificações periódicas da API Mercado Livre.
- Atualizações automáticas de preços.
- Qualquer tarefa agendada.

## Ver status dos serviços

```bash
python3 ia_promocoes.py servicos
```

O comando mostra ON/OFF, PID, CPU, memória, tempo ligado, requisições, custo estimado, log e watchdog.

## Iniciar/parar serviços manualmente

```bash
python3 ia_promocoes.py iniciar playwright
python3 ia_promocoes.py parar playwright

python3 ia_promocoes.py iniciar supervisor
python3 ia_promocoes.py parar supervisor

python3 ia_promocoes.py iniciar monitor
python3 ia_promocoes.py parar monitor

python3 ia_promocoes.py iniciar scheduler
python3 ia_promocoes.py parar scheduler

python3 ia_promocoes.py iniciar telegram
python3 ia_promocoes.py parar telegram

python3 ia_promocoes.py iniciar tunnel
python3 ia_promocoes.py parar tunnel

python3 ia_promocoes.py iniciar deploy
python3 ia_promocoes.py parar deploy
```

Observações:

- `playwright`, `telegram` e `deploy` são flags de habilitação; não executam coleta, envio ou publicação no ato.
- `tunnel` só inicia se `PROMOGG_TUNNEL_COMMAND` estiver configurado no `.env`.
- `scheduler`, `monitor`, `supervisor`, `painel` e `site-local` possuem PID e log.

## Ativar Modo Econômico

```bash
python3 ia_promocoes.py modo-economico
```

Esse comando para serviços custosos/externos e mantém apenas recursos locais permitidos.

## Ativar Modo Produção

```bash
python3 ia_promocoes.py modo-producao
```

Esse comando deve ser usado manualmente. Ele habilita/inicia os serviços necessários para produção, mas não faz deploy nem envia Telegram apenas por habilitar flags.

## Segurança

- Não há configuração de autostart no Mac.
- Não foi criado LaunchAgent.
- Não foi criado cron.
- Não foi criado serviço de sistema.
- Processos controlados possuem PID file em `.promogg_servicos/` ou nos PID files legados.
- Logs ficam em `logs/`.
- Parada usa SIGTERM, aguarda timeout e só então força encerramento se o processo não sair.
- O watchdog do gerenciador detecta PID morto e exibe OFF.

## Painel

O painel possui a aba `Serviços`, com:

- status ON/OFF;
- PID;
- CPU;
- memória;
- tempo ligado;
- requisições;
- custo estimado;
- botão Iniciar;
- botão Parar;
- botão Reiniciar.

Banco e Ollama são exibidos como recursos locais e não têm botão de controle no painel.
