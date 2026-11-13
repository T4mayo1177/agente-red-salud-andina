"""Interfaz común: cualquier almacenamiento debe saber guardar un registro."""

from abc import ABC, abstractmethod


class RepositorioPreguntas(ABC):
    @abstractmethod
    def guardar(self, registro: dict) -> None:
        """Guarda un registro {id, fecha, pregunta, tema}."""
