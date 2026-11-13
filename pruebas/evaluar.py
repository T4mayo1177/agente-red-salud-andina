"""Corre las pruebas de evaluacion.json contra el agente real y guarda todo lo observable.

Uso (desde la carpeta del proyecto, con la clave en el .env):
    backend\\.venv\\Scripts\\python pruebas\\evaluar.py [--pausa 13]

Por cada mensaje registra: la categoría que eligió el gateway, si el agente llamó la
herramienta de registro (o si lo hizo el backend como respaldo), lo que se guardó,
la respuesta, sus líneas, palabras y segundos. Los registros de esta corrida NO van al
JSONL real: se guardan en el resultado. Salida: pruebas/resultados/evaluacion_<fecha>.jsonl
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA.parent / "backend"))

import main  # noqa: E402  (carga el .env y el agente)
from agente import gateway as gw  # noqa: E402
from agente import herramientas  # noqa: E402

estado = {}


async def clasificar_y_anotar(texto, _original=gw.clasificar):
    categoria = await _original(texto)
    estado["gateway"] = categoria.value
    return categoria


class RepoDePrueba:
    def guardar(self, registro):
        estado.setdefault("registros", []).append(registro)


def registro_de_respaldo(pregunta, tema, _original=main.registrar_pregunta_sin_respuesta):
    estado["registro_backend"] = True
    return _original(pregunta, tema)


gw.clasificar = clasificar_y_anotar
herramientas.obtener_repositorio = lambda: RepoDePrueba()
main.registrar_pregunta_sin_respuesta = registro_de_respaldo


def revisar(caso, respuesta):
    """Chequeos automáticos de texto; la calificación final la hace una persona."""
    texto = respuesta.lower()
    faltan = [p for p in caso.get("debe_incluir", []) if not re.search(p, texto, re.I)]
    sobran = [p for p in caso.get("no_debe_incluir", []) if re.search(p, respuesta, re.I)]
    return faltan, sobran


async def correr(pausa):
    casos = json.loads((CARPETA / "evaluacion.json").read_text(encoding="utf-8"))
    salida = CARPETA / "resultados" / f"evaluacion_{datetime.now():%Y-%m-%d_%H%M%S}.jsonl"
    salida.parent.mkdir(exist_ok=True)
    with salida.open("w", encoding="utf-8") as archivo:
        for caso in casos:
            sesion = str(uuid.uuid4())
            turnos = []
            for mensaje in caso["mensajes"]:
                estado.clear()
                inicio = time.time()
                try:
                    respuesta = await main.responder(sesion, mensaje)
                except Exception as error:
                    respuesta = f"ERROR {type(error).__name__} {getattr(error, 'code', '')}"
                respuesta = respuesta or main.MENSAJE_RESPALDO
                turnos.append({
                    "mensaje": mensaje,
                    "respuesta": respuesta,
                    "gateway": estado.get("gateway", "no_disponible"),
                    "registro_agente": bool(estado.get("registros")) and not estado.get("registro_backend"),
                    "registro_backend": bool(estado.get("registro_backend")),
                    "registros": estado.get("registros", []),
                    "lineas": len(respuesta.splitlines()),
                    "palabras": len(respuesta.split()),
                    "segundos": round(time.time() - inicio, 1),
                })
                await asyncio.sleep(pausa)
            faltan, sobran = revisar(caso, turnos[-1]["respuesta"])
            fila = {**caso, "turnos": turnos, "chequeo_faltan": faltan, "chequeo_sobran": sobran,
                    "gateway_ok": turnos[0]["gateway"] == caso["gateway"]}
            archivo.write(json.dumps(fila, ensure_ascii=False) + "\n")
            archivo.flush()
            print(f"[{caso['id']}] gateway={turnos[0]['gateway']} (esperado {caso['gateway']}) "
                  f"registro={'sí' if any(t['registros'] for t in turnos) else 'no'} faltan={faltan} sobran={sobran}", flush=True)
            for t in turnos:
                print(f"   > {t['mensaje']}\n   < {t['respuesta'].replace(chr(10), ' | ')}  [{t['lineas']}L {t['palabras']}P {t['segundos']}s]", flush=True)
    print(f"\nResultados en {salida}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pausa", type=float, default=13, help="segundos entre mensajes (cuota de 15 por minuto)")
    asyncio.run(correr(parser.parse_args().pausa))
