import csv

with open("posts_prontos.csv", newline="", encoding="utf-8") as arquivo:
    leitor = csv.DictReader(arquivo)

    whatsapp = open("whatsapp.txt", "w", encoding="utf-8")
    promobit = open("promobit.txt", "w", encoding="utf-8")
    instagram = open("instagram.txt", "w", encoding="utf-8")

    for linha in leitor:
        if linha["status"] == "aprovado":
            post = linha["post"]

            whatsapp.write(post)
            whatsapp.write("\n\n" + "-" * 40 + "\n\n")

            promobit.write(post)
            promobit.write("\n\n" + "-" * 40 + "\n\n")

            instagram.write(post)
            instagram.write("\n\n" + "-" * 40 + "\n\n")

    whatsapp.close()
    promobit.close()
    instagram.close()

print("Arquivos exportados: whatsapp.txt, promobit.txt e instagram.txt")