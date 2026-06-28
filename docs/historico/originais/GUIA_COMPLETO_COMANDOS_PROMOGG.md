# Guia completo de comandos do Promogg

Gerado para documentar os comandos existentes no projeto. A fonte principal é o CLI oficial:

```bash
python3 ia_promocoes.py <comando> [opções]
```

Opções globais reconhecidas pelo CLI principal:

- `--dry-run`: simula quando o comando oferece modo seguro.
- `--publicar`: permite publicação real apenas em comandos que exigem autorização explícita, como `ciclo-automatico`.
- `--somente-leitura`: usado com `validar` para validar sem mutações operacionais.
- `--visual`: usado por fluxos Playwright/coleta para abrir navegador visual quando suportado.

Regra de ouro: antes de qualquer comando que mexa em banco, curadoria, recuperação, afiliados, site ou publicação, rode primeiro com `--dry-run` quando disponível.

## Comandos oficiais do `ia_promocoes.py`

### Produção e estado do sistema

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py iniciar` | Inicia o worker local de produção. | Alta. Liga automação local. | Só quando o ambiente estiver validado e você quiser rodar o worker. |
| `python3 ia_promocoes.py producao` | Alias/fluxo de produção para iniciar worker. | Alta. Pode iniciar automações. | Preferir `iniciar-producao --dry-run` antes; use com cautela. |
| `python3 ia_promocoes.py online` | Coloca o sistema em ONLINE, atualiza site por estado, tenta publicar e inicia serviços. | Crítica. Muda estado operacional. | Só depois de validação completa e decisão consciente de produção. |
| `python3 ia_promocoes.py iniciar-producao --dry-run` | Executa pré-voo de produção sem iniciar produção. | Crítica para segurança. | Antes de qualquer tentativa de ONLINE/produção. |
| `python3 ia_promocoes.py iniciar-producao` | Executa pré-voo e entra em ONLINE se aprovado. | Crítica. Pode ativar produção. | Apenas quando o pré-voo seco estiver aprovado. |
| `python3 ia_promocoes.py manutencao` | Pausa automações e mantém painel/dados disponíveis. | Crítica para contenção. | Antes de manutenção, investigação, Playwright, recuperação ou alterações. |
| `python3 ia_promocoes.py manutencao-producao` | Alias de manutenção para produção. | Alta. Pausa produção preservando dados. | Quando quiser pausar operação produtiva sem desligar tudo. |
| `python3 ia_promocoes.py offline` | Para serviços automatizados preservando dados. | Alta. Desliga operação. | Quando quiser parar tudo com segurança. |
| `python3 ia_promocoes.py parar-producao` | Para produção com segurança. | Alta. | Quando produção estiver ativa e precisar interromper. |
| `python3 ia_promocoes.py parar` | Solicita parada segura do worker. | Alta. | Para encerrar worker sem matar processo à força. |
| `python3 ia_promocoes.py reiniciar` | Reinicia worker preservando banco e histórico. | Média/alta. | Quando o worker travou ou precisa recarregar configuração. |
| `python3 ia_promocoes.py status` | Mostra estado, serviços, eventos e contagens principais. | Essencial. | Antes e depois de qualquer operação importante. |
| `python3 ia_promocoes.py _worker-producao` | Worker interno de produção. | Interna/crítica. | Não rode manualmente; é chamado por outros comandos. |

### Site, validação e publicação

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py gerar-site` | Gera o site estático local com proteção contra catálogo degradado. | Alta. | Após curadoria/recuperação, antes de validar. |
| `python3 ia_promocoes.py validar` | Valida banco, site, SEO, segurança e assistentes; pode alternar estados temporariamente. | Alta. | Em validação operacional completa. |
| `python3 ia_promocoes.py validar --somente-leitura` | Valida banco, catálogo, páginas, links, imagens e SEO sem mutações operacionais. | Essencial. | Validação padrão segura antes de publicar ou commitar. |
| `python3 ia_promocoes.py servir-site` | Serve o site localmente para teste. | Média. | Para inspeção manual no navegador. |
| `python3 ia_promocoes.py publicar-site` | Copia/prepara `dist_site/` sem fazer push. | Alta. | Quando quiser preparar artefato de publicação local. |
| `python3 ia_promocoes.py subir-site` | Valida e envia site ao GitHub Pages. | Crítica. Faz deploy. | Só com catálogo íntegro, qualidade aprovada e autorização explícita. |
| `python3 ia_promocoes.py publicar` | Valida e publica remotamente quando estado permite. | Crítica. | Só em ONLINE e após validação completa. |
| `python3 ia_promocoes.py auditar-paginas-produto` | Compara catálogo e páginas individuais. | Alta. | Quando houver suspeita de páginas faltando/quebradas. |
| `python3 ia_promocoes.py corrigir-paginas-produto` | Regenera páginas de produto e remove órfãs. | Alta. Altera site local. | Após auditoria indicar divergência. Validar depois. |
| `python3 ia_promocoes.py auditar-qualidade-catalogo` | Audita catálogo público: links, imagens, preços, SEO, categorias e duplicados. | Essencial. | Antes de deploy e após gerar/restaurar site. |

