from datetime import datetime

from agente_ofertas import coletar_ofertas
from banco import registrar_log, salvar_produto
from gerador_link_mercadolivre import gerar_link_afiliado


def normalizar_produto(produto):
    link_original = str(produto.get("link", "")).strip()
    link_afiliado = gerar_link_afiliado(link_original)

    return {
        "titulo": produto.get("titulo", ""),
        "preco_atual": produto.get("preco", 0),
        "preco_anterior": produto.get("preco_anterior"),
        "link_original": link_original,
        "link_afiliado": link_afiliado,
        "item_id": produto.get("item_id", ""),
        "plataforma": "mercado_livre",
        "categoria": produto.get("categoria", "ofertas"),
        "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "coletado",
        "desconto": produto.get("desconto", 0),
        "imagem": produto.get("imagem", ""),
        "estoque": 1,
    }


def coletar(salvar_no_banco=True):
    registrar_log("coletor_mercadolivre", "Iniciando coleta Mercado Livre")
    produtos = coletar_ofertas()
    normalizados = [normalizar_produto(produto) for produto in produtos]
    salvos = 0
    rejeitados = 0

    if salvar_no_banco:
        for produto in normalizados:
            ok, _, motivo = salvar_produto(produto)
            if ok:
                salvos += 1
            else:
                rejeitados += 1
                registrar_log(
                    "coletor_mercadolivre",
                    f"Produto rejeitado: {produto['titulo']} ({motivo})",
                )

    registrar_log(
        "coletor_mercadolivre",
        f"Coleta finalizada. coletados={len(normalizados)} salvos={salvos} rejeitados={rejeitados}",
    )
    return normalizados


if __name__ == "__main__":
    coletar()
