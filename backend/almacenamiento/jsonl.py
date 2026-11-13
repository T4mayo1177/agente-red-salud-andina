"""Almacenamiento local: una línea JSON por pregunta sin respuesta."""

import json
from pathlib import Path

from .base import RepositorioPreguntas

RUTA_POR_DEFECTO = Path(__file__).resolve().parent.parent / "data" / "preguntas_sin_respuesta.jsonl"


class RepositorioJsonl(RepositorioPreguntas):
    def __init__(self, ruta: Path = RUTA_POR_DEFECTO):
        self.ruta = Path(ruta)

    def guardar(self, registro: dict) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self.ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
