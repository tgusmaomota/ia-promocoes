# Comandos

Este documento consolida os guias antigos de comandos. Os originais completos foram preservados em `docs/historico/originais/`.

## Ajuda

```bash
python3 ia_promocoes.py comandos
```

## Validação e Segurança

```bash
python3 ia_promocoes.py validar --somente-leitura
python3 ia_promocoes.py auditar-seguranca-publicacao
python3 ia_promocoes.py checklist-divulgacao
python3 validar_catalogo_publico.py
```

## Site Público

```bash
python3 ia_promocoes.py gerar-site
python3 gerar_site_publico.py --fonte catalogo_publico/ofertas.json --destino /tmp/promogg_dist_teste --dominio promogg.com.br
python3 validar_catalogo_publico.py --arquivo /tmp/promogg_dist_teste/ofertas.json
```

## Serviços

```bash
python3 ia_promocoes.py status
python3 ia_promocoes.py servicos
python3 ia_promocoes.py modo-estavel
python3 ia_promocoes.py modo-economico
python3 ia_promocoes.py parar
```

## API Read-only

```bash
python3 ia_promocoes.py api
python3 ia_promocoes.py api-teste
python3 ia_promocoes.py auth-teste
```

O comando `api` inicia a API local em `127.0.0.1:8001` com Uvicorn e `--reload`. A API é somente leitura, não substitui o painel Streamlit e não implementa login/JWT nesta fase.

O comando `auth-teste` exercita o fluxo experimental local de autenticação com `TestClient`, banco temporário em `/tmp` e variáveis de ambiente forçadas apenas dentro do processo. Ele não inicia servidor, não ativa produção, não toca no `banco.db` e imprime somente `AUTH_TESTE=ok` quando passa.

Opções:

```bash
python3 ia_promocoes.py api --host 127.0.0.1 --porta 8001
```

O host `0.0.0.0` é bloqueado pelo CLI para evitar exposição acidental sem camada autenticada.

## Coleta e Curadoria

```bash
python3 ia_promocoes.py coletar
python3 ia_promocoes.py coletar-confiavel
python3 ia_promocoes.py curadoria-automatica --dry-run
python3 ia_promocoes.py calibrar-curadoria
python3 ia_promocoes.py atualizar-categorias
```

## Afiliados e Mercado Livre

```bash
python3 ia_promocoes.py login-mercadolivre
python3 ia_promocoes.py meli-auth
python3 ia_promocoes.py meli-testar-token
python3 ia_promocoes.py meli-refresh-token
python3 ia_promocoes.py gerar-afiliados
python3 ia_promocoes.py diagnosticar-compartilhar
```

## Recuperação e Manutenção

```bash
python3 ia_promocoes.py backup
python3 ia_promocoes.py restaurar
python3 ia_promocoes.py restaurar-catalogo-valido
python3 ia_promocoes.py reconstruir-base --dry-run
python3 ia_promocoes.py limpar-seguro
```

## Fontes Consolidadas

- `docs/historico/originais/COMANDOS_PROMOGG.md`
- `docs/historico/originais/GUIA_COMPLETO_COMANDOS_PROMOGG.md`
- `docs/historico/originais/PROMOGG_V1_COMANDOS_OFICIAIS.md`
- `docs/historico/originais/README_OPERACAO.md`
