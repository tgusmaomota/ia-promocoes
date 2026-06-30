# Relatorio de Arquitetura EmpresaGPT

Data: 2026-06-30

## Escopo

Auditoria arquitetural inicial do repositorio atual para iniciar a plataforma EmpresaGPT sem alterar comportamento do Promogg.

## Resultado Executivo

O Promogg ja contem varios blocos de plataforma embrionaria: API read-only, auth experimental isolada, RBAC experimental, validadores de seguranca, middleware de request id, catalogo publico sanitizado, auditorias e monitoramento. Ao mesmo tempo, grande parte do repositorio e dominio especifico do Promogg: Mercado Livre, afiliados, site publico, painel, supervisor, coleta, curadoria de ofertas e publicacao.

Recomendacao: manter tudo no lugar na Fase 1 e iniciar a Fase 2 por contratos/testes para `api_promogg/security`, `api_promogg/auth`, `api_promogg/errors`, `api_promogg/middleware`, analytics e validadores.

## Arvore da Plataforma

```text
empresa_gpt/
├── ai/
│   └── README.md
├── analytics/
│   └── README.md
├── core/
│   └── README.md
├── deployment/
│   └── README.md
├── docs/
│   └── README.md
├── integrations/
│   └── README.md
├── monitoring/
│   └── README.md
├── security/
│   └── README.md
├── services/
│   └── README.md
├── shared/
│   └── README.md
└── storage/
    └── README.md
```

## Classificacao dos Modulos

### Core EmpresaGPT

| Modulo | Motivo |
|---|---|
| `api_promogg/errors.py` | Padrao reutilizavel de erro e payload com request id. |
| `api_promogg/middleware.py` | Middleware transversal de request id. |
| `api_promogg/schemas.py` | Modelo inicial de envelopes e respostas padronizadas. |
| `api_promogg/security/constants.py` | Vocabulário central de seguranca, permissoes, headers e env vars. |
| `api_promogg/security/settings.py` | Configuracao central por ambiente e flags. |
| `api_promogg/security/feature_flags.py` | Interface unica para features de auth/RBAC/MFA/JWT. |
| `api_promogg/security/validators.py` | Validadores genericos de e-mail, senha, origem, host e entrada. |
| `api_promogg/security/csrf.py` | Infraestrutura generica de CSRF. |
| `api_promogg/security/origin.py` | Validacao generica de origem, host e referer. |
| `api_promogg/security/session_security.py` | Contratos reutilizaveis de sessao e anti-session-fixation. |
| `api_promogg/auth/password.py` | Hash/verificacao de senha com potencial de plataforma. |
| `api_promogg/auth/tokens.py` | Tokens opacos e hash de token reutilizaveis. |
| `api_promogg/auth/credentials.py` | Contratos de credenciais. |
| `api_promogg/auth/cookies.py` | Especificacoes de cookies seguros. |
| `api_promogg/auth/audit.py` | Sanitizacao de eventos de auditoria. |
| `api_promogg/auth/rbac.py` | Autorizador e helpers RBAC reutilizaveis depois de desacoplamento. |
| `api_promogg/auth/models.py` | Entidades de identidade com potencial de plataforma. |
| `api_promogg/auth/migrations.py` | Schema experimental de auth, candidato a base de migracoes. |
| `api_promogg/auth/repository.py` | Repositorio experimental de auth. |
| `api_promogg/auth/service.py` | Servico experimental de auth. |
| `api_promogg/auth/auth_facade.py` | Fachada de credenciais. |
| `api_promogg/auth/jwt_provider.py` | Provider JWT experimental. |
| `api_promogg/auth/db.py` | Conexao isolada para banco de auth. |

### Compartilhavel no Futuro

