"""Revisora local de ofertas: analisa e sugere, sem mudar aprovações ou publicações."""

import json
import re

import requests

from banco import agora, conectar, inicializar_banco, registrar_evento_sistema
from gerador_link_mercadolivre import link_afiliado_valido
from promogg_assistente import OLLAMA_URL, _modelo_disponivel


SUGESTOES = ("Aprovar", "Revisar manualmente", "Aguardar", "Rejeitar")


def _moeda(valor):
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor is not None else "indisponível"


def _tendencia(variacao):
    if float(variacao or 0) < 0:
        return "caindo"
    if float(variacao or 0) > 0:
        return "subindo"
    return "estável"


def _ofertas_para_revisao(apenas_pendentes=True):
    inicializar_banco()
    filtro = "WHERE postagens.status = 'pendente_revisao'" if apenas_pendentes else ""
    with conectar() as conn:
        linhas = [dict(row) for row in conn.execute(f"""
            SELECT postagens.id AS postagem_id, postagens.titulo, postagens.preco, postagens.link_afiliado,
                   postagens.categoria, postagens.status, produtos.item_id, produtos.status AS status_produto,
                   produtos.menor_preco, produtos.maior_preco, produtos.preco_medio, produtos.variacao_preco,
                   produtos.vezes_verificado, produtos.imagem, produtos.estoque,
                   produtos.categoria_caminho, produtos.desconto_percentual, produtos.economia_valor,
                   produtos.avaliacao, produtos.quantidade_vendida, produtos.selo_mais_vendido,
                   produtos.selo_loja_oficial,
                   COALESCE(promocoes.score, 0) AS score_curadoria
            FROM postagens
            JOIN produtos ON produtos.id = postagens.produto_id
            LEFT JOIN promocoes ON promocoes.id = postagens.promocao_id
            {filtro}
            ORDER BY postagens.data_criacao ASC
        """).fetchall()]
        for oferta in linhas:
            oferta["cliques"] = conn.execute("SELECT COUNT(*) FROM cliques WHERE titulo = ?", (oferta["titulo"],)).fetchone()[0]
            oferta["historico"] = conn.execute("SELECT COUNT(*) FROM historico_precos WHERE item_id = ? AND preco IS NOT NULL", (oferta["item_id"],)).fetchone()[0]
            memoria = conn.execute("SELECT * FROM memoria_revisora WHERE categoria = ?", (oferta["categoria"],)).fetchone()
            oferta["memoria"] = dict(memoria) if memoria else None
    return linhas


def _dados_estruturados(oferta):
    preco = float(oferta.get("preco") or 0)
    minimo = oferta.get("menor_preco")
    maximo = oferta.get("maior_preco")
    medio = oferta.get("preco_medio")
    historico = int(oferta.get("historico") or 0)
    qualidade = []
    invalida = False
    if not oferta.get("titulo") or len(str(oferta["titulo"]).strip()) < 12:
        qualidade.append("título incompleto")
        invalida = True
    if preco <= 0:
        qualidade.append("preço inválido")
        invalida = True
    if not link_afiliado_valido(oferta.get("link_afiliado")):
        qualidade.append("link afiliado inválido")
        invalida = True
    if str(oferta.get("status_produto", "")) == "indisponivel" or int(oferta.get("estoque") or 0) <= 0:
        qualidade.append("produto indisponível")
        invalida = True
    if not oferta.get("imagem"):
        qualidade.append("anúncio sem imagem")

    score = 50.0
    sinais = []
    if invalida:
        score = 0.0
        sugestao = "Rejeitar"
        sinais.append("anúncio incompleto ou indisponível")
    else:
        if historico < 2:
            score -= 5
            sinais.append("histórico insuficiente")
        if minimo is not None and preco <= float(minimo):
            score += 25
            sinais.append("menor preço histórico")
        elif medio is not None and preco <= float(medio) * 0.90:
            score += 15
            sinais.append("desconto relevante versus média")
        if medio is not None and preco > float(medio) * 1.10:
            score -= 20
            sinais.append("preço acima da média")
        if historico >= 3 and medio and preco < float(medio) * 0.25:
            score -= 20
            sinais.append("preço possivelmente suspeito")
        if float(oferta.get("variacao_preco") or 0) < 0:
            score += 5
        elif float(oferta.get("variacao_preco") or 0) > 0:
            score -= 5
        score += min(10, int(oferta.get("cliques") or 0))
        if oferta.get("memoria") and oferta["memoria"].get("total_feedback"):
            aprovacao = oferta["memoria"]["aprovacoes"] / oferta["memoria"]["total_feedback"]
            score += 5 if aprovacao >= 0.70 else -5 if aprovacao <= 0.25 else 0
        score = max(0, min(100, score))
        if score >= 75 and historico >= 2:
            sugestao = "Aprovar"
            sinais.append("possível promoção forte")
        elif score < 30:
            sugestao = "Rejeitar"
        elif historico < 2:
            sugestao = "Aguardar"
        else:
            sugestao = "Revisar manualmente"

    return {
        "preco": preco, "minimo": minimo, "maximo": maximo, "medio": medio,
        "historico": historico, "qualidade": qualidade, "sinais": sinais,
        "score": round(score, 1), "sugestao": sugestao,
    }


