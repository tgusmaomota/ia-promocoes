# Roadmap

## Concluído

- Limpeza segura do índice Git.
- Remoção de artefatos gerados do Git.
- Catálogo público sanitizado.
- Geração estática via `gerar_site_publico.py`.
- Proteção contra deploy vazio.
- GitHub Pages gerando `dist_site/` no CI.
- Remoção de `dist_site/` do Git.
- Organização inicial da documentação.

## Em Andamento

- Consolidação da documentação operacional.
- Redução da quantidade de arquivos na raiz.
- Separação entre documentação permanente e histórico.
- Melhoria contínua das validações de publicação.

## Próxima Versão

- Autenticação JWT.
- RBAC com roles e permissões.
- OAuth2 Google/GitHub.
- MFA.
- Senhas com bcrypt ou Argon2.
- CORS restritivo.
- CSP.
- Rate limiting.
- Testes automatizados.
- Docker.
- CI/CD completo.

## Longo Prazo

- Criptografia em repouso para dados sensíveis.
- HTTPS obrigatório em todos os ambientes publicados.
- Auditoria completa: quem fez o quê, quando e de onde.
- SIEM/logs estruturados.
- Monitoramento de segurança e atividade suspeita.
- Hardening de infraestrutura.
- Separação formal em `app/`, `backend/`, `frontend/`, `scripts/` e `tests/`.
