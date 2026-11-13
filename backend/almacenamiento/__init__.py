"""Elige dónde se guardan las preguntas sin respuesta según STORAGE_BACKEND."""

import os

from .base import RepositorioPreguntas


def obtener_repositorio() -> RepositorioPreguntas:
    tipo = os.getenv("STORAGE_BACKEND", "jsonl").lower()
    if tipo == "firestore":
        from .firestore import RepositorioFirestore

        return RepositorioFirestore()
    from .jsonl import RepositorioJsonl

    return RepositorioJsonl()
