import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

import main

cliente = TestClient(main.app)


class RunnerSimulado:
    """Reemplaza al Runner de ADK para no llamar a Gemini."""

    def __init__(self, texto=None, error=None):
        self.texto, self.error = texto, error

    async def run_async(self, **kwargs):
        if self.error:
            raise self.error
        parte = SimpleNamespace(text=self.texto, thought=None)
        yield SimpleNamespace(is_final_response=lambda: True, content=SimpleNamespace(parts=[parte]))


def enviar(mensaje, session_id=None):
    return cliente.post("/chat", json={"session_id": session_id or str(uuid.uuid4()), "mensaje": mensaje})


def test_health():
    assert cliente.get("/health").json() == {"ok": True}


def test_chat_devuelve_respuesta(monkeypatch):
    monkeypatch.setattr(main, "runner", RunnerSimulado(texto="Hola, ¿en qué le ayudo?"))
    respuesta = enviar("hola")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"respuesta": "Hola, ¿en qué le ayudo?"}


def test_mensaje_vacio_422():
    assert enviar("   ").status_code == 422


def test_mensaje_largo_422():
    assert enviar("a" * 1001).status_code == 422


def test_session_id_invalido_422():
    assert enviar("hola", session_id="no-es-uuid").status_code == 422


def test_error_de_gemini_da_mensaje_de_respaldo(monkeypatch):
    monkeypatch.setattr(main, "runner", RunnerSimulado(error=RuntimeError("429 cuota")))
    respuesta = enviar("hola")
    assert respuesta.status_code == 200
    assert "(601) 555 0100" in respuesta.json()["respuesta"]


class RunnerConHerramienta(RunnerSimulado):
    """Simula que el modelo llamó la herramienta de registro antes de responder."""

    async def run_async(self, **kwargs):
        llamada = SimpleNamespace(text=None, thought=None, function_call=SimpleNamespace(name="registrar_pregunta_sin_respuesta"))
        yield SimpleNamespace(is_final_response=lambda: False, content=SimpleNamespace(parts=[llamada]))
        async for evento in super().run_async(**kwargs):
            yield evento


def test_quita_lineas_vacias(monkeypatch):
    monkeypatch.setattr(main, "runner", RunnerSimulado(texto="Línea 1.  \n\nLínea 2.\n \nLínea 3."))
    assert enviar("hola").json()["respuesta"] == "Línea 1.\nLínea 2.\nLínea 3."


def test_si_dice_registrada_sin_llamar_la_herramienta_el_backend_registra(monkeypatch):
    registros = []
    monkeypatch.setattr(main, "registrar_pregunta_sin_respuesta", lambda pregunta, tema: registros.append((pregunta, tema)))
    monkeypatch.setattr(main, "runner", RunnerSimulado(texto="No tengo esa información.\nDejé registrada su pregunta para el equipo."))
    enviar("¿Cuánto vale una resonancia?")
    assert registros == [("¿Cuánto vale una resonancia?", "sin_tema")]


def test_si_el_modelo_llamo_la_herramienta_no_se_registra_dos_veces(monkeypatch):
    registros = []
    monkeypatch.setattr(main, "registrar_pregunta_sin_respuesta", lambda pregunta, tema: registros.append(pregunta))
    monkeypatch.setattr(main, "runner", RunnerConHerramienta(texto="Dejé registrada su pregunta para el equipo."))
    enviar("¿Cuánto vale una resonancia?")
    assert registros == []


def test_quita_oferta_de_cierre_pero_no_la_aclaracion(monkeypatch):
    monkeypatch.setattr(main, "runner", RunnerSimulado(texto="Los menores de 5 años no pagan.\n¿Desea conocer los canales?"))
    assert enviar("hola").json()["respuesta"] == "Los menores de 5 años no pagan."
    monkeypatch.setattr(main, "runner", RunnerSimulado(texto="Puede pedirla por WhatsApp.\n¿Para qué especialidad la necesita?"))
    assert enviar("hola").json()["respuesta"].endswith("¿Para qué especialidad la necesita?")
