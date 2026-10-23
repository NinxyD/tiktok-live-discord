import os
import json
import asyncio
from datetime import datetime, timezone
import requests
from TikTokLive import TikTokLiveClient

# Configuración del usuario y Webhook
TIKTOK_USERNAME = "edwin7marfps"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
STATE_FILE = "live_state.json"

client = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

async def check_live():
    """Consulta la API de TikTok para verificar si la cuenta está en directo."""
    try:
        return await client.is_live()
    except Exception as e:
        print(f"⚠️ Error o respuesta no válida de TikTok: {e}")
        return None

def load_state():
    """Carga el estado anterior desde el archivo JSON."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ No se pudo leer {STATE_FILE}: {e}")
    return {"is_live": False, "last_notified": None}

def save_state(is_live, last_notified=None):
    """Guarda el estado actual en el archivo JSON."""
    state = {
        "is_live": is_live,
        "last_notified": last_notified
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def send_discord_notification():
    """Envía la alerta a Discord."""
    if not DISCORD_WEBHOOK_URL:
        print("❌ Error: No se ha configurado DISCORD_WEBHOOK.")
        return False

    payload = {
        "content": f"🔴 **¡@everyone EN VIVO EN TIKTOK!** 🔴\n\n**{TIKTOK_USERNAME}** acaba de iniciar transmisión.\n\n👉 ¡Entra a verlo aquí!: https://www.tiktok.com/@{TIKTOK_USERNAME}/live"
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code in [200, 204]:
            print("✅ Notificación enviada con éxito a Discord.")
            return True
        else:
            print(f"❌ Error al enviar a Discord ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"❌ Excepción al contactar a Discord: {e}")
        return False

def main():
    print(f"🔍 Comprobando estado para @{TIKTOK_USERNAME}...")

    # Verificar si es una ejecución manual de prueba desde GitHub
    is_test = os.environ.get("TEST_DISCORD", "false").lower() == "true"
    if is_test:
        print("🧪 Modo de prueba activado. Enviando notificación de prueba a Discord...")
        send_discord_notification()
        return

    # Consultar TikTok
    is_currently_live = asyncio.run(check_live())

    # Caso 1: TikTok dio error de respuesta (JSON/Bloqueo)
    if is_currently_live is None:
        print("⚠️ No se pudo confirmar el estado en esta revisión (TikTok no respondió correctamente). Se mantiene el estado anterior y se reintentará en 5 minutos.")
        return  # Sale sin tocar live_state.json ni marcar error en GitHub

    # Cargar estado guardado
    previous_state = load_state()
    was_live = previous_state.get("is_live", False)
    last_notified = previous_state.get("last_notified")

    # Obtener fecha/hora actual estándar en UTC
    now_utc = datetime.now(timezone.utc).isoformat()

    print(f"Estado actual: {'LIVE' if is_currently_live else 'OFFLINE'}")
    print(f"Estado anterior: {'LIVE' if was_live else 'OFFLINE'}")

    # Caso 2: Transición de OFFLINE a LIVE (Inicio de directo)
    if is_currently_live and not was_live:
        print("🚨 ¡Nuevo directo detectado! Enviando notificación...")
        success = send_discord_notification()
        if success:
            save_state(is_live=True, last_notified=now_utc)
        else:
            # Si falló la notificación a Discord, conservamos el estado para reintentar
            save_state(is_live=False, last_notified=last_notified)

    # Caso 3: Sigue en vivo o se apagó
    else:
        if not is_currently_live and was_live:
            print("🔴 El directo ha finalizado. Actualizando estado a OFFLINE.")
        else:
            print("ℹ️ La cuenta permanece en el mismo estado. Sin cambios.")

        save_state(is_live=is_currently_live, last_notified=last_notified)

if __name__ == "__main__":
    main()
