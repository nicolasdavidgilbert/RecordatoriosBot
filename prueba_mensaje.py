import os
import requests
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Puedes poner tu ID aquí directamente para la prueba
CHAT_ID = os.getenv("CHAT_ID_NICO")

def enviar_test(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown" # Para poder usar negritas, etc.
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ ¡Mensaje enviado con éxito!")
        else:
            print(f"❌ Error de Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    print("Enviando mensaje de prueba...")
    enviar_test("🚀 *¡Sistema de Presencia Online!* \nEl bot ya puede hablarte.")