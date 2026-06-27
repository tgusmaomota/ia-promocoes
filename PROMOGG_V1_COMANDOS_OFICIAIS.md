# Promogg V1 - Comandos Oficiais

Este documento congela os comandos recomendados para a Versao Estavel 1.0.
O modo padrao da v1 e `MODO_ESTAVEL_LOCAL`: local, auditavel e sem publicacao automatica.

## Comandos seguros

```bash
python3 ia_promocoes.py modo-estavel
python3 ia_promocoes.py status-servicos
python3 ia_promocoes.py status
python3 ia_promocoes.py relatorio
python3 ia_promocoes.py relatorio-precos
python3 ia_promocoes.py saude
python3 ia_promocoes.py saude-detalhada
python3 ia_promocoes.py auditar-base
python3 ia_promocoes.py auditar-sistema
python3 ia_promocoes.py auditar-seguranca-publicacao
python3 ia_promocoes.py checklist-divulgacao
python3 ia_promocoes.py auditar-qualidade-catalogo
python3 ia_promocoes.py auditar-paginas-produto
python3 ia_promocoes.py auditar-precos
python3 ia_promocoes.py perguntar "sua pergunta"
python3 ia_promocoes.py treinar-memoria
python3 ia_promocoes.py gerar-site
python3 ia_promocoes.py validar --somente-leitura
python3 ia_promocoes.py servir-site
```

## Comandos de manutencao

```bash
python3 ia_promocoes.py modo-economico
python3 ia_promocoes.py iniciar painel
python3 ia_promocoes.py iniciar site-local
python3 ia_promocoes.py parar painel
python3 ia_promocoes.py parar site-local
python3 ia_promocoes.py backup
python3 ia_promocoes.py limpar-seguro --dry-run
python3 ia_promocoes.py curadoria-automatica --dry-run
python3 ia_promocoes.py ciclo-automatico --dry-run
python3 ia_promocoes.py preparar-publicacao --dry-run
python3 ia_promocoes.py diagnosticar-playwright
python3 ia_promocoes.py testar-playwright-sessao
```

## Comandos de producao controlada

```bash
python3 ia_promocoes.py modo-operacao
python3 ia_promocoes.py modo-divulgacao
python3 ia_promocoes.py preparar-publicacao
python3 ia_promocoes.py publicar-site
python3 ia_promocoes.py subir-site
python3 ia_promocoes.py publicar
```

Regras da v1:

- `modo-operacao` roda ciclo controlado em dry-run e nao faz deploy.
- `modo-divulgacao` so libera o estado se `auditar-seguranca-publicacao` estiver aprovado.
- `subir-site` e `publicar` sao bloqueados por auditoria de seguranca.
- Telegram/social real exige comando ou flag explicita fora do modo estavel.

## Comandos perigosos

Use somente com intencao clara, backup recente e revisao do impacto.

```bash
python3 ia_promocoes.py coletar
python3 ia_promocoes.py coletar-confiavel
python3 ia_promocoes.py retomar-coleta
python3 ia_promocoes.py monitorar-precos
python3 ia_promocoes.py atualizar-categorias
python3 ia_promocoes.py gerar-afiliados
python3 ia_promocoes.py reconstruir-base
python3 ia_promocoes.py reparar-playwright
python3 ia_promocoes.py meli-refresh-token
python3 ia_promocoes.py online
python3 ia_promocoes.py iniciar-producao
python3 ia_promocoes.py modo-producao
python3 ia_promocoes.py supervisor-loop
```

## Comandos legados ou descontinuados na v1

Eles permanecem no codigo por compatibilidade, mas nao fazem parte do fluxo oficial da v1.

```bash
python3 ia_promocoes.py servicos
python3 ia_promocoes.py producao
python3 ia_promocoes.py iniciar
python3 ia_promocoes.py supervisor
python3 ia_promocoes.py publicar-um
python3 ia_promocoes.py analytics-teste
python3 ia_promocoes.py painel-remoto
python3 ia_promocoes.py publicar-alteracoes-painel
```

Use os aliases oficiais quando existirem:

- `status-servicos` no lugar de `servicos`.
- `modo-operacao` no lugar de `modo-producao` para rotina controlada.
- `modo-estavel` como ponto de partida diario.
