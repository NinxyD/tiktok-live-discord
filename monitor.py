
import asyncio
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

USERNAME = "edwin7marfps"
LIVE_URL = f"https://www.tiktok.com/@{USERNAME}/live"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip()
TEST_DISCORD = os.environ.get("TEST_DISCORD", "").lower() in {
    "true", "1", "yes"
}
STATE_FILE = Path("live_state.json")


async def check_live():
    from TikTokLive import TikTokLiveClient

    client = TikTokLiveClient(unique_id=USERNAME)
    return await client.is_live()


def get_previous_state():
    if not STATE_FILE.exists():
        return None

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("live")
    except (json.JSONDecodeError, OSError):
        return None


def save_state(live):
    STATE_FILE.write_text(
        json.dumps(
            {"username": USERNAME, "live": live},
            indent=2
        ) + "\n",
        encoding="utf-8"
    )


def send_discord_message(message):
    if not WEBHOOK:
        raise RuntimeError(
            "Falta configurar DISCORD_WEBHOOK en GitHub Secrets."
        )

    payload = {
        "content": message,
        "allowed_mentions": {"parse": ["everyone"]}
    }

    request = Request(
        WEBHOOK,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urlopen(request, timeout=20) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(
                    f"Discord respondió HTTP {response.status}."
                )

        print("Discord aceptó el mensaje correctamente.")

    except HTTPError as error:
        details = error.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"Discord respondió HTTP {error.code}: {details}"
        ) from error

    except URLError as error:
        raise RuntimeError(
            f"No se pudo contactar con Discord: {error}"
        ) from error


def send_live_notification():
    message = (
        "@everyone\n"
        "🔴 **¡ESTAMOS EN LIVE!** 🔥\n"
        "Entra y acompáñanos un rato. 👀\n"
        f"📲 {LIVE_URL}"
    )
    send_discord_message(message)


def main():
    if not WEBHOOK:
        raise RuntimeError(
            "No se encontró DISCORD_WEBHOOK. Configúralo en "
            "Settings > Secrets and variables > Actions."
        )

    # Prueba manual: no consulta TikTok ni modifica el estado.
    if TEST_DISCORD:
        send_discord_message(
            "🧪 **Prueba del webhook:** la conexión con Discord funciona."
        )
        print("Prueba del webhook completada.")
        return

    live = asyncio.run(check_live())
    previous = get_previous_state()

    print(f"Estado actual: {'LIVE' if live else 'OFFLINE'}")
    print(f"Estado anterior: {previous!r}")

    # Primera ejecución: registra el estado sin enviar una alerta.
    if previous is None:
        save_state(live)
        print("Estado inicial guardado; no se envió ninguna alerta.")
        return

    # Notificar solo al detectar OFFLINE -> LIVE.
    if live and previous is False:
        send_live_notification()
    elif live and previous is True:
        print("El directo continúa. No se repite la alerta.")
    elif not live and previous is True:
        print("El directo terminó.")
    else:
        print("La cuenta sigue offline.")

    save_state(live)


if __name__ == "__main__":
    main()
