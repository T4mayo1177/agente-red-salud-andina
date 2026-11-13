"""Almacenamiento en Google Cloud (Firestore). Solo se usa con STORAGE_BACKEND=firestore."""

from .base import RepositorioPreguntas


class RepositorioFirestore(RepositorioPreguntas):
    def __init__(self, coleccion: str = "preguntas_sin_respuesta"):
        from google.cloud import firestore  # import perezoso: en local no se carga

        self.coleccion = firestore.Client().collection(coleccion)

    def guardar(self, registro: dict) -> None:
        self.coleccion.document(registro["id"]).set(registro)
