from datetime import datetime

from agente import agent
from agente.fecha import HORA_COLOMBIA, asesores_disponibles, describir_momento


def test_dia_normal():
    texto = describir_momento(datetime(2026, 11, 12, 21, 40, tzinfo=HORA_COLOMBIA))
    assert texto == "jueves 12 de noviembre de 2026, 21:40 (no es festivo)"


def test_festivo_trasladado_al_lunes():
    # La Independencia de Cartagena (11 de noviembre) se pasa al lunes 16 en 2026.
    texto = describir_momento(datetime(2026, 11, 16, 9, 5, tzinfo=HORA_COLOMBIA))
    assert texto.startswith("lunes 16 de noviembre de 2026, 09:05 (festivo en Colombia:")


def test_asesores_disponibles():
    def en(dia, hora, minuto=0):
        return asesores_disponibles(datetime(2026, 11, dia, hora, minuto, tzinfo=HORA_COLOMBIA))

    assert en(17, 7) and en(17, 18, 59)  # martes
    assert not en(17, 6, 59) and not en(17, 19)
    assert en(14, 13, 59) and not en(14, 14)  # sábado
    assert not en(15, 10)  # domingo
    assert not en(16, 10)  # lunes festivo


def test_la_instruccion_trae_el_momento_actual():
    instruccion = agent.construir_instruccion(None)
    assert instruccion.startswith(agent.INSTRUCCION_FIJA)
    assert "# Momento actual\nAhora es " in instruccion
