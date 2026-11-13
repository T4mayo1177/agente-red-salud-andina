"""Fecha y hora actual de Colombia, para que el agente sepa qué está abierto."""

from datetime import datetime, timedelta, timezone

import holidays

# Colombia está siempre en UTC-5 (no cambia de horario), así que no hace falta tzdata.
HORA_COLOMBIA = timezone(timedelta(hours=-5), "Colombia")

_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Calcula los festivos de Colombia de cualquier año, incluidos los que se trasladan al lunes.
_FESTIVOS = holidays.country_holidays("CO", language="es")


def ahora_colombia() -> datetime:
    return datetime.now(HORA_COLOMBIA)


def asesores_disponibles(momento: datetime) -> bool:
    """Call center y WhatsApp: lunes a viernes 7:00–19:00 y sábados 8:00–14:00, sin festivos."""
    if momento.date() in _FESTIVOS:
        return False
    hora = momento.hour + momento.minute / 60
    if momento.weekday() < 5:
        return 7 <= hora < 19
    if momento.weekday() == 5:
        return 8 <= hora < 14
    return False


def describir_momento(momento: datetime) -> str:
    """Texto con el día, la fecha, la hora y si es festivo. Ej.: «lunes 16 de noviembre de 2026, 09:30 (festivo: ...)»."""
    texto = (
        f"{_DIAS[momento.weekday()]} {momento.day} de {_MESES[momento.month - 1]} "
        f"de {momento.year}, {momento:%H:%M}"
    )
    festivo = _FESTIVOS.get(momento.date())
    if festivo:
        texto += f" (festivo en Colombia: {festivo})"
    else:
        texto += " (no es festivo)"
    return texto


def describir_asesores(momento: datetime) -> str:
    if asesores_disponibles(momento):
        return "Call center y WhatsApp: ABIERTOS en este momento."
    return (
        "Call center y WhatsApp: CERRADOS en este momento. Si la persona quiere hablar con alguien, "
        "díselo y dale primero el formulario en citas.redsaludandina.example (responden el siguiente día hábil)."
    )