### Ciclo automático e curadoria

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py ciclo-automatico --dry-run` | Simula coleta, histórico, afiliados, curadoria, site, validação, Telegram e bloqueios sem alterar nada. | Essencial. | Primeiro comando para avaliar se o robô pode operar. |
| `python3 ia_promocoes.py ciclo-automatico` | Executa ciclo seguro com backup, mas sem Telegram/deploy real se `--publicar` não for usado. | Crítica. | Quando o dry-run estiver bom e você quiser processar localmente. |
| `python3 ia_promocoes.py ciclo-automatico --publicar` | Tenta ciclo com publicação/deploy somente se todas as travas passarem. | Crítica máxima. | Só quando qualidade, saúde, Git, catálogo e Telegram simulado estiverem 100%. |
| `python3 ia_promocoes.py curadoria-automatica --dry-run` | Simula decisão automática de pendentes/novos. | Essencial. | Antes de aplicar decisões em massa. |
| `python3 ia_promocoes.py curadoria-automatica` | Aplica curadoria automática com backup. | Alta. Altera status de postagens. | Quando o dry-run mostrar decisões seguras. |
| `python3 ia_promocoes.py reprocessar-pendentes --dry-run` | Simula reprocessamento legado de pendentes. | Média. | Para comparar com a curadoria nova. |
| `python3 ia_promocoes.py reprocessar-pendentes` | Reaplica curadoria legado aos pendentes. | Média/alta. | Preferir `curadoria-automatica`; usar se precisar compatibilidade. |
| `python3 ia_promocoes.py reprocessar-pendentes-enriquecido --dry-run` | Simula curadoria com sinais públicos enriquecidos. | Média. | Auditoria/comparação de regras. |
| `python3 ia_promocoes.py reprocessar-pendentes-enriquecido` | Aplica curadoria enriquecida. | Alta. | Só após dry-run. |
| `python3 ia_promocoes.py simular-score` | Compara cenários de score sem alterar banco. | Média/alta. | Para calibrar curadoria sem risco. |
| `python3 ia_promocoes.py calibrar-curadoria` | Aplica calibração segura com backup. | Alta. | Quando quiser recalibrar regras após auditoria. |
| `python3 ia_promocoes.py limpar-titulos` | Saneia títulos com backup. | Média/alta. | Quando títulos estiverem sujos, com preço embutido ou ruins para SEO/Telegram. |

### Coleta Mercado Livre e Playwright

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py coletar` | Executa coleta normal conforme modo configurado. | Alta. Pode alterar banco. | Com sistema preparado, preferencialmente em manutenção controlada. |
| `python3 ia_promocoes.py coletar-confiavel` | Coleta lenta com checkpoint por produto. | Alta. Mais segura para sessão ML. | Quando quiser coleta robusta por lotes. |
| `python3 ia_promocoes.py coletar-confiavel --visual` | Coleta confiável com navegador visível. | Alta. | Para diagnosticar comportamento do Playwright. |
| `python3 ia_promocoes.py retomar-coleta` | Retoma coleta do checkpoint sem publicar. | Alta. | Após pausa/falha de Playwright. |
| `python3 ia_promocoes.py retomar-coleta --visual` | Retoma coleta com navegador visível. | Alta. | Quando precisar observar login/sessão. |
| `python3 ia_promocoes.py testar-coleta-api` | Testa API sem persistir. | Média/alta. | Diagnosticar API Mercado Livre. |
| `python3 ia_promocoes.py testar-coleta-api playwright` | Compara API com Playwright sem persistir. | Média/alta. | Quando API e página divergem. |
| `python3 ia_promocoes.py testar-captura-produto <url>` | Diagnostica captura híbrida de um produto sem persistir. | Média. | Para investigar produto específico. |
| `python3 ia_promocoes.py comparar-captura <url>` | Compara captura legada e híbrida sem persistir. | Média. | Ao refatorar captura ou investigar falhas. |
| `python3 ia_promocoes.py diagnosticar-playwright` | Verifica perfil, sessão e locks. | Essencial para Playwright. | Antes de login/coleta, ou após travas. |
| `python3 ia_promocoes.py reparar-playwright` | Remove locks preservando sessão. | Alta. | Quando perfil ficou bloqueado, sem apagar cookies. |
| `python3 ia_promocoes.py pausar-playwright` | Entra em manutenção, para automações, fecha Chrome for Testing e preserva perfil/checkpoints. | Crítica de segurança. | Antes de mexer no Playwright ou quando detectar logout/instabilidade. |
| `python3 ia_promocoes.py login-mercadolivre` | Abre navegador para login manual e salva sessão em `perfil_mercadolivre`. | Essencial. | Quando sessão expirar ou antes de gerar afiliados/coletar via ML logado. |
| `python3 ia_promocoes.py testar-playwright-sessao` | Verifica se o perfil Mercado Livre está logado, sem coletar. | Essencial. | Após login e antes de coleta/afiliados. |

