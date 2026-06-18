from dotenv import load_dotenv
import os

load_dotenv()

client_id = os.getenv("MELI_CLIENT_ID")

redirect_uri = "https://example.com/"

url = (
    "https://auth.mercadolivre.com.br/authorization"
    f"?response_type=code"
    f"&client_id={client_id}"
    f"&redirect_uri={redirect_uri}"
)

print("Abra este link no navegador:")
print(url)