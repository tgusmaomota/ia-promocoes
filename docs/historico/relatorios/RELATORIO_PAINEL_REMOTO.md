# Relatório do Painel Remoto Promogg

- Gerado em: 2026-06-27 10:29:08
- Aprovado: True
- Domínio esperado: painel.promogg.com.br
- Host local: 127.0.0.1
- Porta local: 8501
- Remoto habilitado: True
- Auto deploy painel: False
- Admin emails configurados: sim

## Arquitetura recomendada
- `promogg.com.br`: site público estático.
- `painel.promogg.com.br`: Cloudflare Tunnel apontando para `127.0.0.1:8501`.
- Cloudflare Access: login Google e política Allow apenas para `PROMOGG_ADMIN_EMAILS`.
- Não abrir porta pública no roteador.
- Não expor Streamlit sem Cloudflare Access.

## Achados bloqueantes
- nenhum

## Avisos
- nenhum

## Comando de túnel sugerido
- `cloudflared tunnel --url http://127.0.0.1:8501 --hostname painel.promogg.com.br`

## Checklist Cloudflare Access
- Criar aplicação Self-hosted em Cloudflare Zero Trust.
- Domínio: `painel.promogg.com.br`.
- Session duration curta/moderada.
- Identity provider: Google.
- Policy Allow: somente os e-mails em `PROMOGG_ADMIN_EMAILS`.
- Policy default: deny.
