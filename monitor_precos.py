from datetime import date

from analisador_promocao import analisar_produto
from banco import (
    conectar,
    inicializar_banco,
    marcar_produto_indisponivel,
    registrar_evento_sistema,
    registrar_log,
    registrar_observacao_preco,
    salvar_promocao,
    semear_historico_existente,
)
from mercadolivre_api import ErroMercadoLivre, consultar_item


def _indisponibilidade_confirmada(item):
    motivo = str(item.get("motivo") or "").lower()
    # Apenas uma resposta conclusiva do anúncio pode retirar uma oferta do
    # catálogo. Falhas de autenticação, rede e timeout são tratadas abaixo.
    return (
        "não encontrado" in motivo
        or "not found" in motivo
        or "http 404" in motivo
        or any(status in motivo for status in ("status mercado livre: closed", "status mercado livre: paused"))
    )


def monitoramento_executado_hoje():
    hoje = date.today().strftime("%Y-%m-%d")
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM logs
            WHERE etapa = 'monitor_precos_sucesso'
              AND substr(criado_em, 1, 10) = ?
            LIMIT 1
            """,
            (hoje,),
        ).fetchone()
    return row is not None


def reavaliar_queda(produto, detalhes):
    produto_atualizado = dict(produto)
    produto_atualizado.update({
        "preco_atual": produto["preco_atual"],
        "categoria": produto.get("categoria_nome") or produto.get("categoria") or "ofertas",
    })
    analise = analisar_produto(produto_atualizado)
    status = "destaque" if detalhes["destaque_menor_preco"] else "reavaliado"
    motivo = (
        f"Reavaliação diária após queda de R$ {abs(detalhes['variacao']):.2f}. "
        f"{analise['motivo']}"
    )
    salvar_promocao(
        produto["id"],
        analise["desconto"],
        analise["score"],
        status,
        motivo,
    )
    registrar_log("curadoria", f"Preço caiu; score reavaliado: {produto['titulo']}", dados=motivo)


def _atualizar_status_monitoramento(produto_id, status):
    with conectar() as conn:
        conn.execute(
            "UPDATE produtos SET status = ? WHERE id = ?",
            (status, produto_id),
        )


def monitorar_precos_diariamente(forcar=False):
    """Atualiza preços conhecidos sem criar postagens nem acionar Telegram."""
    inicializar_banco()
    registrar_evento_sistema("monitoramento_precos", "mercado_livre", "iniciado", "Monitoramento de preços iniciado")
    referencias_criadas = semear_historico_existente()
    if not forcar and monitoramento_executado_hoje():
        registrar_log("monitor_precos", "Monitoramento diário já executado hoje")
        return {"executado": False, "motivo": "já executado hoje", "referencias_criadas": referencias_criadas}

    with conectar() as conn:
        produtos = [dict(row) for row in conn.execute(
            "SELECT * FROM produtos WHERE plataforma = 'mercado_livre' ORDER BY id"
        ).fetchall()]

    resultado = {"executado": True, "referencias_criadas": referencias_criadas, "verificados": 0, "caíram": 0, "subiram": 0, "iguais": 0, "indisponíveis": 0, "erros": 0, "interrompidos": 0}
    falhas_consecutivas = 0
    for indice, produto in enumerate(produtos):
        try:
            item = consultar_item(produto.get("item_id"))
            falhas_consecutivas = 0
            if not item.get("disponivel"):
                motivo = item.get("motivo", "verificação inconclusiva")
                if _indisponibilidade_confirmada(item):
                    marcar_produto_indisponivel(produto["id"], produto, motivo)
                    resultado["indisponíveis"] += 1
                else:
                    registrar_observacao_preco(produto["id"], produto, None, "verificacao_inconclusiva", fonte_preco="api_item")
                    registrar_log("monitor_precos", f"Verificação inconclusiva; status preservado: {produto.get('item_id') or produto['id']}", nivel="warning", dados=motivo)
                continue

            produto_atualizado = dict(produto)
            produto_atualizado.update({
                "titulo": item.get("titulo") or produto["titulo"],
                "preco_atual": item["preco"],
                "categoria_id": item.get("categoria_id", ""),
                "categoria_nome": item.get("categoria_nome", ""),
                "categoria": item.get("categoria_nome") or produto.get("categoria") or "ofertas",
                "imagem": item.get("imagem_url", ""),
            })
            detalhes = registrar_observacao_preco(
                produto["id"], produto_atualizado, item["preco"], "ok", fonte_preco="api_item"
            )
            resultado["verificados"] += 1

            if detalhes["variacao"] < 0:
                _atualizar_status_monitoramento(produto["id"], "monitorado_queda")
                produto_atualizado["preco_atual"] = item["preco"]
                reavaliar_queda(produto_atualizado, detalhes)
                resultado["caíram"] += 1
            elif detalhes["variacao"] > 0:
                _atualizar_status_monitoramento(produto["id"], "monitorado_alta")
                resultado["subiram"] += 1
                registrar_log("monitor_precos", f"Preço subiu; não será republicado: {produto['titulo']}")
            else:
                _atualizar_status_monitoramento(produto["id"], "monitorado_igual")
                resultado["iguais"] += 1
        except (ErroMercadoLivre, ValueError) as erro:
            resultado["erros"] += 1
            falhas_consecutivas += 1
            registrar_log(
                "monitor_precos",
                f"Falha ao verificar {produto.get('item_id') or produto['id']}: {erro}",
                nivel="error",
            )
            registrar_evento_sistema("monitoramento_precos", "mercado_livre", "erro", "Falha ao verificar preço", str(erro))
            # 403 e outras falhas de API nunca alteram a disponibilidade do produto.
            try:
                registrar_observacao_preco(produto["id"], produto, None, "erro_api", fonte_preco="api_item")
            except Exception:
                pass
        except Exception as erro:
            resultado["erros"] += 1
            falhas_consecutivas += 1
            registrar_log(
                "monitor_precos",
                f"Erro inesperado ao verificar produto {produto['id']}: {erro}",
                nivel="error",
            )
            registrar_evento_sistema("monitoramento_precos", "mercado_livre", "erro", "Erro inesperado no monitoramento", str(erro))
            try:
                registrar_observacao_preco(
                    produto["id"], produto, None, "verificacao_inconclusiva", fonte_preco="api_item"
                )
            except Exception:
                pass

        if falhas_consecutivas >= 5:
            resultado["interrompidos"] = len(produtos) - indice - 1
            registrar_log(
                "monitor_precos",
                "Monitoramento interrompido após 5 falhas consecutivas na API; a próxima execução retomará os itens restantes.",
                nivel="warning",
            )
            break

    resumo = "Monitoramento diário: " + " ".join(
        f"{chave}={valor}" for chave, valor in resultado.items() if chave != "executado"
    )
    registrar_log(
        "monitor_precos",
        resumo,
    )
    if not produtos or resultado["verificados"] or resultado["indisponíveis"]:
        registrar_log("monitor_precos_sucesso", "Monitoramento diário concluído")
        registrar_evento_sistema("monitoramento_precos", "mercado_livre", "concluido", "Monitoramento de preços concluído", resumo)
    else:
        registrar_log(
            "monitor_precos",
            "Monitoramento incompleto; será tentado novamente no próximo ciclo.",
            nivel="warning",
        )
        registrar_evento_sistema("monitoramento_precos", "mercado_livre", "atencao", "Monitoramento de preços incompleto", resumo)
    return resultado


if __name__ == "__main__":
    print(monitorar_precos_diariamente(forcar=True))
