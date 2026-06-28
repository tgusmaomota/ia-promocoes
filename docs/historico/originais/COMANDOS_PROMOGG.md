# Comandos Promogg

Use `python3 ia_promocoes.py comandos` para a lista viva de comandos e descrições.

## Checklist operacional

```bash
# Estado e painel
python3 ia_promocoes.py status
python3 ia_promocoes.py painel
python3 ia_promocoes.py manutencao
python3 ia_promocoes.py online
python3 ia_promocoes.py offline

# Coleta e catálogo
python3 ia_promocoes.py coletar-confiavel --visual
python3 ia_promocoes.py testar-captura-produto "URL_DO_PRODUTO"
python3 ia_promocoes.py comparar-captura "URL_DO_PRODUTO"
python3 ia_promocoes.py gerar-site
python3 ia_promocoes.py validar

# Curadoria e recuperação
python3 ia_promocoes.py reprocessar-pendentes --dry-run
python3 ia_promocoes.py recuperar-indisponiveis --dry-run

# Publicação (somente após validar)
python3 ia_promocoes.py subir-site
```

## Segurança operacional

- Use `--dry-run` antes de reprocessar ou recuperar quando disponível.
- `subir-site` bloqueia publicação se a validação do site falhar.
- Não versione `.env`, `banco.db`, perfis Playwright, logs ou backups.
- `online` habilita automações; prefira `manutencao` durante ajustes locais.
