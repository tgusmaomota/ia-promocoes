from schema_posts import ler_posts

df = ler_posts("posts_prontos.csv")

aprovados = df[df["status"] == "aprovado"]

if aprovados.empty:
    print("Nenhum post aprovado.")
    exit()

with open("telegram.txt", "w", encoding="utf-8") as tg:
    for _, linha in aprovados.iterrows():
        tg.write(linha["post"])
        tg.write("\n\n-----------------\n\n")

with open("whatsapp.txt", "w", encoding="utf-8") as wa:
    for _, linha in aprovados.iterrows():
        wa.write(linha["post"])
        wa.write("\n\n-----------------\n\n")

with open("instagram.txt", "w", encoding="utf-8") as insta:
    for _, linha in aprovados.iterrows():
        insta.write(linha["post"])
        insta.write("\n\n-----------------\n\n")

print(f"{len(aprovados)} posts exportados.")
