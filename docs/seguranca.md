# Segurança

Prioridades do projeto:

1. Segurança
2. Integridade
3. Autenticidade
4. Disponibilidade

## Controles Atuais

- `.env`, `banco.db`, logs, perfis de navegador e backups estão fora do Git.
- Catálogo público sanitizado versionado.
- Deploy bloqueado contra catálogo vazio.
- GitHub Pages gera `dist_site/` em CI.
- Auditoria de publicação: `python3 ia_promocoes.py auditar-seguranca-publicacao`.
- Checklist de divulgação: `python3 ia_promocoes.py checklist-divulgacao`.

## Dados que Nunca Devem Ir Para o Git

- `.env`
- tokens OAuth
- cookies
- sessões Playwright/Chrome
- `banco.db`
- logs operacionais
- perfis de navegador
- backups de banco
- CSVs temporários

## Próximos Controles

- JWT
- RBAC
- OAuth2 Google/GitHub
- MFA
- bcrypt/Argon2
- criptografia em repouso
- HTTPS obrigatório
- CSP
- CORS restritivo
- auditoria completa
- SIEM/logs
- rate limiting