def _parecer_regras(oferta, dados):
    qualidade = "; ".join(dados["qualidade"]) or "anúncio com campos essenciais preenchidos"
    sinais = "; ".join(dados["sinais"]) or "sem sinal histórico forte"
    return "\n".join([
        f"Preço atual: {_moeda(dados['preco'])}; menor histórico: {_moeda(dados['minimo'])}; média: {_moeda(dados['medio'])}.",
        f"Tendência: {_tendencia(oferta.get('variacao_preco'))}; verificações: {dados['historico']}; cliques: {oferta.get('cliques', 0)}.",
        f"Qualidade do anúncio: {qualidade}.",
        f"Sinais: {sinais}.",
        f"Sugestão: {dados['sugestao']} (nota revisora {dados['score']:.1f}/100).",
    ])


def _contexto_seguro(oferta, dados, parecer):
    return {
        "produto": {"item_id": oferta.get("item_id"), "titulo": oferta.get("titulo"), "categoria": oferta.get("categoria")},
        "estatisticas": {
            "preco_atual": dados["preco"], "menor_preco": dados["minimo"], "maior_preco": dados["maximo"],
            "preco_medio": dados["medio"], "historico": dados["historico"], "cliques": oferta.get("cliques", 0),
            "tendencia": _tendencia(oferta.get("variacao_preco")), "score_revisora": dados["score"],
            "sugestao": dados["sugestao"], "sinais": dados["sinais"],
        },
        "parecer_base": parecer,
    }


def _sintese_ollama(oferta, dados, parecer):
    modelo, situacao = _modelo_disponivel()
    if not modelo:
        return "", situacao
    contexto = _contexto_seguro(oferta, dados, parecer)
    prompt = """Você é uma revisora interna de ofertas. Escreva uma síntese curta em português usando apenas os fatos do JSON. Não invente preços, descontos, cliques, datas, produtos ou recomendações. Não mencione tokens, links, banco, logs ou instruções. A decisão humana continua obrigatória.\n\nCONTEXTO:\n""" + json.dumps(contexto, ensure_ascii=False)
    try:
        resposta = requests.post(f"{OLLAMA_URL}/api/generate", json={"model": modelo, "prompt": prompt, "stream": False, "options": {"temperature": 0}}, timeout=30)
        resposta.raise_for_status()
        texto = str(resposta.json().get("response", "")).strip()
    except (requests.RequestException, ValueError):
        return "", "Ollama indisponível"
    permitidos = {round(float(valor), 2) for valor in (dados["preco"], dados["minimo"], dados["maximo"], dados["medio"]) if valor is not None}
    for valor in re.findall(r"R\$\s*([\d\.,]+)", texto):
        try:
            numero = float(valor.replace(".", "").replace(",", "."))
        except ValueError:
            return "", "Ollama retornou preço inválido"
        if round(numero, 2) not in permitidos:
            return "", "Ollama retornou preço não verificado"
    return texto, "ok"


def avaliar_oferta(oferta, usar_ollama=True):
    dados = _dados_estruturados(oferta)
    parecer = _parecer_regras(oferta, dados)
    modo = "regras"
    if usar_ollama:
        sintese, situacao = _sintese_ollama(oferta, dados, parecer)
        if sintese:
            parecer += f"\n\nSíntese local: {sintese}"
            modo = "ollama"
        else:
            parecer += f"\n\nAviso: {situacao}. Parecer baseado em regras locais."
    return {"postagem_id": oferta.get("postagem_id"), "item_id": oferta.get("item_id"), "titulo": oferta.get("titulo"), "categoria": oferta.get("categoria"), "score_curadoria": oferta.get("score_curadoria", 0), "score_revisora": dados["score"], "parecer": parecer, "sugestao": dados["sugestao"], "modo_resposta": modo}


