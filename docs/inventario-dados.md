# Inventário de Dados

Este documento classifica os dados do Promogg para preparar autenticação, autorização, auditoria, retenção, criptografia e operação segura.

## Classes de Dados

| Classe | Pode ir para Git? | Criptografia necessária | Retenção recomendada |
|---|---|---|---|
| Público | Sim, se sanitizado. | Não obrigatória. | Enquanto útil ao site. |
| Operacional | Não, salvo documentação sanitizada. | Recomendada em repouso. | 90 a 365 dias, conforme utilidade. |
| Sensível | Não. | Obrigatória em produção. | Menor tempo necessário. |
| Secret | Nunca. | Obrigatória, preferir Secret Manager. | Rotação periódica e após incidente. |
| Log | Não, exceto exemplo sanitizado. | Recomendada; obrigatória se contiver dado sensível. | 30 a 180 dias. |
| Backup | Não. | Obrigatória. | Política por geração: diária/semanal/mensal. |

## Inventário

| Dado | Classe | Onde vive hoje | Git | Retenção | Criptografia | Risco de vazamento | Proteção atual | Proteção futura |
|---|---|---|---|---|---|---|---|---|
| Catálogo público | Público | `catalogo_publico/ofertas.json` | Sim | Enquanto publicado | Não obrigatória | Baixo/Médio: adulteração pode afetar reputação. | Validação de contrato e bloqueio de campos sensíveis. | Assinatura/hash, revisão e trilha por versão. |
| Site gerado | Público | `site/`, `dist_site/`, GitHub Pages | Não para gerados locais; sim para Pages via artefato | Última versão e rollback | Não obrigatória | Médio: conteúdo malicioso ou incorreto. | Geração pública sem secrets. | CSP forte, validação de release, rollback. |
| Ofertas operacionais | Operacional | `banco.db`, tabelas de produtos/postagens | Não | 365 dias ou conforme valor histórico | Sim em produção | Alto: expõe estratégia, histórico e operação. | SQLite local ignorado. | PostgreSQL criptografado, RBAC, backups criptografados. |
| Histórico de preços | Operacional | `banco.db` | Não | 365 dias ou mais se agregado | Sim em produção | Médio/Alto: inteligência comercial. | SQLite local ignorado. | Agregação, retenção definida, criptografia. |
| Observações internas | Sensível | `banco.db`, postagens/logs | Não | 180 a 365 dias | Sim | Alto: decisões internas e contexto operacional. | Não entra no catálogo público. | RBAC, auditoria, minimização. |
| Logs operacionais | Log | `logs/`, tabela `logs`, `sistema_eventos` | Não | 30 a 180 dias | Recomendada | Médio/Alto: pode revelar fluxo ou erro sensível. | `.gitignore`, sanitização parcial em eventos. | Sanitização central, SIEM, retenção e mascaramento. |
| Auditoria futura | Log/Sensível | Tabela futura append-only | Não | 365 dias ou mais | Sim | Alto: trilha de ações e IP/User Agent. | Parcial via `sistema_eventos`. | Append-only, RBAC, export seguro e retenção. |
| Backups SQLite | Backup | `backups/` | Não | Diário 7 a 30 dias, semanal 8 a 12 semanas, mensal 6 a 12 meses | Sim | Crítico: cópia completa do banco. | Fora do Git, backups antes de migrações. | Criptografia, checksums, restore testado, MFA para restauração. |
| Banco SQLite | Sensível | `banco.db` | Não | Arquivo operacional vigente | Sim em produção | Crítico: dados operacionais completos. | `.gitignore`, uso local. | PostgreSQL gerenciado, criptografia, allowlist e backup automático. |
| `.env` | Secret | `.env` local | Nunca | Enquanto credenciais ativas | Sim/Secret Manager | Crítico: tokens e secrets. | `.gitignore`, `.env.example` sem valores. | Secret Manager, rotação e secret scanning. |
| `.env.example` | Público | `.env.example` | Sim | Permanente | Não | Baixo se sem valores reais. | Contém chaves vazias. | Revisão contínua para não incluir segredo. |
| OAuth Mercado Livre | Secret/Sensível | `.env`, fluxo `meli_oauth.py` | Nunca | Conforme expiração/rotação | Sim | Crítico: acesso à conta/API. | Tokens não são impressos; `.env` ignorado. | Secret Manager, rotação, escopos mínimos e auditoria. |
| Code OAuth Mercado Livre | Secret transitório | Terminal local/callback estático | Nunca | Minutos; uso único | Não persistir | Alto: troca por token se capturado. | Uso local e orientação de não compartilhar. | PKCE quando aplicável, expiração e não logar. |
| Dados de afiliado | Sensível | `.env`, banco, links gerados | Parcial: links públicos podem ir ao catálogo; IDs/secrets não | Enquanto parceria ativa | Sim para IDs/secrets | Alto: abuso comercial e alteração de receita. | Validação de link `meli.la`, secrets fora do Git. | RBAC, auditoria de geração e rotação de credenciais. |
| Telegram bot token | Secret | `.env` | Nunca | Enquanto bot ativo | Sim | Crítico: publicação indevida. | `.env` ignorado. | Secret Manager, rotação e permissão `telegram:publish`. |
| Telegram chat IDs | Sensível | `.env` | Não | Enquanto canal ativo | Recomendada | Médio: exposição de destino operacional. | `.env` ignorado. | Secret Manager e minimização. |
| Perfis Playwright/Chrome | Secret/Sensível | diretórios locais de perfil | Nunca | Enquanto sessão necessária | Sim ou proteção de filesystem | Crítico: sessão autenticada. | Ignorados no Git; comandos preservam cookies sem imprimir. | Isolamento, rotação, permissões restritas e auditoria. |
| Cookies/sessões navegador | Secret | Perfis locais | Nunca | Menor tempo possível | Sim | Crítico: sequestro de sessão. | Fora do Git. | Cofre/isolamento, expiração e revogação operacional. |
| Analytics público | Operacional | `cliques` no SQLite ou Cloudflare D1 | Não para bruto; agregados podem ser públicos | 90 a 365 dias, preferir agregado | Recomendada | Baixo/Médio: padrões de tráfego e negócio. | Não registra IP, cookie, e-mail ou User Agent. | Retenção, rate limiting, agregação e painel RBAC. |
| Relatórios históricos | Operacional | `docs/historico/relatorios/` quando sanitizados | Sim se revisados | Permanente se úteis | Não obrigatória | Médio se contiver detalhe operacional sensível. | Relatórios atuais revisados/movidos. | Classificação antes de versionar. |
| CSVs temporários | Operacional/Sensível | arquivos locais temporários | Não | Apagar após uso ou reter até 30 dias | Recomendada | Médio/Alto: dados brutos e links. | `.gitignore`. | Pasta temporária controlada e limpeza automática. |
| Configuração de serviços | Operacional | `.promogg_servicos/`, env vars | Não | Enquanto estado operacional | Recomendada | Médio: revela processos e flags. | Fora do Git. | Config central, RBAC para alteração e auditoria. |
| Estado de workers | Operacional | pid files, stop files, logs | Não | Curto, dias a semanas | Não obrigatória | Baixo/Médio: operação interna. | Fora do Git. | Healthchecks e auditoria. |
| GitHub workflow | Público/Operacional | `.github/workflows/pages.yml` | Sim | Permanente | Não | Alto se adulterado. | Workflow minimalista para Pages. | Branch protection, revisão obrigatória e permissões mínimas. |
| Chaves futuras JWT | Secret | Futuro Secret Manager/env | Nunca | Rotação planejada | Sim | Crítico: falsificação de sessão. | Não implementado. | KMS/Secret Manager, `kid`, rotação e expiração. |
| Refresh tokens futuros | Secret | Futuro banco/sessões | Nunca | Dias/semanas, conforme política | Hash obrigatório | Crítico: sessão persistente. | Não implementado. | Hash, rotação, detecção de reuso e revogação. |
| Dados de usuários futuros | Sensível | Futuro banco de produção | Não | Enquanto conta ativa + retenção legal | Sim | Alto: identidade e acesso. | Não implementado. | RBAC, MFA, auditoria e minimização. |

