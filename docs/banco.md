# Banco

O projeto usa SQLite local em `banco.db`. Esse arquivo é operacional, sensível e não deve ir para o Git.

## Responsabilidades

- Produtos e postagens.
- Histórico de preços.
- Eventos do sistema.
- Saúde da coleta.
- Dados locais do assistente e feedback.

## Segurança

- `banco.db` está ignorado.
- Backups de banco ficam em `backups/`.
- Migrações criam backups antes de alterações estruturais.
- O site público não depende do banco no GitHub Actions.

## Validação

```bash
python3 ia_promocoes.py validar --somente-leitura
python3 ia_promocoes.py auditar-base
```
