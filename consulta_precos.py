import argparse

from banco import conectar, inicializar_banco


def moeda(valor):
    if valor is None:
        return "-"
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def buscar_por_titulo(termo, limite=20):
    inicializar_banco()
    termo = str(termo or "").strip()
    with conectar() as conn:
        return [dict(row) for row in conn.execute(
            """
            SELECT item_id, titulo, preco_atual, menor_preco, preco_medio,
                   categoria_nome, categoria, ultima_verificacao, status
            FROM produtos
            WHERE plataforma = 'mercado_livre' AND lower(titulo) LIKE lower(?)
            ORDER BY atualizado_em DESC LIMIT ?
            """,
            (f"%{termo}%", limite),
        ).fetchall()]


def historico_item(item_id, limite=100):
    inicializar_banco()
    with conectar() as conn:
        return [dict(row) for row in conn.execute(
            """
            SELECT item_id, titulo, preco, data_verificacao, categoria_nome, status_verificacao
            FROM historico_precos
            WHERE item_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (str(item_id).strip().upper(), limite),
        ).fetchall()]


def menor_preco_por_titulo(termo):
    produtos = buscar_por_titulo(termo)
    return sorted(produtos, key=lambda produto: produto["menor_preco"] if produto["menor_preco"] is not None else float("inf"))


def relatorio_produto(termo):
    produtos = buscar_por_titulo(termo)
    for produto in produtos:
        produto["historico"] = historico_item(produto["item_id"], limite=10)
    return produtos


def resumo_precos():
    inicializar_banco()
    with conectar() as conn:
        monitorados = conn.execute("SELECT COUNT(*) FROM produtos WHERE vezes_verificado > 0").fetchone()[0]
        hoje_menor = conn.execute(
            """
            SELECT COUNT(*) FROM produtos
            WHERE destaque_menor_preco = 1
              AND substr(COALESCE(ultima_verificacao, ''), 1, 10) = date('now', 'localtime')
            """
        ).fetchone()[0]
        subiram = conn.execute("SELECT COUNT(*) FROM produtos WHERE variacao_preco > 0").fetchone()[0]
        cairam = conn.execute("SELECT COUNT(*) FROM produtos WHERE variacao_preco < 0").fetchone()[0]
        indisponiveis = conn.execute("SELECT COUNT(*) FROM produtos WHERE status = 'indisponivel'").fetchone()[0]
        categorias = [dict(row) for row in conn.execute(
            """
            SELECT COALESCE(NULLIF(categoria_nome, ''), categoria, 'ofertas') AS categoria,
                   COUNT(*) AS total
            FROM produtos
            WHERE status != 'indisponivel'
            GROUP BY categoria
            ORDER BY total DESC, categoria ASC LIMIT 10
            """
        ).fetchall()]
        erros = [dict(row) for row in conn.execute(
            """
            SELECT etapa, mensagem, criado_em FROM logs
            WHERE nivel = 'error'
              AND lower(etapa) NOT LIKE '%shopee%'
              AND lower(mensagem) NOT LIKE '%shopee%'
            ORDER BY id DESC LIMIT 10
            """
        ).fetchall()]
    return {
        "monitorados": monitorados,
        "menor_preco_hoje": hoje_menor,
        "subiram": subiram,
        "cairam": cairam,
        "indisponiveis": indisponiveis,
        "categorias": categorias,
        "erros": erros,
    }


def imprimir_busca(termo):
    resultados = buscar_por_titulo(termo)
    if not resultados:
        print("Nenhum produto encontrado.")
        return
    for produto in resultados:
        categoria = produto["categoria_nome"] or produto["categoria"] or "ofertas"
        print(f"{produto['item_id']} | {produto['titulo']}")
        print(f"  Atual: {moeda(produto['preco_atual'])} | Menor: {moeda(produto['menor_preco'])} | Categoria: {categoria}")


def imprimir_historico(item_id):
    registros = historico_item(item_id)
    if not registros:
        print("Nenhum histórico encontrado para este item.")
        return
    for registro in registros:
        print(f"{registro['data_verificacao']} | {moeda(registro['preco'])} | {registro['status_verificacao']}")


def imprimir_menor_preco(termo):
    resultados = menor_preco_por_titulo(termo)
    if not resultados:
        print("Nenhum produto encontrado.")
        return
    for produto in resultados:
        print(f"{produto['item_id']} | menor preço: {moeda(produto['menor_preco'])} | atual: {moeda(produto['preco_atual'])}")


def imprimir_relatorio(termo):
    resultados = relatorio_produto(termo)
    if not resultados:
        print("Nenhum produto encontrado.")
        return
    for produto in resultados:
        categoria = produto["categoria_nome"] or produto["categoria"] or "ofertas"
        print(f"\n{produto['titulo']} ({produto['item_id']})")
        print(f"Categoria: {categoria}")
        print(f"Preço atual: {moeda(produto['preco_atual'])}")
        print(f"Menor preço: {moeda(produto['menor_preco'])}")
        print(f"Preço médio: {moeda(produto['preco_medio'])}")
        print(f"Última atualização: {produto['ultima_verificacao'] or '-'}")
        print("Últimas verificações:")
        for registro in produto["historico"]:
            print(f"- {registro['data_verificacao']}: {moeda(registro['preco'])} ({registro['status_verificacao']})")


def imprimir_resumo_precos():
    resumo = resumo_precos()
    print("Relatório de preços")
    print(f"Produtos monitorados: {resumo['monitorados']}")
    print(f"Menor preço histórico hoje: {resumo['menor_preco_hoje']}")
    print(f"Produtos que subiram: {resumo['subiram']}")
    print(f"Produtos que caíram: {resumo['cairam']}")
    print(f"Produtos indisponíveis: {resumo['indisponiveis']}")
    print("\nCategorias com mais ofertas:")
    for categoria in resumo["categorias"] or [{"categoria": "sem dados", "total": 0}]:
        print(f"- {categoria['categoria']}: {categoria['total']}")
    print("\nErros recentes:")
    for erro in resumo["erros"] or [{"criado_em": "-", "etapa": "-", "mensagem": "nenhum"}]:
        print(f"- {erro['criado_em']} [{erro['etapa']}] {erro['mensagem']}")


def main():
    parser = argparse.ArgumentParser(description="Consultas locais ao histórico de preços")
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    for nome in ("buscar", "menor-preco", "relatorio"):
        comando = subcomandos.add_parser(nome)
        comando.add_argument("termo")
    historico = subcomandos.add_parser("historico")
    historico.add_argument("item_id")
    args = parser.parse_args()

    if args.comando == "buscar":
        imprimir_busca(args.termo)
    elif args.comando == "historico":
        imprimir_historico(args.item_id)
    elif args.comando == "menor-preco":
        imprimir_menor_preco(args.termo)
    else:
        imprimir_relatorio(args.termo)


if __name__ == "__main__":
    main()
