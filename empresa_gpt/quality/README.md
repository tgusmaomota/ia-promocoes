# Quality Engine

## Filosofia

O Quality Engine e o guardiao automatico da EmpresaGPT. Ele verifica arquitetura, seguranca, documentacao, contratos, preservacao do Promogg e estado do Git antes que mudancas avancem.

Nesta fase ele e local, seguro e verificadora. Nao executa deploy, Telegram, supervisor-loop, online, coleta, Playwright automatico, publicacao, alteracao de banco, alteracao de catalogo ou alteracao de site publico.

## Responsabilidades

- `rules.py`: regras oficiais de qualidade.
- `checks.py`: verificacoes individuais.
- `engine.py`: orquestra a execucao das verificacoes.
- `report.py`: gera resumo humano, relatorio Markdown e JSON.
- `cli.py`: interface futura da plataforma.

## Entradas

- Arvore local do repositorio.
- Arquivos documentais da EmpresaGPT.
- Contratos inertes.
- Status local do Git.
- Codigo fonte para analise estatica de imports.

## Saidas

- Resumo humano no terminal.
- `RELATORIO_EMPRESAGPT_QUALITY_ENGINE.md`.
- `RELATORIO_EMPRESAGPT_QUALITY_ENGINE.json` quando `--json` for usado.
- Codigo de saida seguro para automacoes futuras.

## Erros

- Check critico: risco alto de seguranca ou violacao estrutural.
- Check bloqueante: impede avancar sem correcao.
- Check alerta: nao bloqueia sem `--strict`, mas exige revisao.

## Seguranca

- Sem rede por padrao.
- Sem escrita em banco.
- Sem chamada a deploy.
- Sem envio de Telegram.
- Sem supervisor-loop.
- Sem coleta ou Playwright automatico.
- Sem alteracao de `site/`, `dist_site/` ou `catalogo_publico/`.

## Uso

```bash
python3 ia_promocoes.py quality-check
python3 ia_promocoes.py quality-check --json
python3 ia_promocoes.py quality-check --strict
```

## Uso Futuro

O Quality Engine sera integrado futuramente a:

- pre-commit;
- GitHub Actions;
- CI;
- checklist de release;
- painel administrativo;
- supervisor;
- modo-divulgacao.

Nenhuma dessas integracoes e ativada automaticamente nesta fase.

