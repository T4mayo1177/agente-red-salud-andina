"""Herramienta que el agente usa cuando una pregunta no está en la base."""

import logging
import re
import uuid
from datetime import datetime, timezone

from almacenamiento import obtener_repositorio

logger = logging.getLogger("red_salud_andina")

# Correos y números largos (documentos, teléfonos) se reemplazan antes de guardar.
_CORREO = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_NUMERO_LARGO = re.compile(r"\d(?:[\s.-]?\d){5,}")  # 6 o más dígitos, con o sin separadores


def limpiar_texto(texto: str) -> str:
    """Quita correos y secuencias de 6 o más dígitos."""
    texto = _CORREO.sub("[dato omitido]", texto)
    texto = _NUMERO_LARGO.sub("[dato omitido]", texto)
    return texto.strip()


def registrar_pregunta_sin_respuesta(pregunta: str, tema: str) -> dict:
    """Registra una pregunta que no se puede responder con la base de conocimiento.

    Úsala solo cuando la información NO está en la base, para que el equipo de
    Red Salud Andina la revise y complete la base. No la uses para trámites que
    ya sabes derivar, consejo médico ni temas ajenos a Red Salud Andina.

    Args:
        pregunta: La pregunta de la persona, reescrita sin datos personales
            (sin nombres, documentos, teléfonos, correos ni diagnósticos).
        tema: Tema corto, por ejemplo "costos", "servicios", "sedes" o "aseguradoras".

    Returns:
        Un diccionario con "estado": "registrada" si se guardó, o
        "no_registrada" si hubo un problema al guardar.
    """
    registro = {
        "id": str(uuid.uuid4()),
        "fecha": datetime.now(timezone.utc).isoformat(),
        "pregunta": limpiar_texto(pregunta),
        "tema": limpiar_texto(tema),
    }
    try:
        obtener_repositorio().guardar(registro)
    except Exception as error:
        logger.error("No se pudo registrar la pregunta: %s", type(error).__name__)
        return {"estado": "no_registrada"}
    return {"estado": "registrada"}
