# Manutenção

Este documento consolida rotinas de manutenção do Promogg.

## Rotinas Seguras

```bash
python3 ia_promocoes.py validar --somente-leitura
python3 validar_catalogo_publico.py
python3 gerar_site_publico.py --fonte catalogo_publico/ofertas.json --destino /tmp/promogg_dist_teste --dominio promogg.com.br
python3 validar_catalogo_publico.py --arquivo /tmp/promogg_dist_teste/ofertas.json
```

## Limpeza

- Relatórios temporários devem ir para `docs/historico/relatorios/` ou `backups/relatorios/`.
- Artefatos gerados devem ficar fora do Git.
- Antes de qualquer remoção local: criar backup, mostrar diff e validar.
- Nunca apagar `.env`, banco local ou perfis de navegador sem confirmação explícita.

## Operação

Documentos originais preservados:

- `docs/historico/originais/MANUTENCAO_PROMOGG.md`
- `docs/historico/originais/MODO_ECONOMICO_PROMOGG.md`
- `docs/historico/originais/README_OPERACAO.md`
