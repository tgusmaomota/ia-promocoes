# ADR-0001: Core sem dependencia do Promogg

## Status

Aceita.

## Contexto

O Promogg e o Cliente n. 1 da EmpresaGPT, mas a plataforma nao pode nascer dependente de nomes, banco, site, supervisor, deploy ou comandos do Promogg. A Fase 2 define contratos antes de qualquer extracao.

## Decisao

O `empresa_gpt/core` deve permanecer independente do Promogg. Ele pode definir contratos, tipos, erros, configuracao e policies de plataforma, mas nao deve importar modulos do Promogg nem executar comportamento operacional.

## Consequencias

- O Core pode ser testado sem banco, site, painel, deploy, supervisor ou variaveis de producao do Promogg.
- O Promogg so passara a usar o Core por adaptadores futuros.
- Qualquer dependencia inversa, de EmpresaGPT para Promogg, deve ser tratada como violacao arquitetural.

## Regras

- Nao importar `ia_promocoes`, `banco`, `gerar_site`, `painel`, `supervisor_promogg` ou modulos equivalentes.
- Nao ler `.env` automaticamente em imports.
- Nao abrir conexoes, processos, sockets ou arquivos operacionais em import.
- Nao assumir Mercado Livre, ofertas, afiliados ou catalogo Promogg como dominio da plataforma.

