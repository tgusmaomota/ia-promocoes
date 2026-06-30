# ADR-0004: Produtos como modulos

## Status

Aceita.

## Contexto

O Promogg e o primeiro produto/cliente da EmpresaGPT. A plataforma precisa permitir novos produtos sem copiar toda a operacao nem misturar regras de dominio.

## Decisao

Produtos devem ser tratados como modulos de cliente sobre contratos comuns da EmpresaGPT. Cada produto pode ter dominio, integracoes, storage e fluxos proprios, mas deve conversar com a plataforma por contratos estaveis.

## Consequencias

- O Promogg continua dono de ofertas, Mercado Livre, afiliados, site e curadoria.
- EmpresaGPT define interfaces compartilhadas para IA, seguranca, analytics, storage, servicos e monitoramento.
- Novos produtos devem nascer com configuracao propria e sem alterar comportamento do Promogg.

## Regras

- Produto nao deve depender de outro produto.
- Plataforma nao deve importar dominio de produto.
- Adaptadores fazem a ponte entre produto e plataforma.
- Contratos devem ser documentados antes de codigo compartilhado.

