from dotenv import load_dotenv
import requests
import os

from schema_posts import ler_posts, salvar_posts

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ARQUIVO_POSTS = "posts_prontos.csv"

if not TOKEN or not CHAT_ID:
    print("Telegram não configurado: defina TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env.")
    exit()

df = ler_posts(ARQUIVO_POSTS)

aprovados = df[df["status"] == "aprovado"]

if aprovados.empty:
    print("Nenhum post aprovado para enviar.")
    exit()

enviados = 0

for idx, linha in aprovados.iterrows():

    titulo = str(linha.get("titulo", "")).strip()
    post = str(linha.get("post", "")).strip()
    status_telegram = str(linha.get("status_telegram", "")).strip()

    if titulo == "" or titulo == "0" or post == "" or post == "0":
        print("Ignorado registro inválido.")
        continue

    if status_telegram == "enviado":
        print(f"Ignorado já enviado: {titulo}")
        continue

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    resposta = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": post
        },
        timeout=30
    )

    if resposta.status_code == 200:
        df.loc[idx, "status_telegram"] = "enviado"
        enviados += 1
        print(f"Enviado: {titulo}")
    else:
        print(f"Erro ao enviar: {titulo}")
        print(resposta.status_code)
        print(resposta.text)

salvar_posts(df, ARQUIVO_POSTS)

print(f"Total enviados: {enviados}")