| Modulo | Motivo |
|---|---|
| `api_promogg/main.py` | Estrutura FastAPI reutilizavel, mas ainda nomeada e configurada para Promogg. |
| `api_promogg/config.py` | Config de API reutilizavel depois de generalizacao de nomes. |
| `api_promogg/catalogo.py` | Padrao de leitura publica read-only, mas acoplado a ofertas. |
| `api_promogg/routers/health.py` | Health check reutilizavel com ajustes de plataforma. |
| `api_promogg/routers/ofertas.py` | Exemplo de router read-only de cliente. |
| `api_promogg/routers/auth.py` | Router experimental reutilizavel depois de estabilizar contratos. |
| `analytics_promogg.py` | Logica de status/relatorio de analytics pode virar camada generica. |
| `servidor_analytics.py` | Coleta HTTP simples de analytics pode virar adaptador. |
| `analytics_cloudflare_worker.js` | Worker Cloudflare reutilizavel com parametrizacao. |
| `analytics_cloudflare_d1.sql` | Schema inicial de analytics adaptavel. |
| `auditoria_sistema.py` | Auditoria geral pode virar ferramenta de plataforma. |
| `seguranca_publicacao.py` | Scanner de publicacao segura reutilizavel. |
| `catalogo_integridade.py` | Padrao de protecao contra publicacao vazia aplicavel a clientes. |
| `validar_catalogo_publico.py` | Validador de artefato publico pode virar contrato por cliente. |
| `deploy_site.py` | Fluxo de deploy seguro reutilizavel com adaptadores. |
| `homologacao_publicacao.py` | Checklist pre-publicacao reutilizavel. |
| `saude_sistema.py` | Modelo de saude operacional reaproveitavel. |
| `alertas_telegram.py` | Alertas podem virar integracao generica de mensageria. |
| `csv_utils.py` | Utilitarios CSV reutilizaveis se mantidos sem dominio. |
| `item_utils.py` | Parsing de identificadores pode virar utilitario se generalizado. |
| `saneamento_ofertas.py` | Saneamento de texto/preco reaproveitavel com contrato generico. |
| `metricas_historico.py` | Metricas historicas podem virar analytics/storage. |
| `estado_sistema.py` | Estado operacional pode virar modelo comum de runtime. |
| `servicos_promogg.py` | Controle de servicos e PIDs reaproveitavel apos remover nomes Promogg. |
| `servidor_site.py` | Servidor estatico local reaproveitavel. |
| `scheduler.py` | Loop agendado simples pode virar worker scheduler generico. |
| `gerador_texto.py` | Chamada de IA/prompts pode migrar para `ai` com provider configuravel. |
| `ia_revisora.py` | Revisao por IA e heuristicas podem virar servico de avaliacao. |
| `promogg_assistente.py` | Assistente com memoria e regras pode inspirar modulo `ai`, mas e acoplado a ofertas. |
| `qualidade_catalogo.py` | Indicadores de qualidade podem virar framework de qualidade por cliente. |

### Exclusivo do Promogg

| Modulo | Motivo |
|---|---|
| `ia_promocoes.py` | CLI principal e orquestracao operacional do Promogg. |
| `banco.py` | Banco operacional SQLite do Promogg e tabelas de ofertas/postagens. |
| `painel.py` | Painel Streamlit operacional do Promogg. |
| `painel_remoto.py` | Fluxo remoto/admin especifico do Promogg. |
| `supervisor_promogg.py` | Supervisor de operacao Promogg. |
| `producao_promogg.py` | Producao Promogg. |
| `operacao_sistema.py` | Operacao local do sistema atual. |
| `gerar_site.py` | Gerador local do site Promogg. |
| `gerar_site_publico.py` | Gerador publico do site Promogg. |
| `publicar_site_git.py` | Publicacao do site Promogg. |
| `agente_site.py` | Agente especifico do site Promogg. |
| `agente_publicador.py` | Publicador especifico do fluxo atual. |
| `publicador_telegram.py` | Publicacao Telegram do Promogg. |
| `agente_telegram.py` | Automacao Telegram especifica. |
| `fila_postagens.py` | Fila de postagens de ofertas. |
| `controle_ofertas.py` | Aprovacao/edicao/rejeicao de ofertas. |
| `schema_posts.py` | CSV de postagens do Promogg. |
| `curadoria_automatica.py` | Curadoria de ofertas Promogg. |
| `agente_curadoria.py` | Curadoria especifica de produto/oferta. |
| `auditoria_score.py` | Auditoria de score de ofertas. |
| `calibracao_curadoria.py` | Calibracao de curadoria Promogg. |
| `analisador_promocao.py` | Analise de promocao/oferta. |
| `analisador.py` | Heuristica simples de promocao. |
| `coletor_mercadolivre.py` | Integracao Mercado Livre especifica. |
| `coletor_mercadolivre_api.py` | API Mercado Livre especifica. |
| `mercadolivre_api.py` | Cliente Mercado Livre. |
| `meli_oauth.py` | OAuth Mercado Livre. |
| `login_ml.py` | Login Mercado Livre local. |
| `trocar_code.py` | Troca de code Mercado Livre. |
| `trocar_token_meli.py` | Troca de token Mercado Livre. |
| `gerar_token.py` | Utilitario de token do fluxo atual. |
| `playwright_perfil.py` | Perfil Playwright ligado a operacao ML. |
| `captura_hibrida.py` | Captura produto Mercado Livre. |
| `coleta_confiavel.py` | Coleta confiavel ML/Promogg. |
| `agente_ofertas.py` | Coleta/extracao de ofertas. |
| `agente_afiliado.py` | Afiliados no fluxo atual. |
| `gerador_afiliados_oficial.py` | Geracao de links oficiais ML. |
| `gerador_link_mercadolivre.py` | Link afiliado Mercado Livre. |
| `auditoria_afiliados.py` | Auditoria de afiliados do Promogg. |
| `importar_afiliados.py` | Importacao de afiliados. |
| `atualizar_categorias.py` | Categorias de produtos/ofertas Promogg. |
| `integridade_paginas_produto.py` | Integridade de paginas de produto Promogg. |
| `integridade_precos.py` | Auditoria de precos de ofertas. |
| `consulta_precos.py` | Consulta historica de precos Promogg. |
| `monitor_precos.py` | Monitoramento de precos Promogg. |
| `dashboard_receita.py` | Dashboard de receita do dominio atual. |
| `buscador.py` | Busca em produtos/ofertas. |
| `extrator.py` | Extracao de item/link no dominio atual. |
| `enriquecimento_pagina_ml.py` | Enriquecimento por pagina Mercado Livre. |

