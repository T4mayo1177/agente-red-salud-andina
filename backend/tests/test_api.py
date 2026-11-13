import asyncio
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


def test_respaldo_de_noche_ofrece_primero_el_formulario(monkeypatch):
    monkeypatch.setattr(main, "asesores_disponibles", lambda momento: False)
    monkeypatch.setattr(main, "runner", RunnerSimulado(error=RuntimeError("429 cuota")))
    texto = enviar("hola").json()["respuesta"]
    assert "formulario" in texto.splitlines()[1]


def test_respaldo_en_horario_ofrece_asesor(monkeypatch):
    monkeypatch.setattr(main, "asesores_disponibles", lambda momento: True)
    monkeypatch.setattr(main, "runner", RunnerSimulado(error=RuntimeError("429 cuota")))
    assert "asesor le atiende ahora" in enviar("hola").json()["respuesta"]


def test_si_no_era_pregunta_no_registra_y_quita_la_frase(monkeypatch):
    registros = []
    monkeypatch.setattr(main, "registrar_pregunta_sin_respuesta", lambda pregunta, tema: registros.append(pregunta))
    monkeypatch.setattr(main, "runner", RunnerSimulado(texto="No tengo esa información.\nDejé registrada su pregunta para el equipo."))
    assert enviar("es para mi mamá").json()["respuesta"] == "No tengo esa información."
    assert registros == []


def test_si_tarda_demasiado_da_el_mensaje_de_respaldo(monkeypatch):
    class RunnerLento(RunnerSimulado):
        async def run_async(self, **kwargs):
            await asyncio.sleep(1)
            yield SimpleNamespace(is_final_response=lambda: True, content=SimpleNamespace(parts=[]))
    monkeypatch.setattr(main, "ESPERA_MAXIMA", 0.1)
    monkeypatch.setattr(main, "runner", RunnerLento())
    assert "(601) 555 0100" in enviar("hola").json()["respuesta"]


def test_si_dice_que_no_sabe_y_no_registro_el_backend_registra(monkeypatch):
    registros = []
    monkeypatch.setattr(main, "registrar_pregunta_sin_respuesta", lambda pregunta, tema: registros.append(pregunta))
    monkeypatch.setattr(main, "runner", RunnerSimulado(texto="No tengo información sobre nutrición.\nWhatsApp +57 300 555 0100."))
    enviar("¿Tienen servicio de nutrición?")
    assert registros == ["¿Tienen servicio de nutrición?"]


def test_si_dice_que_no_sabe_pero_no_era_pregunta_no_registra(monkeypatch):
    registros = []
    monkeypatch.setattr(main, "registrar_pregunta_sin_respuesta", lambda pregunta, tema: registros.append(pregunta))
    monkeypatch.setattr(main, "runner", RunnerSimulado(texto="No tengo esa información."))
    enviar("es para mi mamá")
    assert registros == []
