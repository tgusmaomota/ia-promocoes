"""Curadoria automática segura e auditável do Promogg.

Este módulo decide ofertas pendentes/novas usando apenas dados locais já
coletados. Não publica, não gera site e não chama Telegram.
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from urllib.parse import urlparse

from banco import conectar, criar_postagem, inicializar_banco, registrar_log, salvar_promocao
from gerador_link_mercadolivre import link_afiliado_valido
from item_utils import extrair_item_id
from operacao_sistema import criar_backup_emergencia


RELATORIO = Path("RELATORIO_CURADORIA_AUTOMATICA.md")
TITULO_COM_PRECO = re.compile(r"(?i)(?:R\$\s*\d|\d+\s*%\s*OFF)")
CATEGORIAS_PROIBIDAS = {
    "armas",
    "munições",
    "municoes",
    "tabaco",
    "cigarros",
    "bebidas alcoólicas",
    "bebidas alcoolicas",
}

PESOS = {
    "integridade": 30,
    "preco": 30,
    "historico": 15,
    "comercial": 15,
    "confiabilidade": 10,
}


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def numero(valor, padrao=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def inteiro(valor, padrao=0):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return padrao


def _url_https(valor):
    url = urlparse(str(valor or "").strip())
    return url.scheme in {"http", "https"} and bool(url.netloc)


def _permalink_valido(oferta):
    link = str(oferta.get("link_original") or "").strip()
    if not link:
        return True
    return _url_https(link)


def _titulo_limpo(titulo):
    titulo = " ".join(str(titulo or "").split())
    return len(titulo) >= 8 and not TITULO_COM_PRECO.search(titulo)


def _categoria_confiavel(oferta):
    categoria = str(oferta.get("categoria_nome") or oferta.get("categoria") or "").strip().lower()
    caminho = str(oferta.get("categoria_caminho") or "").strip()
    if any(proibida in categoria or proibida in caminho.lower() for proibida in CATEGORIAS_PROIBIDAS):
        return False
    return bool(categoria and categoria not in {"ofertas", "oferta", "sem categoria"} or caminho)


def _historico_produto(produto_id):
    with conectar() as conn:
        rows = [dict(row) for row in conn.execute(
            """
            SELECT preco, status_verificacao, fonte_preco
            FROM historico_precos
            WHERE produto_id = ? AND preco IS NOT NULL AND preco > 0
            ORDER BY id DESC
            LIMIT 20
            """,
            (produto_id,),
        ).fetchall()]
    precos = [numero(row["preco"]) for row in rows if numero(row["preco"]) > 0]
    if not precos:
        return {
            "observacoes": 0, "menor": 0, "maior": 0, "media": 0,
            "queda_recente": False, "alta_recente": False, "confiabilidade": 0,
        }
    fontes_boas = sum(
        1 for row in rows
        if str(row.get("fonte_preco") or row.get("status_verificacao") or "") in {
            "api_item", "api", "coleta", "playwright", "ok", "coletado",
            "baseline_local", "recuperacao_catalogo_estatico",
        }
    )
    return {
        "observacoes": len(precos),
        "menor": min(precos),
        "maior": max(precos),
        "media": round(mean(precos), 2),
        "queda_recente": len(precos) >= 2 and precos[0] < precos[1],
        "alta_recente": len(precos) >= 2 and precos[0] > precos[1] * 1.20,
        "confiabilidade": round(min(100, min(len(precos), 5) * 12 + (fontes_boas / max(1, len(rows))) * 40), 1),
    }


def carregar_ofertas_para_curadoria():
    """Lista pendentes e produtos novos ainda sem postagem."""
    inicializar_banco()
    with conectar() as conn:
        pendentes = [dict(row) for row in conn.execute(
            """
            SELECT postagens.id AS postagem_id, postagens.status AS status_postagem,
                   postagens.titulo AS titulo_postagem, postagens.preco AS preco_postagem,
                   postagens.link_afiliado AS link_afiliado_postagem,
                   postagens.categoria AS categoria_postagem,
                   postagens.motivo AS motivo_postagem,
                   produtos.*
            FROM postagens
            JOIN produtos ON produtos.id = postagens.produto_id
            WHERE postagens.status = 'pendente_revisao'
              AND produtos.plataforma = 'mercado_livre'
            ORDER BY postagens.id
            """
        ).fetchall()]
        novos = [dict(row) for row in conn.execute(
            """
            SELECT NULL AS postagem_id, NULL AS status_postagem, NULL AS titulo_postagem,
                   NULL AS preco_postagem, NULL AS link_afiliado_postagem,
                   NULL AS categoria_postagem, NULL AS motivo_postagem,
                   produtos.*
            FROM produtos
            WHERE produtos.plataforma = 'mercado_livre'
              AND produtos.status IN ('coletado', 'migrado_csv')
              AND produtos.status NOT IN ('indisponivel', 'erro', 'duplicado_oculto')
              AND NOT EXISTS (
                  SELECT 1 FROM postagens WHERE postagens.produto_id = produtos.id
              )
            ORDER BY produtos.id
            """
        ).fetchall()]
    return pendentes + novos


def _normalizar_oferta(oferta):
    oferta = dict(oferta)
    oferta["titulo"] = str(oferta.get("titulo_postagem") or oferta.get("titulo") or "").strip()
    oferta["preco"] = numero(oferta.get("preco_postagem") or oferta.get("preco_atual"))
    oferta["link_afiliado"] = str(oferta.get("link_afiliado_postagem") or oferta.get("link_afiliado") or "").strip()
    oferta["categoria"] = str(oferta.get("categoria_postagem") or oferta.get("categoria_nome") or oferta.get("categoria") or "ofertas").strip() or "ofertas"
    oferta["item_id"] = str(oferta.get("item_id") or extrair_item_id(oferta.get("link_original")) or "").strip().upper()
    return oferta


def avaliar_oferta(oferta):
    oferta = _normalizar_oferta(oferta)
    historico = _historico_produto(oferta["id"])
    preco = numero(oferta.get("preco") or oferta.get("preco_atual"))
    preco_original = numero(oferta.get("preco_original") or oferta.get("preco_anterior"))
    desconto = numero(oferta.get("desconto_percentual") or oferta.get("percentual_off"))
    if desconto <= 0 and preco_original > preco > 0:
        desconto = round(((preco_original - preco) / preco_original) * 100, 2)
    economia = numero(oferta.get("economia_valor"))
    if economia <= 0 and preco_original > preco > 0:
        economia = round(preco_original - preco, 2)

    positivos = []
    negativos = []
    criticos = []
    componentes = {"integridade": 0, "preco": 0, "historico": 0, "comercial": 0, "confiabilidade": 0}

    item_id = str(oferta.get("item_id") or "").strip().upper()
    if item_id.startswith("MLB") and extrair_item_id(item_id) == item_id:
        componentes["integridade"] += 5
    else:
        criticos.append("item_id inválido")

    if link_afiliado_valido(oferta.get("link_afiliado")):
        componentes["integridade"] += 7
    else:
        criticos.append("sem meli.la válido")

    if preco > 0:
        componentes["integridade"] += 5
    else:
        criticos.append("preço inválido")

    if _url_https(oferta.get("imagem")):
        componentes["integridade"] += 4
    else:
        criticos.append("imagem inválida")

    if _titulo_limpo(oferta.get("titulo")):
        componentes["integridade"] += 4
    else:
        criticos.append("título vazio/sujo")

    if _permalink_valido(oferta):
        componentes["integridade"] += 3
    else:
        criticos.append("permalink inválido")

    status_produto = str(oferta.get("status") or "").lower()
    motivo_indisponivel = str(oferta.get("motivo_indisponivel") or "").lower()
    if status_produto in {"indisponivel", "erro", "duplicado_oculto"} and any(x in motivo_indisponivel for x in ("404", "finalizado", "pausado", "closed", "inactive")):
        criticos.append("indisponível confirmado")
    elif status_produto not in {"indisponivel", "erro", "duplicado_oculto"}:
        componentes["integridade"] += 2

    if desconto >= 35:
        componentes["preco"] += 10
        positivos.append(f"desconto real {desconto:g}%")
    elif desconto >= 20:
        componentes["preco"] += 7
        positivos.append(f"desconto real {desconto:g}%")
    elif desconto >= 10:
        componentes["preco"] += 3
    else:
        negativos.append("desconto fraco/ausente")

    if economia >= 100:
        componentes["preco"] += 7
        positivos.append(f"economia R$ {economia:.2f}")
    elif economia > 0:
        componentes["preco"] += 4
        positivos.append(f"economia R$ {economia:.2f}")

    menor_preco = numero(oferta.get("menor_preco") or historico["menor"])
    variacao = numero(oferta.get("variacao_preco"))
    if menor_preco > 0 and preco > 0 and preco <= menor_preco + 0.01:
        componentes["historico"] += 8
        positivos.append("menor preço histórico")
    if variacao < 0 or historico["queda_recente"]:
        componentes["historico"] += 5
        positivos.append("preço caiu na última verificação")
    if historico["observacoes"] >= 2:
        componentes["historico"] += 2
    else:
        negativos.append("histórico insuficiente")
    if historico["alta_recente"]:
        negativos.append("preço subiu muito recentemente")

    avaliacao = numero(oferta.get("avaliacao"))
    if avaliacao > 5:
        avaliacao = round(avaliacao / 10, 2)
    vendidos = inteiro(oferta.get("quantidade_vendida"))
    if avaliacao >= 4.5:
        componentes["comercial"] += 4
        positivos.append(f"boa avaliação {avaliacao:g}")
    elif avaliacao > 0 and avaliacao < 3.8:
        negativos.append(f"avaliação baixa {avaliacao:g}")
    if vendidos >= 100:
        componentes["comercial"] += 4
        positivos.append(f"{vendidos} vendidos")
    elif vendidos >= 20:
        componentes["comercial"] += 2
    if inteiro(oferta.get("vendedor_confiavel")):
        componentes["comercial"] += 2
        positivos.append("vendedor confiável")
    if inteiro(oferta.get("selo_loja_oficial")):
        componentes["comercial"] += 2
        positivos.append("loja oficial")
    if inteiro(oferta.get("selo_mais_vendido")):
        componentes["comercial"] += 2
        positivos.append("mais vendido")
    if _categoria_confiavel(oferta):
        componentes["comercial"] += 1
        positivos.append("categoria confiável")
    else:
        negativos.append("categoria genérica/duvidosa")

    origem_categoria = str(oferta.get("origem_categoria") or "").strip()
    origem_preco = str(oferta.get("dados_comerciais_origem") or oferta.get("status_verificacao") or "").strip()
    componentes["confiabilidade"] += min(6, historico["confiabilidade"] / 100 * 6)
    if origem_categoria in {"api", "breadcrumb", "site_restaurado", "dist_site_restaurado"}:
        componentes["confiabilidade"] += 2
    if origem_preco in {"ok", "api_item", "coletado", "baseline_local"} or historico["observacoes"] > 0:
        componentes["confiabilidade"] += 2

    for chave, limite in PESOS.items():
        componentes[chave] = min(limite, componentes[chave])
    score = round(sum(componentes.values()), 1)

    sinais_preco = sum(
        1 for sinal in (
            desconto >= 20,
            economia > 0,
            menor_preco > 0 and preco > 0 and preco <= menor_preco + 0.01,
            variacao < 0 or historico["queda_recente"],
        ) if sinal
    )
    sinais_comerciais = sum(
        1 for sinal in (
            avaliacao >= 4.5,
            vendidos >= 20,
            inteiro(oferta.get("vendedor_confiavel")),
            inteiro(oferta.get("selo_loja_oficial")),
            inteiro(oferta.get("selo_mais_vendido")),
            _categoria_confiavel(oferta),
            score >= 70,
        ) if sinal
    )
    sinais_positivos = sinais_preco + sinais_comerciais

    if criticos:
        decisao = "rejeitado"
        motivo = "; ".join(criticos[:4])
    elif historico["alta_recente"] and sinais_preco == 0:
        decisao = "rejeitado"
        motivo = "preço subiu muito e não há oportunidade"
    elif not sinais_preco and score < 55:
        decisao = "rejeitado"
        motivo = "sem evidência de promoção após enriquecimento"
    elif score < 42:
        decisao = "rejeitado"
        motivo = f"score muito baixo: {score:g}"
    elif score >= 45 and sinais_preco >= 2 and sinais_positivos >= 2:
        decisao = "aprovado_auto"
        motivo = f"aprovado automaticamente: score {score:g}; {', '.join(positivos[:4])}"
    elif score < 55 and sinais_preco < 2:
        decisao = "rejeitado"
        motivo = "sem evidência suficiente de promoção"
    else:
        decisao = "pendente_revisao"
        motivo = f"incerteza real: score {score:g}; {', '.join(negativos[:4]) or 'sinais insuficientes'}"

    if decisao != "aprovado_auto" and "internacional" in str(oferta.get("titulo") or "").lower():
        decisao = "rejeitado"
        motivo = "categoria/produto indesejado: internacional"

    return {
        "postagem_id": oferta.get("postagem_id"),
        "produto_id": oferta.get("id"),
        "item_id": item_id,
        "titulo": oferta.get("titulo"),
        "score": score,
        "componentes": componentes,
        "decisao": decisao,
        "motivo": motivo,
        "positivos": positivos,
        "negativos": negativos,
        "criticos": criticos,
        "desconto": desconto,
        "economia": economia,
        "historico": historico,
        "oferta": oferta,
    }


def _atualizar_postagem_existente(conn, analise, promocao_id):
    status = analise["decisao"]
    conn.execute(
        """
        UPDATE postagens
        SET status = ?,
            motivo = ?,
            promocao_id = ?,
            aprovado_por = CASE WHEN ? = 'aprovado_auto' THEN 'curadoria_automatica' ELSE aprovado_por END,
            aprovado_em = CASE WHEN ? = 'aprovado_auto' THEN COALESCE(aprovado_em, ?) ELSE aprovado_em END,
            atualizado_em = ?
        WHERE id = ?
        """,
        (status, analise["motivo"], promocao_id, status, status, agora(), agora(), analise["postagem_id"]),
    )


def _aplicar_decisao(analise):
    oferta = analise["oferta"]
    promocao_id = salvar_promocao(
        analise["produto_id"],
        analise["desconto"],
        analise["score"],
        analise["decisao"],
        f"curadoria_automatica_v2: {analise['motivo']}",
    )
    if analise.get("postagem_id"):
        with conectar() as conn:
            _atualizar_postagem_existente(conn, analise, promocao_id)
    else:
        from fila_postagens import gerar_texto_post, pode_publicar_texto

        texto = gerar_texto_post(oferta, {"desconto": analise["desconto"]})
        ok_texto, motivo_texto = pode_publicar_texto(texto)
        status = analise["decisao"] if ok_texto else "rejeitado"
        motivo = analise["motivo"] if ok_texto else f"anti-spam: {motivo_texto}"
        criar_postagem(analise["produto_id"], promocao_id, oferta, texto, status=status, motivo=motivo)
    registrar_log(
        "curadoria_automatica",
        f"Produto={analise['produto_id']} -> {analise['decisao']}",
        dados=json.dumps({
            "score": analise["score"],
            "motivo": analise["motivo"],
            "positivos": analise["positivos"][:8],
            "negativos": analise["negativos"][:8],
        }, ensure_ascii=False)[:1000],
    )


def _contar_pendentes():
    inicializar_banco()
    with conectar() as conn:
        return conn.execute("SELECT COUNT(*) FROM postagens WHERE status='pendente_revisao'").fetchone()[0]


def _gerar_relatorio(resultado):
    motivos = Counter(item["motivo"] for item in resultado["itens"])
    scores = [item["score"] for item in resultado["itens"]]

    def exemplos(status):
        return [item for item in resultado["itens"] if item["decisao"] == status][:8]

    linhas = [
        "# Relatório de Curadoria Automática",
        "",
        f"- Gerado em: {agora()}",
        f"- Modo: {'dry-run' if resultado['dry_run'] else 'execução real'}",
        f"- Backup: {resultado.get('backup') or 'não aplicável'}",
        f"- Pendentes antes: {resultado['pendentes_antes']}",
        f"- Pendentes depois: {resultado['pendentes_depois']}",
        f"- Pendentes estimados após aplicar: {resultado.get('pendentes_estimados_pos_aplicacao', resultado['pendentes'])}",
        f"- Total analisado: {resultado['total']}",
        f"- Aprovados automaticamente: {resultado['aprovados_auto']}",
        f"- Rejeitados automaticamente: {resultado['rejeitados']}",
        f"- Mantidos pendentes: {resultado['pendentes']}",
        "",
        "## Regras usadas",
        "- Rejeição automática para item_id inválido, ausência de `meli.la`, preço inválido, imagem inválida, título sujo/vazio, permalink inválido ou indisponibilidade confirmada.",
        "- Aprovação automática exige requisitos mínimos íntegros, score >= 45, pelo menos 2 sinais positivos de preço e pelo menos 2 sinais positivos totais.",
        "- Pendência fica restrita a conflito/incerteza: histórico fraco, categoria duvidosa ou sinais comerciais insuficientes sem erro crítico.",
        f"- Pesos: {', '.join(f'{k}={v}' for k, v in PESOS.items())}.",
        "",
        "## Distribuição de score",
        f"- Menor: {min(scores) if scores else 0:g}",
        f"- Médio: {round(mean(scores), 1) if scores else 0:g}",
        f"- Maior: {max(scores) if scores else 0:g}",
        "",
        "## Motivos principais",
    ]
    linhas += [f"- {motivo}: {total}" for motivo, total in motivos.most_common(12)] or ["- nenhum"]
    for titulo_secao, status in (
        ("Exemplos aprovados", "aprovado_auto"),
        ("Exemplos rejeitados", "rejeitado"),
        ("Exemplos pendentes", "pendente_revisao"),
    ):
        linhas += ["", f"## {titulo_secao}"]
        itens = exemplos(status)
        if not itens:
            linhas.append("- nenhum")
        for item in itens:
            linhas.append(
                f"- #{item.get('postagem_id') or 'novo'} {item['item_id']} | score={item['score']:g} | "
                f"{item['titulo']} | {item['motivo']}"
            )
    linhas += [
        "",
        "## Segurança",
        "- Histórico de preços não foi apagado.",
        "- Telegram, deploy, ONLINE e geração de site não são chamados por este comando.",
        "- O dry-run é somente leitura; a execução real cria backup antes de aplicar decisões.",
    ]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def executar_curadoria_automatica(dry_run=True):
    pendentes_antes = _contar_pendentes()
    ofertas = carregar_ofertas_para_curadoria()
    analises = [avaliar_oferta(oferta) for oferta in ofertas]
    resultado = {
        "dry_run": dry_run,
        "backup": "",
        "pendentes_antes": pendentes_antes,
        "pendentes_depois": pendentes_antes,
        "pendentes_estimados_pos_aplicacao": pendentes_antes,
        "total": len(analises),
        "aprovados_auto": 0,
        "rejeitados": 0,
        "pendentes": 0,
        "itens": [],
    }
    if not dry_run:
        resultado["backup"] = str(criar_backup_emergencia())

    for analise in analises:
        resultado[{
            "aprovado_auto": "aprovados_auto",
            "rejeitado": "rejeitados",
            "pendente_revisao": "pendentes",
        }[analise["decisao"]]] += 1
        item_relatorio = {
            "postagem_id": analise.get("postagem_id"),
            "produto_id": analise.get("produto_id"),
            "item_id": analise["item_id"],
            "titulo": analise["titulo"],
            "score": analise["score"],
            "decisao": analise["decisao"],
            "motivo": analise["motivo"],
            "positivos": analise["positivos"],
            "negativos": analise["negativos"],
            "componentes": analise["componentes"],
        }
        resultado["itens"].append(item_relatorio)
        if not dry_run:
            _aplicar_decisao(analise)

    resultado["pendentes_estimados_pos_aplicacao"] = resultado["pendentes"]
    resultado["pendentes_depois"] = pendentes_antes if dry_run else _contar_pendentes()
    _gerar_relatorio(resultado)
    return resultado
