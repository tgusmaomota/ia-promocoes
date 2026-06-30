# Modelo de Modulos

## Categorias Oficiais

### Core EmpresaGPT

Modulo com alta chance de virar base da plataforma, com baixo acoplamento a um cliente especifico ou com responsabilidade claramente transversal.

### Exclusivo do Promogg

Modulo que implementa regra, fluxo, interface, integracao ou artefato especifico do Promogg.

### Compartilhavel no Futuro

Modulo util, mas ainda acoplado a detalhes do Promogg. Precisa de contrato, limpeza, testes ou adaptador antes de migrar.

### Legado

Modulo antigo, simples demais, duplicado ou substituido por implementacao mais nova. Deve ser preservado ate confirmacao de ausencia de uso.

### Candidato a Quarentena

Modulo com risco operacional, baixa clareza de uso, finalidade temporaria, script de correcao pontual ou potencial para ser removido depois de auditoria.

## Criterios de Promocao para Plataforma

- Sem dependencia direta de dominio Promogg.
- Testes cobrindo contrato principal.
- Configuracao por parametros ou settings.
- Erros padronizados.
- Logs sanitizados.
- Compatibilidade comprovada por adaptador.

## Criterios de Permanencia no Cliente

- Depende de Mercado Livre, afiliados, catalogo de ofertas ou site Promogg.
- Manipula banco operacional atual.
- Executa automacao local especifica.
- E interface operacional do cliente.
- Existe para manutencao ou recuperacao historica.

