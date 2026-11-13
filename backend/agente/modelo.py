"""Modelo del agente con respaldo: si se agota la cuota del principal, responde otro modelo.

La cuota gratuita de Gemini se cuenta por modelo. Si el principal responde 429 (cuota
por minuto o por día agotada), la misma petición se envía al modelo de respaldo, que tiene
su propia cuota, y durante unos minutos se usa directamente el respaldo para no gastar
una llamada fallida en cada mensaje.
"""

import logging
import time

from google.adk.models import Gemini
from google.genai.errors import ClientError

logger = logging.getLogger("red_salud_andina")

PAUSA_PRINCIPAL = 600  # segundos que se usa solo el respaldo después de un 429

_principal_agotado_hasta = 0.0


class GeminiConRespaldo(Gemini):
    modelo_respaldo: str | None = None

    async def generate_content_async(self, llm_request, stream: bool = False):
        global _principal_agotado_hasta
        if not self.modelo_respaldo or time.monotonic() >= _principal_agotado_hasta:
            try:
                async for respuesta in super().generate_content_async(llm_request, stream):
                    yield respuesta
                return
            except ClientError as error:
                if error.code != 429 or not self.modelo_respaldo:
                    raise
                logger.warning("Cuota agotada en %s; responde %s", llm_request.model, self.modelo_respaldo)
                _principal_agotado_hasta = time.monotonic() + PAUSA_PRINCIPAL

        peticion = llm_request.model_copy(deep=True)
        peticion.model = self.modelo_respaldo
        async for respuesta in super().generate_content_async(peticion, stream):
            yield respuesta
