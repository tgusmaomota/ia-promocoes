# Produção Promogg

## Iniciar com segurança

```bash
python3 ia_promocoes.py iniciar-producao
```

O comando verifica ambiente, banco, perfil Playwright, OAuth, catálogo público, links `meli.la`, imagens, SEO, `.env`, proteção do Git, backups e pré-requisitos dos serviços. Todo o preflight é somente leitura; ele só chama `online` e registra evento operacional quando não houver falha crítica.

Para revisar sem iniciar serviços, deploy ou Telegram:

```bash
python3 ia_promocoes.py iniciar-producao --dry-run
```

O modo seco é somente leitura: não gera relatórios rastreados, não registra evento operacional e não altera o estado do Git.

Também é possível auditar os artefatos existentes sem regenerar o site:

```bash
python3 ia_promocoes.py validar --somente-leitura
```

## Manutenção e parada

```bash
python3 ia_promocoes.py manutencao-producao
python3 ia_promocoes.py parar-producao
```

O primeiro mantém painel e dados locais disponíveis. O segundo equivale a `offline` e preserva banco, histórico e backups.

## Recuperação

1. Leia os itens `[FALHA]` do checklist.
2. Para Git pendente, revise e faça commit ou guarde as alterações antes de iniciar produção.
3. Para perfil Playwright bloqueado, use `python3 ia_promocoes.py diagnosticar-playwright` e, se necessário, `reparar-playwright`.
4. Para OAuth, use `python3 ia_promocoes.py meli-testar-token` ou `meli-auth`.
5. Para catálogo, execute `python3 ia_promocoes.py validar` e corrija o erro indicado.
6. Para serviços já ativos ou inconsistentes, use `python3 ia_promocoes.py status` antes de qualquer reinício.
