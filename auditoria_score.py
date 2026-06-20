"""Auditoria somente leitura e simulação da curadoria de ofertas.

Este módulo não altera status, promoções, histórico, links ou dados do catálogo.
Ele existe para tornar a decisão de calibração auditável antes de qualquer mudança
na regra de produção.
"""

import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from analisador_promocao import LIMITE_FILA, LIMITE_REVISAO, analisar_produto
from banco import conectar, inicializar_banco
from gerador_link_mercadolivre import link_afiliado_valido


RELATORIO = Path("RELATORIO_AUDITORIA_SCORE.md")
TITULO_COM_PRECO = re.compile(r"(?i)(?:R\$\s*\d|\d+\s*%\s*OFF)")


def _numero(valor):
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _imagem_publica(url):
    parsed = urlparse(str(url or "").strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def _ofertas_pendentes():
    inicializar_banco()
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT postagens.id AS postagem_id, postagens.produto_id, postagens.titulo,
                   postagens.preco, postagens.link_afiliado, postagens.categoria,
                   postagens.motivo, postagens.data_criacao,
                   produtos.item_id, produtos.preco_atual, produtos.preco_original,
                   produtos.desconto_percentual, produtos.economia_valor,
                   produtos.imagem, produtos.categoria_id, produtos.categoria_nome,
                   produtos.status AS status_produto, produtos.menor_preco,
                   produtos.maior_preco, produtos.preco_medio, produtos.variacao_preco,
                   produtos.vezes_verificado, produtos.destaque_menor_preco
            FROM postagens
            JOIN produtos ON produtos.id = postagens.produto_id
            WHERE postagens.status = 'pendente_revisao'
              AND postagens.plataforma = 'mercado_livre'
            ORDER BY postagens.id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _score_proposto(oferta):
    """Pontuação sugerida; não é usada pela curadoria em produção."""
    preco = _numero(oferta.get("preco_atual") or oferta.get("preco"))
    desconto = _numero(oferta.get("desconto_percentual"))
    economia = _numero(oferta.get("economia_valor"))
    menor = _numero(oferta.get("menor_preco"))
    variacao = _numero(oferta.get("variacao_preco"))
    verificacoes = int(oferta.get("vezes_verificado") or 0)
    titulo = str(oferta.get("titulo") or "")
    pontos = 0
    sinais = []
    faltas = []

    if preco > 0:
        pontos += 10
        sinais.append("preço válido")
    else:
        faltas.append("preço inválido")

    if link_afiliado_valido(oferta.get("link_afiliado")):
        pontos += 10
        sinais.append("link meli.la válido")
    else:
        faltas.append("sem link meli.la válido")

    if _imagem_publica(oferta.get("imagem")):
        pontos += 5
        sinais.append("imagem pública")
    else:
        faltas.append("sem imagem pública")

    if titulo.strip() and not TITULO_COM_PRECO.search(titulo):
        pontos += 5
        sinais.append("título limpo")
    else:
        faltas.append("título ausente ou com preço embutido")

    if str(oferta.get("categoria_id") or "").strip() or str(oferta.get("categoria_nome") or "").strip():
        pontos += 5
        sinais.append("categoria real")
    else:
        faltas.append("sem categoria real")

    if str(oferta.get("status_produto") or "").lower() not in {"indisponivel", "erro"}:
        pontos += 5
        sinais.append("produto disponível")
    else:
        faltas.append("produto indisponível ou com erro")

    if desconto >= 50:
        pontos += 25
        sinais.append("desconto >= 50%")
    elif desconto >= 35:
        pontos += 20
        sinais.append("desconto >= 35%")
    elif desconto >= 25:
        pontos += 15
        sinais.append("desconto >= 25%")
    elif desconto >= 15:
        pontos += 8
        sinais.append("desconto >= 15%")

    if economia > 0:
        pontos += 5
        sinais.append("economia calculada")

    if verificacoes:
        if menor > 0 and preco <= menor + 0.01:
            pontos += 15
            sinais.append("menor preço histórico")
        elif variacao < 0:
            pontos += 10
            sinais.append("preço em queda")
    else:
        # Produto novo não deve perder pontos por ainda não ter série histórica,
        # mas não recebe um bônus que simule promoção comprovada.
        sinais.append("produto novo: histórico ainda insuficiente")

    evidencia_preco = (
        (desconto >= 25 and economia > 0)
        or (menor > 0 and preco <= menor + 0.01)
        or variacao < 0
    )
    return min(100, pontos), sinais, faltas, evidencia_preco


def _classificar(score, limite_auto, limite_revisao, evidencia_preco):
    # Integridade é necessária, mas não substitui evidência de uma boa oferta.
    if score >= limite_auto and evidencia_preco:
        return "aprovado_auto"
    if score >= limite_revisao:
        return "revisao_manual"
    return "rejeitado"


def _analise_oferta(oferta):
    atual = analisar_produto({
        **oferta,
        "preco_atual": oferta.get("preco_atual") or oferta.get("preco"),
        "desconto": oferta.get("desconto_percentual") or 0,
    })
    proposto, sinais, faltas, evidencia_preco = _score_proposto(oferta)
    return {
        **oferta,
        "score_atual": float(atual["score"]),
        "motivo_atual": atual["motivo"],
        "score_proposto": float(proposto),
        "sinais_propostos": sinais,
        "faltas": faltas,
        "evidencia_preco": evidencia_preco,
    }


def _cenarios(itens):
    configuracoes = {
        "A - regra em produção": (LIMITE_FILA, LIMITE_REVISAO),
        "B - auto >= 70 / revisão >= 50": (70, 50),
        "C - auto >= 65 / revisão >= 45": (65, 45),
        "D - auto >= 60 / revisão >= 45": (60, 45),
    }
    resultado = {}
    for nome, (limite_auto, limite_revisao) in configuracoes.items():
        usa_score_atual = nome == "A - regra em produção"
        classes = [
            _classificar(
                item["score_atual"] if usa_score_atual else item["score_proposto"],
                limite_auto,
                limite_revisao,
                item["evidencia_preco"],
            )
            for item in itens
        ]
        contagem = Counter(classes)
        exemplos = []
        for categoria in ("aprovado_auto", "revisao_manual", "rejeitado"):
            exemplo = next((item for item, classe in zip(itens, classes) if classe == categoria), None)
            if exemplo:
                exemplos.append({"resultado": categoria, "titulo": exemplo["titulo"], "score": exemplo["score_atual"] if usa_score_atual else exemplo["score_proposto"]})
        resultado[nome] = {
            "limite_auto": limite_auto,
            "limite_revisao": limite_revisao,
            "aprovadas_auto": contagem["aprovado_auto"],
            "revisao_manual": contagem["revisao_manual"],
            "rejeitadas": contagem["rejeitado"],
            "exemplos": exemplos,
        }
    return resultado


def _escrever_relatorio(itens, cenarios):
    distribuicao = Counter(int(item["score_atual"]) for item in itens)
    motivos = Counter(item["motivo_atual"] for item in itens)
    faltas = Counter(falta for item in itens for falta in item["faltas"])
    top = sorted(itens, key=lambda item: (item["score_proposto"], item["score_atual"]), reverse=True)[:50]
    linhas = [
        "# Relatório de Auditoria de Score", "",
        f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Pendentes auditadas: {len(itens)}", "",
        "## Fórmula atual", "",
        "- Integridade: preço +10, link meli.la +10, imagem pública +5, título limpo +5, categoria real +5 e disponibilidade +5.",
        "- Valor da oferta: desconto +8 a +25, economia +5, menor preço histórico +15 ou queda +10.",
        "- Produto novo não é penalizado por ainda não ter histórico, mas não recebe bônus de promoção comprovada.",
        f"- Aprovação automática: score >= {LIMITE_FILA}, com evidência verificável de preço.",
        f"- Revisão recomendada: score >= {LIMITE_REVISAO}; abaixo disso, rejeição.", "",
        "## Diagnóstico", "",
        "- A regra passou a usar evidências estruturadas em vez de depender de palavras promocionais no título.",
        "- Categoria real, imagem e link confirmam integridade; sozinhos não aprovam uma oferta.",
        "- O corte automático requer desconto com economia, menor preço histórico ou queda real.", "",
        "## Distribuição do score atual", "",
    ]
    linhas.extend(f"- {score}: {quantidade}" for score, quantidade in sorted(distribuicao.items())) or linhas.append("- sem ofertas")
    linhas += ["", "## Motivos de baixa pontuação"]
    linhas.extend(f"- {motivo}: {quantidade}" for motivo, quantidade in motivos.most_common(12)) or linhas.append("- sem dados")
    linhas += ["", "## Campos ou sinais ausentes"]
    linhas.extend(f"- {falta}: {quantidade}" for falta, quantidade in faltas.most_common()) or linhas.append("- nenhum")
    linhas += ["", "## Simulação sem alteração no banco"]
    for nome, dados in cenarios.items():
        linhas += [
            f"### {nome}",
            f"- Aprovadas automaticamente: {dados['aprovadas_auto']}",
            f"- Revisão manual: {dados['revisao_manual']}",
            f"- Rejeitadas: {dados['rejeitadas']}",
        ]
        for exemplo in dados["exemplos"]:
            linhas.append(f"- Exemplo {exemplo['resultado']}: score {exemplo['score']:.0f} | {exemplo['titulo']}")
    linhas += ["", "## Top 50 pendentes por score proposto", ""]
    for indice, item in enumerate(top, 1):
        sinais = ", ".join(item["sinais_propostos"][:5]) or "sem sinais"
        linhas.append(
            f"{indice}. [{item['item_id'] or item['postagem_id']}] atual={item['score_atual']:.0f} "
            f"proposto={item['score_proposto']:.0f} | {item['titulo']} | {sinais}"
        )
    linhas += ["", "## Fórmula sugerida para avaliação futura", "",
        "- Base de integridade: link meli.la +10, imagem +5, título limpo +5, preço válido +10, categoria real +5, disponibilidade +5.",
        "- Valor da oferta: desconto +8 a +25, economia +5, menor preço histórico +15 ou queda +10.",
        "- Produto novo não é penalizado por histórico ausente, mas não recebe bônus que substitua evidência real de preço.",
        "- Aprovação automática proposta exige o score do cenário e evidência verificável: desconto >= 25% com economia, menor preço histórico ou queda real.",
        "- Sugestão segura: começar pelo cenário B, revisar uma amostra das aprovadas simuladas e só então decidir por qualquer mudança.",
        "- Esta auditoria não altera a regra de produção, status, links, histórico, Telegram nem o site.",
    ]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def simular_score():
    """Executa a auditoria e retorna os cenários, sem qualquer escrita no banco."""
    itens = [_analise_oferta(oferta) for oferta in _ofertas_pendentes()]
    cenarios = _cenarios(itens)
    _escrever_relatorio(itens, cenarios)
    return {"total": len(itens), "cenarios": cenarios, "relatorio": str(RELATORIO)}
