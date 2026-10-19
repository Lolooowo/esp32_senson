import os
from ipaddress import IPv4Address
from alerta import enviar_alerta_seguridad
import mysql.connector
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

app = FastAPI(title="Monitoreo ESP32")

DB_CONFIG = {
    "host": "localhost",
    "user": "esp32",
    "password": os.environ["ESP32_DB_PASSWORD"],
    "database": "monitoreo",
    "connection_timeout": 5,
}


class Medicion(BaseModel):
    dispositivo: str = Field(min_length=1, max_length=50)
    temperatura: float | None = Field(default=None, ge=-40, le=80)
    humedad: float | None = Field(default=None, ge=0, le=100)
    ip_destino: IPv4Address
    ping_exitoso: bool
    ping_promedio_ms: float | None = Field(default=None, ge=0)


@app.get("/")
def inicio():
    return {"mensaje": "API de monitoreo ESP32 activa"}

@app.get("/mediciones")
def obtener_mediciones(
    limite: int = Query(default=100, ge=1, le=1000),
    desplazamiento: int = Query(default=0, ge=0),
    dispositivo: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
):
    conexion = None
    cursor = None

    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        cursor = conexion.cursor(dictionary=True)

        consulta = """
            SELECT
                id,
                dispositivo,
                fecha_recepcion,
                temperatura,
                humedad,
                ip_destino,
                ping_exitoso,
                ping_promedio_ms
            FROM mediciones
        """

        parametros = []

        if dispositivo is not None:
            consulta += " WHERE dispositivo = %s"
            parametros.append(dispositivo)

        consulta += """
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """

        parametros.extend([limite, desplazamiento])

        cursor.execute(consulta, tuple(parametros))
        registros = cursor.fetchall()

        for registro in registros:
            registro["ping_exitoso"] = bool(registro["ping_exitoso"])

        return {
            "cantidad": len(registros),
            "limite": limite,
            "desplazamiento": desplazamiento,
            "datos": registros,
        }

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="No se pudieron consultar las mediciones en MySQL",
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()

@app.post("/mediciones")
def verificar_medicion(datos: Medicion, response: Response):
    alerta, contador = mensaje(datos)
    if alerta == "Nada que reportar.":
        return {"mensaje": "Medición verificada; sin alertas y no se guardó"}, enviar_alerta_seguridad(alerta, contador)
    
    enviar_alerta_seguridad(alerta, contador)
    resultado = guardar_medicion(datos)
    response.status_code = 201
    return resultado


def guardar_medicion(datos: Medicion):
    conexion = None
    cursor = None

    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        cursor = conexion.cursor()

        consulta = """
            INSERT INTO mediciones (
                dispositivo,
                fecha_recepcion,
                temperatura,
                humedad,
                ip_destino,
                ping_exitoso,
                ping_promedio_ms
            ) VALUES (
                %s, NOW(), %s, %s, %s, %s, %s
            )
        """

        cursor.execute(
            consulta,
            (
                datos.dispositivo,
                datos.temperatura,
                datos.humedad,
                str(datos.ip_destino),
                datos.ping_exitoso,
                datos.ping_promedio_ms,
            ),
        )

        conexion.commit()

        return {"mensaje": "Medición guardada correctamente"}

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="No se pudo guardar la medición en MySQL",
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


def mensaje(datos: Medicion):
    mensajes_alerta = []
    contador= 0

    if not datos.ping_exitoso:
        contador += 1
        mensajes_alerta.append(
            f"El dispositivo {datos.dispositivo} no puede hacer ping "
            f"a la IP {datos.ip_destino}."
        )
    if datos.ping_promedio_ms is None or datos.ping_promedio_ms > 100:
        contador += 1
        mensajes_alerta.append(
            f"El ping promedio de {datos.ping_promedio_ms} ms es demasiado alto."
        )
    if datos.temperatura is None or (
        datos.temperatura < 10 or datos.temperatura > 27
    ):
        contador += 1
        mensajes_alerta.append(
            f"La temperatura {datos.temperatura}°C está fuera del rango "
            "permitido (10°C a 27°C)."
        )
    if datos.humedad is None or (datos.humedad < 50 or datos.humedad > 75):
        contador += 1
        mensajes_alerta.append(
            f"La humedad {datos.humedad}% está fuera del rango permitido "
            "(50% a 75%)."
        )

    if not mensajes_alerta:
        return "Nada que reportar.", 0
    return " ".join(mensajes_alerta), contador
    