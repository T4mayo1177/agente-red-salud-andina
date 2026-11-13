"""El modelo de respaldo entra cuando el principal agota su cuota (429)."""

import asyncio
from types import SimpleNamespace

import pytest
from google.adk.models import Gemini
from google.adk.models.llm_request import LlmRequest
from google.genai.errors import ClientError

from agente import modelo
from agente.modelo import GeminiConRespaldo


@pytest.fixture
def llamadas(monkeypatch):
    usados = []

    async def falso(self, llm_request, stream=False):
        usados.append(llm_request.model)
        if llm_request.model == "principal":
            raise ClientError(429, {"error": {"code": 429, "message": "cuota", "status": "RESOURCE_EXHAUSTED"}})
        yield SimpleNamespace(texto="ok desde " + llm_request.model)

    monkeypatch.setattr(Gemini, "generate_content_async", falso)
    monkeypatch.setattr(modelo, "_principal_agotado_hasta", 0.0)
    return usados


def correr(llm):
    async def todo():
        return [r async for r in llm.generate_content_async(LlmRequest(model=llm.model))]
    return asyncio.run(todo())


def test_si_el_principal_da_429_responde_el_respaldo(llamadas):
    llm = GeminiConRespaldo(model="principal", modelo_respaldo="respaldo")
    assert correr(llm)[0].texto == "ok desde respaldo"
    assert llamadas == ["principal", "respaldo"]


def test_despues_del_429_va_directo_al_respaldo(llamadas):
    llm = GeminiConRespaldo(model="principal", modelo_respaldo="respaldo")
    correr(llm)
    correr(llm)
    assert llamadas == ["principal", "respaldo", "respaldo"]


def test_sin_respaldo_el_error_sube(llamadas):
    llm = GeminiConRespaldo(model="principal")
    with pytest.raises(ClientError):
        correr(llm)
