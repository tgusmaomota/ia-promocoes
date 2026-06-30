# Roadmap EmpresaGPT

## Fase 1: Fundacao Arquitetural

Status: iniciada.

- Criar estrutura `empresa_gpt/`.
- Criar documentacao fundadora.
- Auditar modulos atuais.
- Classificar reutilizacao potencial.
- Definir principios de engenharia e seguranca.
- Preservar integralmente o Promogg.

## Fase 2: Contratos e Adaptadores

- Definir contratos minimos para `core`, `security`, `storage`, `analytics` e `monitoring`.
- Criar ADRs para cada extracao proposta.
- Escrever testes de caracterizacao dos modulos candidatos.
- Criar adaptadores sem substituir imports existentes.
- Escolher primeiro modulo de baixo risco para extracao.

## Fase 3: Primeiras Extracoes Controladas

- Extrair utilitarios puros e validadores sem dominio.
- Isolar contratos de erro, request id e configuracao.
- Criar camada de analytics reutilizavel.
- Manter Promogg consumindo adaptadores somente apos equivalencia testada.

## Fase 4: Plataforma Multi-Cliente

- Introduzir conceito formal de tenant/cliente.
- Separar configuracoes de cliente.
- Criar modelo comum de usuario, permissao e auditoria.
- Definir estrutura para novos clientes alem do Promogg.

## Fase 5: Operacao de Plataforma

- Pipeline de testes, validacao de seguranca e deploy por ambiente.
- Monitoramento central.
- Runbooks de incidente.
- Politica de versionamento e compatibilidade.