## Regras Gerais

- Secrets nunca devem ir para Git.
- Dados operacionais brutos não devem ir para Git.
- Relatórios só podem ser versionados quando sanitizados.
- Catálogo público deve conter apenas campos aprovados.
- Logs devem ser úteis para investigação, mas nunca conter senha, token, cookie, segredo ou `.env`.
- Backups devem ser criptografados antes de qualquer retenção longa ou envio para storage externo.

## Retenção Recomendada

| Tipo | Retenção inicial |
|---|---|
| Catálogo público | Última versão versionada e histórico Git. |
| Logs operacionais locais | 30 a 90 dias. |
| Auditoria de segurança | 365 dias ou mais. |
| Analytics bruto | 90 a 180 dias; preferir agregados depois. |
| Backups diários | 7 a 30 dias. |
| Backups semanais | 8 a 12 semanas. |
| Backups mensais | 6 a 12 meses. |
| Tokens/secrets | Enquanto válidos, com rotação periódica. |
| Perfis de navegador | Menor tempo necessário para operação. |

## Criptografia Planejada

- Produção: banco gerenciado com criptografia em repouso.
- Backups: criptografia antes de storage externo.
- Secrets: Secret Manager ou KMS.
- Refresh tokens: hash forte, nunca criptografia reversível.
- TOTP: segredo criptografado com chave em Secret Manager/KMS.
- Logs/auditoria: criptografia em repouso quando armazenados fora do host local.

## Critérios de Aceite

- Todo dado sensível tem dono, localização e proteção definida.
- Todo secret tem regra de não versionamento e rotação.
- Todo dado público tem contrato de sanitização.
- Todo backup tem retenção, criptografia e plano de restore.
- Analytics permanece sem IP, cookie, e-mail ou User Agent completo salvo decisão futura explícita.
