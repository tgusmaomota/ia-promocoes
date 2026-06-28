# Relatório de Limpeza de Código Promogg

- Data: 2026-06-26
- Escopo: ativação segura da publicação automática local, auditoria estrutural, quarentena conservadora e correção de UX da paginação.
- Restrições respeitadas: sem deploy real, sem Telegram real de ofertas, sem `supervisor-loop`, sem `ONLINE`, sem exclusão de banco, histórico, backups, perfil Mercado Livre ou `.env`.

## Ajustes de configuração

- `.env`: `PROMOGG_SUPERVISOR_PUBLICAR` ajustado para `true`.
- `.env`: `PROMOGG_SUPERVISOR_TELEGRAM_ALERTAS` ajustado para `true`.
- `.env.example`: mantido conservador com `PROMOGG_SUPERVISOR_PUBLICAR=false`.
- Tokens, cookies e demais segredos não foram exibidos.

## Correção de UX

- Fonte corrigida: `gerar_site.py`.
- Artefatos estáticos corrigidos: `site/app.js` e `dist_site/app.js`.
- Comportamento novo: ao mudar página, busca, categoria ou ordenação, a tela rola suavemente para o topo da seção `#ofertas`.
- O carregamento inicial do catálogo não força rolagem.
- A correção permanece após nova execução de `gerar-site`, pois foi aplicada no gerador.

## Arquivos movidos para quarentena nesta rodada

| Arquivo/pasta | Destino | Motivo | Risco | Pode apagar futuramente |
|---|---|---|---|---|
| `__pycache__/` | `quarentena_remocao/__pycache___antes_limpeza_2026-06-26/` | Cache Python gerado automaticamente | Baixo | Sim, após validações limpas |

## Arquivos mantidos

Foram preservados os módulos e artefatos principais:

- banco SQLite e históricos;
- `site/` e `dist_site/`;
- `perfil_mercadolivre`;
- `backups/`;
- `.env`;
- supervisor automático;
- ciclo automático;
- curadoria automática;
- Playwright;
- OAuth Mercado Livre;
- Telegram/alertas;
- painel;
- analytics;
- geração de site;
- recuperação de banco/catálogo;
- validações e auditorias.

## Candidatos a revisão futura, não movidos

Estes arquivos apareceram sem referência textual direta na varredura local, mas não foram movidos porque podem ser ferramentas manuais, diagnósticas ou legadas ainda úteis:

| Arquivo | Observação | Decisão |
|---|---|---|
| `buscador.py` | Busca direta na API Mercado Livre; pode servir para testes ou fallback manual | manter |
| `dashboard_receita.py` | Dashboard Streamlit manual de receita | manter |
| `extrator.py` | Extrator simples de dados de produto por link | manter |
| `importar_afiliados.py` | Importação/curadoria de CSV legado; pode ser usado em recuperação | manter |
| `iniciar_ia.py` | Wrapper operacional para iniciar comando oficial | manter |

## Comandos oficiais preservados

A listagem `python3 ia_promocoes.py comandos` deve continuar expondo os fluxos atuais, incluindo:

- `supervisor`
- `supervisor-loop`
- `testar-alerta-telegram`
- `ciclo-automatico`
- `preparar-publicacao`
- `curadoria-automatica`
- `login-mercadolivre`
- `pausar-playwright`
- `retomar-coleta`
- `testar-playwright-sessao`
- `meli-auditar-api`
- `auditar-qualidade-catalogo`
- `validar --somente-leitura`

## Risco residual

- O Git ainda pode mostrar alterações operacionais geradas por validações anteriores e atuais.
- Publicação automática ficou configurada no `.env`, mas a publicação real segue protegida por validação, Git, catálogo, qualidade e supervisor.
- Nenhum arquivo de código foi removido porque a prioridade desta rodada foi segurança e reversibilidade.

## Conclusão

Limpeza conservadora concluída. O projeto está mais seguro para operar porque:

- `.env` local permite homologar publicação automática;
- `.env.example` permanece seguro por padrão;
- a UX de paginação foi corrigida na fonte e nos artefatos atuais;
- cache Python foi colocado em quarentena em vez de apagado;
- módulos incertos foram preservados e documentados para revisão futura.
