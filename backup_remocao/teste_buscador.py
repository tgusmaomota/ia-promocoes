from buscador import buscar_produtos

produtos = buscar_produtos("air fryer", limite=5)

for produto in produtos:
    print(produto)