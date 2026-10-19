import time
import requests
import json


# aqui abajo colocamos la url del webhook de discord que creamos en el servidor de discord
WEBHOOK_URL = "url de prueba"


def enviar_alerta_seguridad(mensaje, contador: int):
    payload = {"content": "Prueba de webhook"}

    if (mensaje == "Nada que reportar." or mensaje == ""):
        payload = {
            "username": "Sistema de Seguridad",
            "avatar_url": "https://i.imgur.com/R3x3f3U.png",
            "embeds": [
                {
                    "title": "✅ Estado de Seguridad",
                    "description": "No se detectaron alertas de seguridad.",
                    "color": 3066993, 
                    "fields": [
                        {
                            "name": "Estado",
                            "value": "Todo en orden",
                            "inline": True,
                        },
                        {
                            "name": "Nivel de Prioridad",
                            "value": "Bajo",
                            "inline": True,
                        },
                    ],
                    "footer": {"text": "Sistema de Vigilancia Automatizado"},
                }
            ],
        }
    else:
        payload = {
            "username": "Sistema de Seguridad",
            "avatar_url": "https://i.imgur.com/R3x3f3U.png",
            "embeds": [
                {
                    "title": "🚨 ALERTA DE SEGURIDAD DETECTADA",
                    "description": mensaje,
                    "color": 15158332,
                    "fields": [
                        {
                            "name": "Estado",
                            "value": "⚠️ Requiere Atención",
                            "inline": True,
                        },
                        {
                            "name": "Nivel de Prioridad",
                            "value": "Alto",
                        "inline": True,
                        },
                    ],
                    "footer": {"text": "Sistema de Vigilancia Automatizado"},
                }
            ],
        }

    try:
        respuesta = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(respuesta.status_code, respuesta.text)
        if respuesta.status_code in (200, 204):
            print("[OK] Alerta de seguridad enviada correctamente.")
        else:
            print(
                f"[Error {respuesta.status_code}, {respuesta.text}] No se pudo enviar la alerta."
            )
    except Exception as e:
        print(f"Error de conexión: {e}")


def iniciar_monitoreo():
    print("Iniciando envío periódico de alertas de seguridad...")
    while True:
        enviar_alerta_seguridad()
        time.sleep(5)


if __name__ == "__main__":
    iniciar_monitoreo()