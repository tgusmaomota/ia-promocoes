# Assistente Local de Precos

O assistente consulta exclusivamente o `banco.db` local. O Ollama recebe apenas um contexto calculado e sanitizado (titulo, categoria, precos, datas, tendencia e recomendacao); ele nao recebe `.env`, tokens, links, logs, observacoes internas ou o arquivo SQLite.

## Configuracao

No arquivo `.env`, defina o modelo local desejado:

```env
OLLAMA_MODEL=llama3.2
OLLAMA_URL=http://localhost:11434
```

Confira os modelos instalados e inicie o servico, quando necessario:

```bash
ollama list
ollama serve
ollama pull llama3.2
```

Para trocar o modelo, altere somente `OLLAMA_MODEL` para um nome exibido em `ollama list`, por exemplo `qwen2.5:3b`.

## Uso

```bash
python3 promogg_assistente.py perguntar "Qual foi o menor preco do PS5?"
python3 ia_promocoes.py perguntar "Vale comprar PS5 agora?"
python3 ia_promocoes.py treinar-memoria
python3 ia_promocoes.py validar
```

`treinar-memoria` nao treina, baixa ou altera nenhum modelo. Ele recalcula resumos locais em `memoria_produtos` usando historico de preco, cliques e feedbacks existentes.

Se o Ollama estiver indisponivel, a resposta continua funcionando por regras locais e exibe um aviso. O painel Streamlit tambem segue funcional nesse modo.

## Privacidade

As perguntas e os feedbacks ficam somente nas tabelas locais `perguntas_assistente` e `feedback_assistente`. Elas nao sao geradas para `site/`, `dist_site/` ou `ofertas.json`.
