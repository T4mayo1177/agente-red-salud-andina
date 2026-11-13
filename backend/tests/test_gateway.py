"""Pruebas del gateway con el clasificador simulado (no llaman a Gemini)."""

import asyncio
import uuid
from types import SimpleNamespace

import pytest
from google.genai import types

import main
from agente import gateway as gw
from agente.gateway import Categoria


def contexto(texto):
    return SimpleNamespace(user_content=types.Content(role="user", parts=[types.Part(text=texto)]))


def simular(monkeypatch, categoria=None, error=None):
    async def clasificar_falso(texto):
        if error:
            raise error
        return categoria

    monkeypatch.setattr(gw, "clasificar", clasificar_falso)


@pytest.mark.parametrize("categoria", list(gw.RESPUESTAS_FIJAS))
def test_categorias_especiales_dan_respuesta_fija(monkeypatch, categoria):
    simular(monkeypatch, categoria)
    resultado = asyncio.run(gw.gateway(contexto("mensaje")))
    assert resultado.parts[0].text == gw.RESPUESTAS_FIJAS[categoria]


def test_respuestas_fijas_de_maximo_4_lineas():
    for texto in gw.RESPUESTAS_FIJAS.values():
        assert len(texto.splitlines()) <= 4


def test_urgencia_menciona_123():
    assert "123" in gw.RESPUESTAS_FIJAS[Categoria.URGENCIA]


def test_normal_sigue_al_agente(monkeypatch):
    simular(monkeypatch, Categoria.NORMAL)
    assert asyncio.run(gw.gateway(contexto("¿Qué horario tiene la sede Norte?"))) is None


def test_si_el_clasificador_falla_sigue_al_agente(monkeypatch):
    simular(monkeypatch, error=RuntimeError("429 cuota"))
    assert asyncio.run(gw.gateway(contexto("hola"))) is None


def test_runner_real_no_llama_al_agente_principal_en_urgencia(monkeypatch):
    """Por el Runner de ADK de verdad: con urgencia, la respuesta fija sale sin llamar a Gemini."""
    simular(monkeypatch, Categoria.URGENCIA)
    texto = asyncio.run(main.responder(str(uuid.uuid4()), "Mi papá no reacciona"))
    assert texto == gw.RESPUESTAS_FIJAS[Categoria.URGENCIA]
