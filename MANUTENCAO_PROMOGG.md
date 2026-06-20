# Manutenção do Promogg

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

## Quarentena

Arquivos só podem ser movidos para `quarentena_remocao/` após auditoria e validação. Esta limpeza não removeu arquivos porque os candidatos existentes não eram inequívocos.
