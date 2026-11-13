import json
from pathlib import Path

from agente import herramientas
from almacenamiento.jsonl import RepositorioJsonl

CARPETA_AGENTE = Path(__file__).resolve().parent.parent / "agente"


def test_limpia_correos_y_numeros_largos():
    texto = "Soy ana@correo.com, cédula 1020304050, cel 300 555 0100. ¿Atienden Sanitas?"
    limpio = herramientas.limpiar_texto(texto)
    assert "ana@correo.com" not in limpio
    assert "1020304050" not in limpio
    assert "300 555 0100" not in limpio
    assert "¿Atienden Sanitas?" in limpio


def test_no_toca_numeros_cortos():
    assert herramientas.limpiar_texto("¿Cuesta $12.000 en la sede 5?") == "¿Cuesta $12.000 en la sede 5?"


def test_escribe_una_linea_jsonl(tmp_path):
    ruta = tmp_path / "sub" / "preguntas.jsonl"
    RepositorioJsonl(ruta).guardar({"id": "1", "pregunta": "¿Hacen resonancias?"})
    RepositorioJsonl(ruta).guardar({"id": "2", "pregunta": "otra"})
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2
    assert json.loads(lineas[0])["pregunta"] == "¿Hacen resonancias?"


def test_herramienta_guarda_registro_limpio(tmp_path, monkeypatch):
    ruta = tmp_path / "preguntas.jsonl"
    monkeypatch.setattr(herramientas, "obtener_repositorio", lambda: RepositorioJsonl(ruta))
    resultado = herramientas.registrar_pregunta_sin_respuesta("Mi correo es a@b.co, ¿precio particular?", "costos")
    assert resultado == {"estado": "registrada"}
    registro = json.loads(ruta.read_text(encoding="utf-8"))
    assert set(registro) == {"id", "fecha", "pregunta", "tema"}
    assert "a@b.co" not in registro["pregunta"]
    assert registro["tema"] == "costos"


def test_markdown_sin_llaves():
    # ADK interpreta {variable} en las instrucciones; los .md no deben tener llaves.
    for nombre in ("instrucciones.md", "base_conocimiento.md"):
        texto = (CARPETA_AGENTE / nombre).read_text(encoding="utf-8")
        assert "{" not in texto and "}" not in texto, nombre
