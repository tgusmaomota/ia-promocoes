# EmpresaGPT Master Plan

## Status

Fase 1 iniciada em 2026-06-30.

EmpresaGPT passa a ser a plataforma-base para clientes operacionais com automacao, IA, analytics, seguranca, integracoes e publicacao controlada. O Promogg e oficialmente o Cliente n. 1 da plataforma.

## Objetivo da Fase 1

Criar a fundacao arquitetural sem alterar comportamento existente do Promogg.

Esta fase nao move codigo, nao renomeia modulos, nao altera imports, nao altera banco, nao altera site, nao altera painel, nao altera deploy, nao altera supervisor e nao altera producao.

## Principios

- Preservar o Promogg como operacao viva.
- Separar decisao arquitetural de refatoracao.
- Evoluir por contratos testaveis, nao por grandes movimentos de arquivos.
- Reutilizar apenas modulos com fronteiras claras.
- Tratar seguranca, auditoria e rastreabilidade como plataforma, nao como remendos.
- Manter compatibilidade operacional ate existir equivalencia funcional comprovada.

## Visao de Plataforma

EmpresaGPT sera organizada em camadas:

- `core`: configuracao, identidade da plataforma, contratos, erros, logging e policies.
- `ai`: provedores de IA, prompts, revisores, memoria e avaliadores.
- `analytics`: eventos, metricas, funis, dashboards e exportacoes.
- `security`: autenticacao, autorizacao, sessoes, CSRF, origem, segredos e auditoria.
- `storage`: repositorios, migracoes, modelos persistidos e adaptadores de banco.
- `services`: regras de negocio reutilizaveis.
- `monitoring`: saude, alertas, observabilidade e supervisor generico.
- `deployment`: publicacao, validacoes pre-deploy, rollback e ambientes.
- `integrations`: provedores externos como marketplaces, mensageria, GitHub e Cloudflare.
- `shared`: utilitarios sem dependencia de dominio.
- `docs`: decisoes, ADRs, runbooks e contratos internos.

## Cliente 1: Promogg

O Promogg permanece dono do seu dominio atual: curadoria, validacao e publicacao de ofertas. Nesta fase, ele nao e desmontado. Ele passa a servir como caso real para extrair padroes da plataforma EmpresaGPT nas proximas fases.

## Entregas da Fase 1

- Estrutura `empresa_gpt/` criada com READMEs de responsabilidade.
- Documentacao fundadora criada.
- Auditoria arquitetural inicial registrada.
- Modulos classificados por potencial de reutilizacao.
- Riscos e plano da Fase 2 definidos.

## Criterios de Aceite

- Nenhum arquivo operacional do Promogg alterado.
- Nenhum import alterado.
- Nenhum comportamento runtime alterado.
- Documentacao suficiente para orientar a Fase 2.
- Classificacao inicial clara, revisavel e conservadora.