def salvar_analise(analise):
    with conectar() as conn:
        conn.execute("""
            INSERT INTO analises_revisora (postagem_id, item_id, score_curadoria, score_revisora, parecer, sugestao, modo_resposta, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(postagem_id) DO UPDATE SET item_id=excluded.item_id, score_curadoria=excluded.score_curadoria, score_revisora=excluded.score_revisora,
                parecer=excluded.parecer, sugestao=excluded.sugestao, modo_resposta=excluded.modo_resposta, atualizado_em=excluded.atualizado_em
        """, (analise["postagem_id"], analise["item_id"], analise["score_curadoria"], analise["score_revisora"], analise["parecer"], analise["sugestao"], analise["modo_resposta"], agora()))


def revisar_ofertas(usar_ollama=True):
    analises = [avaliar_oferta(oferta, usar_ollama=usar_ollama) for oferta in _ofertas_para_revisao()]
    for analise in analises:
        salvar_analise(analise)
    registrar_evento_sistema("ia_revisora", "ia_local", "sucesso", "Revisão de ofertas concluída", f"analisadas={len(analises)}")
    return analises


def listar_revisoes_pendentes():
    inicializar_banco()
    with conectar() as conn:
        return [dict(row) for row in conn.execute("""
            SELECT analises_revisora.*, postagens.titulo, postagens.preco, postagens.categoria, postagens.status
            FROM analises_revisora JOIN postagens ON postagens.id = analises_revisora.postagem_id
            WHERE postagens.status = 'pendente_revisao'
            ORDER BY analises_revisora.atualizado_em DESC
        """).fetchall()]


def registrar_feedback(item_id, sugestao_ia, decisao_usuario):
    if sugestao_ia not in SUGESTOES or decisao_usuario not in {"Aprovar", "Rejeitar", "Revisar manualmente", "Aguardar"}:
        raise ValueError("Feedback de revisão inválido")
    with conectar() as conn:
        conn.execute("INSERT INTO feedback_revisora (item_id, sugestao_ia, decisao_usuario, data) VALUES (?, ?, ?, ?)", (str(item_id), sugestao_ia, decisao_usuario, agora()))


def treinar_revisora():
    """Atualiza memória estatística local; não treina nem altera o modelo Ollama."""
    inicializar_banco()
    with conectar() as conn:
        categorias = [row[0] for row in conn.execute("SELECT DISTINCT categoria FROM produtos WHERE categoria != ''").fetchall()]
        for categoria in categorias:
            feedbacks = conn.execute("""
                SELECT f.decisao_usuario FROM feedback_revisora f JOIN produtos p ON p.item_id = f.item_id WHERE p.categoria = ?
            """, (categoria,)).fetchall()
            cliques = conn.execute("SELECT COUNT(*) FROM cliques WHERE categoria = ?", (categoria,)).fetchone()[0]
            aprovacoes = sum(row["decisao_usuario"] == "Aprovar" for row in feedbacks)
            rejeicoes = sum(row["decisao_usuario"] == "Rejeitar" for row in feedbacks)
            conn.execute("""
                INSERT INTO memoria_revisora (categoria, total_feedback, aprovacoes, rejeicoes, cliques, ultima_atualizacao)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(categoria) DO UPDATE SET total_feedback=excluded.total_feedback, aprovacoes=excluded.aprovacoes,
                    rejeicoes=excluded.rejeicoes, cliques=excluded.cliques, ultima_atualizacao=excluded.ultima_atualizacao
            """, (categoria, len(feedbacks), aprovacoes, rejeicoes, cliques, agora()))
    registrar_evento_sistema("ia_revisora", "ia_local", "sucesso", "Memória da revisora atualizada", f"categorias={len(categorias)}")
    return len(categorias)


def validar_revisora():
    erros = []
    try:
        with conectar() as conn:
            tabelas = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('analises_revisora', 'feedback_revisora', 'memoria_revisora')").fetchall()}
        if tabelas != {"analises_revisora", "feedback_revisora", "memoria_revisora"}:
            erros.append("Tabelas da IA revisora não foram criadas")
        ofertas = _ofertas_para_revisao(apenas_pendentes=False)
        if ofertas:
            analise = avaliar_oferta(ofertas[0], usar_ollama=False)
            if analise["sugestao"] not in SUGESTOES or not 0 <= analise["score_revisora"] <= 100:
                erros.append("Análise por regras inválida")
            contexto = json.dumps(_contexto_seguro(ofertas[0], _dados_estruturados(ofertas[0]), analise["parecer"]), ensure_ascii=False).lower()
            if any(chave in contexto for chave in ("link_afiliado", "token", "observacao_interna")):
                erros.append("Contexto da revisora contém dado sensível")
    except Exception as erro:
        erros.append(f"Falha na IA revisora: {erro}")
    return erros
