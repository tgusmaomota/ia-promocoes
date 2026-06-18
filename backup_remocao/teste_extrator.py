from extrator import extrair_dados_produto

link = "https://www.mercadolivre.com.br/kit-10-potes-hermeticos-vidro-640ml-starhouse-marmita-forno-micro-ondas/p/MLB53222689?pdp_filters=item_id%3AMLB5574851656&extra_comm=true#polycard_client=affiliates&wid=MLB5574851656&sid=affiliates"

produto = extrair_dados_produto(link)

print(produto)