# Relatório de Teste Real Completo - Promogg

- Data/hora: 2026-06-19 20:12:51
- Estado inicial: MANUTENCAO
- Estado final: MANUTENCAO (MASTER MANUTENCAO acionado)
- Backup operacional: backups/operacao/promogg_backup_20260619_200916.zip
- Snapshot de homologação: backups/teste_real/promogg_pre_teste_20260619_200916.tar.gz

## Ambiente
- Python 3.12.10; dependências sem conflitos; Playwright 1.60.0.
- OAuth: HTTP 200 em /users/me (dados sensíveis não exibidos).
- API busca: 403; bloqueada até 2026-06-20 02:04:04.
- Modo de coleta: auto; fallback Playwright previsto.
- Git remoto origin configurado; .env, banco.db, venv e perfil_mercadolivre ignorados.

## Coleta e Monitoramento
- Coleta real tentada em manutenção: BLOQUEADA.
- Motivo: o perfil perfil_mercadolivre está em uso por outra sessão do Chrome; Playwright recusou abrir contexto persistente.
- Produtos novos: 0; duplicados processados: 0; nenhuma oferta persistida nesta tentativa.
- Monitoramento de preços: NÃO EXECUTADO para não repetir marcações de indisponibilidade na base antiga sem uma coleta válida.

## Banco e Curadoria
- Produtos totais: 72
- Histórico de preços: 142
- Postagens totais: 69
- aprovado_auto: 41
- aprovado_manual: 1
- pendente_revisao: 1
- rejeitado: 0
- publicado: 26
- indisponivel (produtos): 70
- IA revisora: executada para 1 oferta; apenas parecer, sem alteração automática de publicação.
- Memória consultiva: atualizada para 72 produtos; Ollama indisponível, fallback por regras funcionou.

## Site, Analytics e Telegram
- Ofertas públicas geradas: 2
- Páginas de produto geradas: 2
- Validação consolidada: APROVADA.
- SEO/sitemap/robots e páginas institucionais: validados pelo comando validar.
- Analytics: tabela cliques existente; 0 cliques; nenhuma informação pessoal coletada.
- Telegram: simulação DRY-RUN concluída; nenhuma mensagem enviada.

## Deploy
- Deploy GitHub Pages: NÃO EXECUTADO.
- Razão: a homologação de coleta não foi concluída; não é seguro publicar um catálogo sem uma coleta válida.
- URL pública preservada: https://promogg.com.br/

## Erros recentes
- 2026-06-19 19:26:15 [monitor_precos] Falha ao verificar MLB6664766808: API respondeu HTTP 403
- 2026-06-19 19:26:07 [monitor_precos] Falha ao verificar MLB779362: item_id inválido: MLB779362
- 2026-06-19 19:06:37 [monitor_precos] Falha ao verificar MLB45532516: API respondeu HTTP 403; configure MELI_ACCESS_TOKEN via OAuth
- 2026-06-19 19:06:36 [monitor_precos] Falha ao verificar MLB83332404511: API respondeu HTTP 403; configure MELI_ACCESS_TOKEN via OAuth
- 2026-06-19 19:06:35 [monitor_precos] Falha ao verificar MLB110805634459: API respondeu HTTP 403; configure MELI_ACCESS_TOKEN via OAuth
- 2026-06-19 19:06:35 [monitor_precos] Falha ao verificar MLB93955563541: API respondeu HTTP 403; configure MELI_ACCESS_TOKEN via OAuth
- 2026-06-19 19:06:35 [monitor_precos] Falha ao verificar MLB85461139997: API respondeu HTTP 403; configure MELI_ACCESS_TOKEN via OAuth
- 2026-06-19 18:48:14 [monitor_precos] Falha ao verificar MLB45532516: API respondeu HTTP 403; configure MELI_ACCESS_TOKEN via OAuth

## Avisos recentes
- 2026-06-19 20:05:41 [scheduler] Ciclo automático pausado pelo estado mestre
- 2026-06-19 20:04:04 [coleta_api] Busca API indisponível (HTTP 403); Playwright será usado até 2026-06-20 02:04:04
- 2026-06-19 19:48:42 [scheduler] Ciclo automático pausado pelo estado mestre
- 2026-06-19 19:06:37 [monitor_precos] Monitoramento incompleto; será tentado novamente no próximo ciclo.
- 2026-06-19 19:06:37 [monitor_precos] Monitoramento interrompido após 5 falhas consecutivas na API; a próxima execução retomará os itens restantes.
- 2026-06-19 18:48:14 [monitor_precos] Monitoramento incompleto; será tentado novamente no próximo ciclo.
- 2026-06-19 18:48:14 [monitor_precos] Monitoramento interrompido após 5 falhas consecutivas na API; a próxima execução retomará os itens restantes.
- 2026-06-19 18:00:01 [monitor_precos] Monitoramento incompleto; será tentado novamente no próximo ciclo.

## Recomendação antes de ONLINE
- NÃO ativar ONLINE ainda.
- Feche somente a janela/processo do Chrome que usa perfil_mercadolivre, confirme que o perfil está liberado e execute novamente python3 ia_promocoes.py coletar.
- Depois de uma coleta concluída, executar monitorar-precos, gerar-site, validar, simular e subir-site; então revisar o status antes de ONLINE.
