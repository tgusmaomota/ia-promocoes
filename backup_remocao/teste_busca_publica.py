from buscador import buscar_produtos

produtos = buscar_produtos("air fryer", limite=10)

for p in produtos:
    print()
    print("Título:", p["titulo"])
    print("Preço:", p["preco"])
    print("Link:", p["link"])