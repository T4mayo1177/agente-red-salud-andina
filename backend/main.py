"""API del agente: POST /chat y GET /health."""

import logging
import os
import uuid
from typing import Annotated

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, StringConstraints

from agente.agent import root_agent  # también carga el .env
from agente.herramientas import registrar_pregunta_sin_respuesta

logger = logging.getLogger("red_salud_andina")
logging.basicConfig(level=logging.INFO)

APP_NAME = "agente"  # igual al nombre de la carpeta del agente
USUARIO = "anonimo"  # no identificamos a nadie

MENSAJE_RESPALDO = (
    "Lo siento, en este momento no puedo responder. Puede comunicarse con un asesor "
    "en el call center (601) 555 0100 o por WhatsApp al +57 300 555 0100, de lunes a "
    "viernes de 7:00 a 19:00 y sábados de 8:00 a 14:00. Fuera de ese horario, use el "
    "formulario de contacto en citas.redsaludandina.example; responden el siguiente día hábil."
)

servicio_sesiones = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=servicio_sesiones)

app = FastAPI(title="Asistente Red Salud Andina")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class PeticionChat(BaseModel):
    session_id: uuid.UUID
    mensaje: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class RespuestaChat(BaseModel):
    respuesta: str


async def responder(session_id: str, mensaje: str) -> str:
    """Envía el mensaje al agente y devuelve el texto de su respuesta final."""
    sesion = await servicio_sesiones.get_session(app_name=APP_NAME, user_id=USUARIO, session_id=session_id)
    if sesion is None:
        await servicio_sesiones.create_session(app_name=APP_NAME, user_id=USUARIO, session_id=session_id)

    contenido = types.Content(role="user", parts=[types.Part(text=mensaje)])
    texto = ""
    uso_registro = False
    async for evento in runner.run_async(user_id=USUARIO, session_id=session_id, new_message=contenido):
        partes = (evento.content.parts if evento.content else None) or []
        for parte in partes:
            llamada = getattr(parte, "function_call", None)
            if llamada and llamada.name == "registrar_pregunta_sin_respuesta":
                uso_registro = True
        if evento.is_final_response() and partes:
            texto = "".join(p.text for p in partes if p.text and not p.thought)

    texto = quitar_pregunta_de_cierre(quitar_lineas_vacias(texto))
    if dice_que_registro(texto) and not uso_registro:
        # El modelo dijo «quedó registrada» sin llamar la herramienta: se registra aquí
        # para que lo que le dijimos a la persona sea cierto.
        logger.warning("Registro hecho por el backend: el modelo no llamó la herramienta")
        registrar_pregunta_sin_respuesta(mensaje, "sin_tema")
    return texto


def quitar_lineas_vacias(texto: str) -> str:
    """Quita líneas en blanco y espacios sobrantes para respetar el máximo de 4 líneas."""
    return "\n".join(linea.strip() for linea in texto.splitlines() if linea.strip())


# Ofertas que el modelo agrega al final aunque ya respondió. Las preguntas de aclaración
# («¿Para qué especialidad...?», «¿Qué sede...?») no empiezan así y no se tocan.
OFERTAS_DE_CIERRE = ("¿desea", "¿necesita", "¿quiere", "¿le gustaría", "¿le ayudo", "¿algo más")


def quitar_pregunta_de_cierre(texto: str) -> str:
    """Quita la última línea si es una oferta genérica y la respuesta ya tiene contenido."""
    lineas = texto.split("\n")
    if len(lineas) > 1 and lineas[-1].lower().startswith(OFERTAS_DE_CIERRE):
        lineas = lineas[:-1]
    return "\n".join(lineas)


def dice_que_registro(texto: str) -> bool:
    texto = texto.lower()
    return "registrad" in texto and "pregunta" in texto and "no quedó registrada" not in texto


@app.post("/chat", response_model=RespuestaChat)
async def chat(peticion: PeticionChat) -> RespuestaChat:
    try:
        texto = await responder(str(peticion.session_id), peticion.mensaje)
    except Exception as error:
        # Solo el tipo de error: nunca el texto que escribió la persona.
        logger.error("No se pudo generar la respuesta: %s %s", type(error).__name__, getattr(error, "code", ""))
        texto = ""
    return RespuestaChat(respuesta=texto or MENSAJE_RESPALDO)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8080")))