### Links afiliados `meli.la`

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py gerar-afiliados` | Gera links oficiais `meli.la` pendentes via portal. | Alta. Usa sessão/Playwright. | Após login confirmado; evitar sessões instáveis. |
| `python3 ia_promocoes.py diagnosticar-afiliado` | Resume saúde dos links afiliados. | Média/alta. | Antes/depois de gerar afiliados. |
| `python3 ia_promocoes.py diagnosticar-compartilhar <url>` | Inspeciona botão oficial de compartilhar sem alterar dados. | Média. | Para diagnosticar um produto/link específico. |
| `python3 ia_promocoes.py testar-afiliado <url>` | Testa geração de `meli.la` sem persistir. | Média. | Antes de processar lote grande. |
| `python3 ia_promocoes.py reprocessar-afiliados-falhos --dry-run` | Simula reprocessamento de links falhos/pendentes. | Alta. | Antes de abrir portal para lote. |
| `python3 ia_promocoes.py reprocessar-afiliados-falhos` | Reprocessa apenas links `meli.la` falhos/pendentes. | Alta. | Após dry-run e sessão Playwright testada. |

### Monitoramento, preços, histórico e categorias

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py monitorar-precos` | Atualiza preços e histórico sem publicar. | Alta. Altera banco/histórico. | Em rotina controlada; não marca indisponível por erro temporário. |
| `python3 ia_promocoes.py auditar-precos` | Audita histórico, variações e verificações inconclusivas. | Alta. | Antes/depois do monitoramento. |
| `python3 ia_promocoes.py relatorio-precos` | Mostra resumo do histórico de preços. | Média. | Para visão rápida do histórico. |
| `python3 ia_promocoes.py atualizar-categorias` | Consulta/atualiza categorias por `item_id`. | Média/alta. | Quando há categorias genéricas/vazias. |
| `python3 ia_promocoes.py corrigir-categorias-vazias --dry-run` | Simula correção de categorias vazias/genéricas com fontes seguras. | Alta. | Antes da correção real. |
| `python3 ia_promocoes.py corrigir-categorias-vazias` | Corrige categorias vazias/genéricas no banco. | Alta. | Só após dry-run. |
| `python3 ia_promocoes.py auditar-indisponiveis` | Audita produtos indisponíveis. | Alta. | Quando muitos produtos foram marcados indisponíveis. |
| `python3 ia_promocoes.py recuperar-indisponiveis --dry-run` | Simula recuperação de indisponibilidades técnicas. | Alta. | Antes da recuperação real. |
| `python3 ia_promocoes.py recuperar-indisponiveis` | Recupera indisponibilidades técnicas quando seguro. | Alta. | Após dry-run e validação. |
| `python3 ia_promocoes.py recuperar-banco-catalogo --dry-run` | Simula recuperação do banco usando catálogo restaurado/fontes permitidas. | Crítica. | Antes de mexer em status/elegibilidade do banco. |
| `python3 ia_promocoes.py recuperar-banco-catalogo` | Recupera elegibilidade/status do banco com backup e regras de segurança. | Crítica. | Só quando dry-run estiver aprovado. |