### Legado

| Modulo | Motivo |
|---|---|
| `app.py` | Entrada simples antiga com persistencia de links; parece substituida por fluxo atual. |
| `coletor.py` | Implementacao minima antiga de afiliado. |
| `corrigir_posts.py` | Script pontual de correcao. |
| `iniciar_ia.py` | Entrada antiga/simples para iniciar automacao. |
| `limpar_invalidos.py` | Script pequeno de limpeza pontual. |
| `limpar_titulos.py` | Limpeza operacional especifica, possivelmente substituivel por saneamento. |
| `agente_publicador.py` | Muito pequeno e provavelmente historico; confirmar uso antes de remover. |
| `agente_site.py` | Script especifico simples; confirmar uso. |

### Candidato a Quarentena

| Modulo | Motivo |
|---|---|
| `limpeza_segura.py` | Operacao de limpeza deve ficar sob controle/auditoria antes de reutilizacao. |
| `correcoes_pos_reconstrucao.py` | Script grande de correcao pos-incidente/reconstrucao. |
| `recuperacao_base.py` | Recuperacao operacional pontual. |
| `recuperacao_banco_catalogo.py` | Recuperacao a partir de catalogo; alto impacto em dados. |
| `recuperacao_indisponiveis.py` | Recuperacao especifica de indisponiveis. |
| `restauracao_catalogo.py` | Restauracao de catalogo; risco operacional. |
| `reprocessar_pendentes.py` | Reprocessamento operacional. |
| `reprocessar_pendentes_enriquecido.py` | Reprocessamento operacional enriquecido. |
| `ciclo_automatico.py` | Orquestracao ampla; manter intacta ate haver testes fortes. |
| `homologacao_publicacao.py` | Compartilhavel, mas atua sobre publicacao; exigir contrato antes. |
| `deploy_site.py` | Compartilhavel, mas com potencial destrutivo via Git/deploy; migrar com cautela. |

## Diretorios e Artefatos

| Caminho | Classificacao | Observacao |
|---|---|---|
| `api_promogg/` | Compartilhavel/Core em partes | Base mais proxima da futura plataforma. |
| `docs/` | Exclusivo Promogg + historico | Manter documentacao operacional do cliente. |
| `tests/` | Compartilhavel no futuro | Testes de auth/API ajudam na extracao. |
| `catalogo_publico/` | Exclusivo Promogg | Artefato publico sanitizado do cliente. |
| `site/`, `dist_site/` | Exclusivo Promogg | Artefatos de site; nao alterar na Fase 1. |
| `quarentena_v1/`, `quarentena_remocao/` | Candidato a quarentena | Preservar para auditoria historica. |
| `backups/`, `logs/`, perfis de navegador | Operacional local | Nao versionar, nao migrar. |

## Oportunidades de Reutilizacao

- Padrao de API read-only com envelopes, erros e request id.
- Auth experimental isolada com DB proprio.
- RBAC, cookies, CSRF, validacao de origem e settings por ambiente.
- Auditoria sanitizada.
- Analytics publico sem identificador pessoal.
- Validador de artefato publico e bloqueio de publicacao vazia.
- Saude operacional e alertas.
- Utilitarios puros de CSV, parsing, saneamento e formatacao.
- Assistente com memoria e resposta por regras como base para `empresa_gpt/ai`.

## Riscos Tecnicos

- `ia_promocoes.py`, `banco.py` e `gerar_site.py` concentram muitas responsabilidades.
- Mistura de scripts pontuais, operacao diaria e modulos candidatos a plataforma na raiz.
- Nomes e contratos ainda acoplados ao Promogg.
- Auth/RBAC ainda experimental e protegido por flags; nao deve ser promovido sem revisao.
- Operacoes de recuperacao, deploy e reprocessamento podem alterar dados ou publicacao se executadas indevidamente.
- Ausencia de fronteira formal cliente/plataforma ate a Fase 2.

## Plano da Fase 2

1. Criar ADRs para os primeiros contratos de plataforma.
2. Definir contratos de `core`, `security`, `storage`, `analytics` e `monitoring`.
3. Escrever testes de caracterizacao para candidatos antes de extrair.
4. Criar adaptadores EmpresaGPT sem alterar imports do Promogg.
5. Escolher uma extracao de baixo risco, preferencialmente validadores ou envelopes de erro.
6. Medir impacto com testes existentes.
7. So depois considerar migracao gradual de chamadas.

