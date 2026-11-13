"""Define el agente: gateway, modelo, instrucciones + base de conocimiento y herramienta."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.genai import types

_CARPETA = Path(__file__).resolve().parent


def buscar_env() -> Path | None:
    """Primero backend/.env; si no existe, el .env más cercano subiendo carpetas."""
    backend = _CARPETA.parent
    for carpeta in [backend, *backend.parents]:
        if (carpeta / ".env").is_file():
            return carpeta / ".env"
    return None


_ENV = buscar_env()
if _ENV:
    load_dotenv(_ENV)

from .fecha import ahora_colombia, describir_asesores, describir_momento  # noqa: E402
from .gateway import gateway  # noqa: E402
from .herramientas import registrar_pregunta_sin_respuesta  # noqa: E402
from .modelo import GeminiConRespaldo  # noqa: E402

# Flash-Lite: ~500 solicitudes/día gratis (Flash solo da 20). Verifique en aistudio.google.com/rate-limit.
MODELO_POR_DEFECTO = "gemini-3.5-flash-lite"
# Si el principal agota su cuota (429), responde este, que tiene cuota propia.
MODELO_RESPALDO_POR_DEFECTO = "gemini-3.1-flash-lite"

reglas_seguridad = (_CARPETA / "reglas_seguridad.md").read_text(encoding="utf-8")
instrucciones = (_CARPETA / "instrucciones.md").read_text(encoding="utf-8")
base_conocimiento = (_CARPETA / "base_conocimiento.md").read_text(encoding="utf-8")

# Las reglas de seguridad van primero: tienen prioridad sobre todo lo demás.
INSTRUCCION_FIJA = reglas_seguridad + "\n\n" + instrucciones + "\n\n# Base de conocimiento\n" + base_conocimiento


def construir_instruccion(_contexto) -> str:
    """Se ejecuta en cada turno: agrega la fecha y hora actual de Colombia al final."""
    ahora = ahora_colombia()
    return (
        INSTRUCCION_FIJA
        + "\n\n# Momento actual\nAhora es " + describir_momento(ahora) + ".\n"
        + describir_asesores(ahora) + "\n"
    )

# Si Gemini está saturado (503) o falla en el servidor, reintenta hasta 3 veces esperando
# 2, 4 y 8 segundos. El 429 (cuota agotada) no se reintenta: pasa de una al modelo de respaldo.
REINTENTOS = types.HttpRetryOptions(
    attempts=4,
    initial_delay=2,
    max_delay=8,
    http_status_codes=[500, 503, 504],
)

root_agent = LlmAgent(
    name="asistente_red_salud_andina",
    model=GeminiConRespaldo(
        model=os.getenv("GEMINI_MODEL") or MODELO_POR_DEFECTO,
        modelo_respaldo=os.getenv("GEMINI_MODEL_RESPALDO") or MODELO_RESPALDO_POR_DEFECTO,
        retry_options=REINTENTOS,
    ),
    instruction=construir_instruccion,
    tools=[registrar_pregunta_sin_respuesta],
    # Razonamiento bajo: en las pruebas, sin él Flash-Lite decía «quedó registrada» sin llamar
    # la herramienta; con él la llamó siempre. Cuesta 1–3 s más por respuesta.
    # Temperatura baja: la misma pregunta debe recibir la misma respuesta completa.
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_level=os.getenv("GEMINI_THINKING") or "LOW"),
    ),
    before_agent_callback=gateway,  # un modelo pequeño filtra los casos especiales
)
