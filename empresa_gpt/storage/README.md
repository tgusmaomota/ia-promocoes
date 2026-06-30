# Storage Contract

## Responsabilidades

- Definir repositorios, consultas, resultados e erros de persistencia.
- Separar banco de plataforma de bancos de cliente.
- Evitar migracoes ou conexoes implicitas.
- Preparar adaptadores para SQLite, PostgreSQL ou storage de artefatos.

## Entradas

- Consulta explicita.
- Nome de colecao/recurso.
- Filtros e limites.
- Contexto de cliente em fases futuras.

## Saidas

- Resultado paginavel.
- Total conhecido quando disponivel.
- Erros de contrato sem detalhes sensiveis.

## Erros

- `StorageError`: consulta invalida, adaptador ausente, schema incompatibile ou operacao bloqueada.

## Regras de Seguranca

- Nao abrir banco em import.
- Nao executar migracao em import.
- Nao tocar no `banco.db` do Promogg.
- Nao expor dados privados em resultados publicos.

## Uso Futuro pelo Promogg

O `banco.py` podera ganhar um adaptador que implemente `RepositoryContract`, mas somente depois de testes de caracterizacao e sem trocar chamadas operacionais em massa.