### Duplicados, base e restauração

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py auditar-duplicados` | Audita `item_id` duplicados e escolhe registro mais íntegro sem apagar. | Alta. | Quando qualidade apontar duplicados. |
| `python3 ia_promocoes.py corrigir-duplicados --dry-run` | Simula ocultação de duplicados inferiores. | Alta. | Antes da correção real. |
| `python3 ia_promocoes.py corrigir-duplicados` | Marca duplicados inferiores como `duplicado_oculto`, sem apagar histórico. | Alta. | Após dry-run. |
| `python3 ia_promocoes.py auditar-base` | Resume saúde da base. | Alta. | Diagnóstico geral do SQLite. |
| `python3 ia_promocoes.py auditar-sistema` | Audita arquitetura, segurança, banco, histórico, catálogo e automação sem publicar. | Alta. | Em auditorias gerais antes de grandes mudanças. |
| `python3 ia_promocoes.py reconstruir-base --dry-run` | Simula reconstrução da base com proteção. | Crítica. | Antes de reconstrução real. |
| `python3 ia_promocoes.py reconstruir-base` | Reconstrói base com backup e proteção. | Crítica. | Só em manutenção e após dry-run aprovado. |
| `python3 ia_promocoes.py restaurar-catalogo-valido --dry-run` | Simula escolha/restauração do melhor catálogo estático. | Crítica. | Antes de restaurar site/dist. |
| `python3 ia_promocoes.py restaurar-catalogo-valido` | Restaura catálogo estático sem tocar no banco. | Crítica. | Quando catálogo público foi degradado. |

### OAuth Mercado Livre e API

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py meli-auth` | Inicia OAuth Mercado Livre. | Alta. | Quando precisar configurar/autenticar API. |
| `python3 ia_promocoes.py meli-testar-token` | Testa token sem exibi-lo. | Alta. | Ao diagnosticar 401/403. |
| `python3 ia_promocoes.py meli-refresh-token` | Renova token local. | Alta. | Quando token expirar ou `/users/me` falhar por token. |
| `python3 ia_promocoes.py meli-auditar-api` | Audita API ML, 401 e refresh automático sem expor tokens. | Alta. | Após erros API, antes de coleta/monitoramento. |

### Telegram e publicação de ofertas

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py simular` | Simula próxima publicação Telegram e atualiza material manual. | Média/alta. | Antes de publicar uma oferta. |
| `python3 ia_promocoes.py publicar-um` | Publica uma oferta elegível no Telegram. | Crítica. Envia Telegram real. | Só quando produção estiver autorizada e fila validada. |

### IA, assistente e revisora

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py perguntar "<pergunta>"` | Consulta local de preços/histórico. | Média. | Para análise consultiva baseada no banco. |
| `python3 ia_promocoes.py treinar-memoria` | Atualiza memória local/resumos sem treinar modelo externo. | Média. | Após grandes mudanças de catálogo/histórico. |
| `python3 ia_promocoes.py revisar-ofertas` | Gera pareceres da IA revisora. | Média. | Quando houver pendentes relevantes. |
| `python3 ia_promocoes.py treinar-revisora` | Atualiza estatísticas da revisora. | Média. | Após feedbacks/decisões suficientes. |

