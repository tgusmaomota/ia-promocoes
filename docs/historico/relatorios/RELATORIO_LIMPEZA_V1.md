# Relatorio de Limpeza V1

Data: 2026-06-27

## Escopo

Preparacao da Versao Estavel 1.0 com foco em operacao local segura, comandos oficiais, auditoria de publicacao e quarentena sem exclusao definitiva.

## Arquivos mantidos no fluxo oficial

- `ia_promocoes.py`: central CLI, agora com `modo-estavel`, `modo-operacao`, `modo-divulgacao` e `status-servicos`.
- `servicos_promogg.py`: gerenciador de servicos, agora com `MODO_ESTAVEL_LOCAL` como padrao.
- `seguranca_publicacao.py`: gate de seguranca para bloquear publicacao com criticos/bloqueantes.
- `site/` e `dist_site/`: mantidos como artefatos publicos auditaveis.
- `banco.py`, `catalogo_integridade.py`, `qualidade_catalogo.py`, `integridade_paginas_produto.py`, `integridade_precos.py`: mantidos para validacao e integridade.
- `promogg_assistente.py`: mantido como integracao local com Ollama.

## Arquivos em quarentena

Nenhum arquivo operacional foi movido nesta primeira etapa.

## Candidatos identificados, mas mantidos

| Arquivo | Motivo | Risco se mover agora | Pode apagar no futuro |
| --- | --- | --- | --- |
| `telegram.txt` | Saida legada/manual de publicacao | Alto: ainda pode ser gerado por `agente_publicador.py` | Sim, apos remover dependencia |
| `whatsapp.txt` | Saida legada/manual de publicacao | Alto: ainda pode ser gerado por `agente_publicador.py` | Sim, apos remover dependencia |
| `whatsapp_posts.txt` | Saida usada por geracao/restauracao | Alto: referenciado por restauracao e publicador | Talvez, apos migracao |
| `instagram.txt` | Saida legada/manual de publicacao | Medio: ainda pode ser gerado por script legado | Sim |
| `promobit.txt` | Rascunho/manual legado | Baixo: sem referencia operacional encontrada nesta revisao curta | Sim, apos revisao de conteudo |
| `site_promocoes.html` | HTML legado | Alto: referenciado por `publicador_telegram.py`, `agente_site.py` e homologacao | Sim, apos confirmar site estatico novo |
| `relatorio_auditoria_ofertas.txt` | Relatorio textual antigo | Baixo | Sim, apos arquivar historico |

## Ajustes aplicados

- Criado `PROMOGG_V1_COMANDOS_OFICIAIS.md`.
- Criada pasta `quarentena_v1/` com manifesto.
- `promocoes.db` adicionado ao `.gitignore`.
- Modos v1 adicionados ao CLI.
- Publicacao e divulgacao continuam bloqueadas por auditoria quando houver achados criticos ou bloqueantes.

## Proxima limpeza segura

Antes de mover scripts Python para `quarentena_v1/`, rodar uma analise de dependencias por import, chamadas CLI e referencias textuais. Depois mover em pequenos lotes e validar:

```bash
python3 -m py_compile *.py
python3 ia_promocoes.py modo-estavel
python3 ia_promocoes.py auditar-seguranca-publicacao
python3 ia_promocoes.py validar --somente-leitura
```