### Analytics, saúde e relatórios

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py analytics-teste` | Registra clique de teste local sem dados pessoais. | Baixa/média. | Para validar analytics local. |
| `python3 ia_promocoes.py analytics-status` | Mostra métricas e configuração do endpoint. | Média. | Diagnóstico de analytics. |
| `python3 ia_promocoes.py saude` | Mostra saúde resumida do sistema. | Essencial. | Antes/depois de operações. |
| `python3 ia_promocoes.py saude-detalhada` | Mostra críticos, alertas, avisos e eventos. | Alta. | Quando `status` indicar atenção/erro. |
| `python3 ia_promocoes.py relatorio` | Mostra resumo operacional geral. | Média. | Check diário. |
| `python3 ia_promocoes.py relatorio-operacional` | Mostra resumo operacional diário. | Média. | Rotina de acompanhamento. |

### Backup, manutenção, painel e documentação

| Comando | O que faz | Importância | Quando rodar |
|---|---|---|---|
| `python3 ia_promocoes.py backup` | Cria backup operacional seguro. | Essencial. | Antes de qualquer operação real. |
| `python3 ia_promocoes.py restaurar` | Lista backups disponíveis. | Alta. | Antes de decidir restauração. |
| `python3 ia_promocoes.py limpar-seguro` | Coloca candidatos em quarentena segura. | Média/alta. | Só após auditoria de limpeza. |
| `python3 ia_promocoes.py mapa` | Exibe mapa do projeto. | Baixa/média. | Para orientação técnica. |
| `python3 ia_promocoes.py painel` | Abre painel Streamlit. | Alta para operação manual. | Para acompanhar filas, saúde e relatórios. |
| `python3 ia_promocoes.py comandos` | Lista ajuda organizada dos comandos. | Baixa/média. | Quando esquecer nomes de comandos. |

## Scripts diretos avançados

Estes scripts têm `if __name__ == "__main__"` ou parser próprio. Sempre prefira o CLI oficial `ia_promocoes.py`, salvo quando você souber exatamente por que precisa chamar o script direto.

| Script/comando direto | O que faz | Importância | Recomendação |
|---|---|---|---|
| `python3 scheduler.py --once` | Executa um ciclo do scheduler e encerra. | Alta. | Preferir `ciclo-automatico --dry-run` ou comandos master. |
| `python3 scheduler.py --publicar` | Permite publicação no ciclo do scheduler. | Crítica. | Evitar manualmente; pode publicar. |
| `python3 scheduler.py --publicar-um` | Publica um post pendente pelo scheduler. | Crítica. | Preferir `ia_promocoes.py publicar-um` com cuidado. |
| `python3 scheduler.py --dry-run` | Simula publicação no scheduler. | Média. | Útil para diagnóstico legado. |
| `python3 scheduler.py --sem-publicar` | Executa sem publicar no Telegram. | Alta. | Usar apenas para compatibilidade. |
| `python3 publicador_telegram.py` | Publica uma oferta elegível diretamente. | Crítica. | Evitar; use `simular` antes e prefira CLI oficial. |
| `python3 login_ml.py` | Login manual ML via Playwright. | Alta. | Preferir `ia_promocoes.py login-mercadolivre`. |
| `python3 gerar_site.py` | Gera site diretamente. | Alta. | Preferir `ia_promocoes.py gerar-site` porque tem proteção. |
| `python3 monitor_precos.py` | Força monitoramento diário de preços. | Alta. | Preferir `ia_promocoes.py monitorar-precos`. |
| `python3 fila_postagens.py` | Gera fila de postagens diretamente. | Alta. | Preferir `curadoria-automatica`/`ciclo-automatico`. |
| `python3 banco.py` | Inicializa/valida estrutura do banco. | Média. | Usar só para diagnóstico técnico. |
| `python3 saude_sistema.py` | Imprime relatório de saúde. | Média. | Preferir `ia_promocoes.py saude` ou `saude-detalhada`. |
| `python3 promogg_assistente.py perguntar "<pergunta>"` | Consulta assistente local. | Média. | Preferir `ia_promocoes.py perguntar`. |
| `python3 servidor_site.py --host 127.0.0.1 --porta 8000` | Serve site local. | Média. | Preferir `ia_promocoes.py servir-site`. |
| `python3 consulta_precos.py buscar "<termo>"` | Busca preços no histórico local. | Média. | Útil para investigação de preços. |
| `python3 consulta_precos.py menor-preco "<termo>"` | Consulta menor preço por termo. | Média. | Usar para auditoria local de histórico. |
| `python3 consulta_precos.py historico MLB...` | Mostra histórico por item_id. | Média. | Usar para diagnóstico de produto específico. |
| `python3 consulta_precos.py relatorio "<termo>"` | Gera relatório local por termo. | Média. | Usar quando quiser visão por produto/categoria. |
| `python3 trocar_token_meli.py <code>` | Troca código OAuth por tokens locais. | Alta/confidencial. | Use com cuidado; não exponha código/tokens. |
| `python3 publicar_site_git.py --mensagem "..."` | Publica `dist_site/` no GitHub Pages. | Crítica. | Preferir `subir-site`; só usar se souber o fluxo Git. |
| `python3 deploy_site.py local --destino dist_site` | Copia `site/` para destino local. | Alta. | Útil para preparar artefato sem push. |
| `python3 deploy_site.py github-pages --destino <pasta>` | Copia site para pasta/repo GitHub Pages. | Crítica. | Usar apenas com validação aprovada. |
| `python3 deploy_site.py github-actions` | Gera `dist_site/`, cria CNAME, commita e envia ao GitHub. | Crítica máxima. | Evitar manualmente; faz commit/push. |
| `python3 deploy_site.py vps` | Reserva para publicação futura em VPS. | Baixa. | Não usar salvo implementação futura. |
| `python3 servidor_analytics.py` | Inicia servidor local de analytics. | Média. | Usar quando quiser analytics ativo localmente. |
| `python3 coletor_mercadolivre.py` | Coletor Mercado Livre legado/direto. | Alta. | Preferir `coletar`/`coletar-confiavel`. |
| `python3 agente_ofertas.py` | Agente legado de ofertas. | Média/alta. | Usar só se souber o fluxo legado. |

## Sequências recomendadas

### Check seguro diário

```bash
python3 ia_promocoes.py status
python3 ia_promocoes.py validar --somente-leitura
python3 ia_promocoes.py auditar-qualidade-catalogo
python3 ia_promocoes.py ciclo-automatico --dry-run
```

### Rodar automação local sem publicar

```bash
python3 ia_promocoes.py backup
python3 ia_promocoes.py ciclo-automatico --dry-run
python3 ia_promocoes.py ciclo-automatico
python3 ia_promocoes.py validar --somente-leitura
python3 ia_promocoes.py auditar-qualidade-catalogo
```

### Playwright seguro

```bash
python3 ia_promocoes.py pausar-playwright
python3 ia_promocoes.py diagnosticar-playwright
python3 ia_promocoes.py login-mercadolivre
python3 ia_promocoes.py testar-playwright-sessao
python3 ia_promocoes.py retomar-coleta
```

### Antes de qualquer deploy/publicação

```bash
python3 ia_promocoes.py status
python3 ia_promocoes.py validar --somente-leitura
python3 ia_promocoes.py auditar-qualidade-catalogo
python3 ia_promocoes.py ciclo-automatico --dry-run
```

Só considere `subir-site`, `publicar`, `online`, `publicar-um` ou `ciclo-automatico --publicar` se todos os relatórios estiverem sem críticos e sem ressalvas impeditivas.

## Comandos de maior risco

Evite rodar por impulso:

- `online`
- `iniciar-producao`
- `subir-site`
- `publicar`
- `publicar-um`
- `ciclo-automatico --publicar`
- `scheduler.py --publicar`
- `publicador_telegram.py`
- `deploy_site.py github-actions`

Esses comandos podem ativar produção, publicar site, enviar Telegram, commitar ou fazer push.

