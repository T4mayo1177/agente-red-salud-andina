"""Envía los casos de casos.json al backend y guarda las respuestas.

Uso (con el backend corriendo):
    python pruebas/correr_casos.py [--url http://localhost:8080] [--pausa 6]

Cada caso usa una sesión nueva. Si el caso tiene "seguimiento", ese segundo mensaje
se envía en la misma sesión. El resultado queda en pruebas/resultados/<fecha>.jsonl
con la pregunta, la respuesta, su número de líneas y palabras. Una persona compara
cada respuesta con el campo "esperado" al revisar el archivo.
"""

import argparse
import json
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

CARPETA = Path(__file__).resolve().parent


def preguntar(url: str, session_id: str, mensaje: str) -> str:
    cuerpo = json.dumps({"session_id": session_id, "mensaje": mensaje}).encode("utf-8")
    peticion = urllib.request.Request(f"{url}/chat", data=cuerpo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))["respuesta"]


def enviar(url: str, session_id: str, mensaje: str) -> str:
    """Como preguntar(), pero si falla devuelve el tipo de error en lugar de detener la corrida."""
    try:
        return preguntar(url, session_id, mensaje)
    except Exception as error:
        return f"ERROR: {type(error).__name__}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--pausa", type=float, default=6, help="segundos entre casos (cuota gratuita)")
    args = parser.parse_args()

    casos = json.loads((CARPETA / "casos.json").read_text(encoding="utf-8"))
    salida = CARPETA / "resultados" / f"{datetime.now():%Y-%m-%d_%H%M%S}.jsonl"
    salida.parent.mkdir(exist_ok=True)

    with salida.open("w", encoding="utf-8") as archivo:
        for i, caso in enumerate(casos):
            if i:
                time.sleep(args.pausa)
            session_id = str(uuid.uuid4())
            respuesta = enviar(args.url, session_id, caso["pregunta"])
            fila = {**caso, "respuesta": respuesta, "lineas": len(respuesta.strip().splitlines()), "palabras": len(respuesta.split())}
            if caso.get("seguimiento"):
                time.sleep(args.pausa)
                fila["respuesta_seguimiento"] = enviar(args.url, session_id, caso["seguimiento"])
            archivo.write(json.dumps(fila, ensure_ascii=False) + "\n")
            print(f"[{caso['id']}] {fila['lineas']} líneas | {caso['pregunta']}\n    {respuesta}\n")
            if "respuesta_seguimiento" in fila:
                print(f"    > {caso['seguimiento']}\n    {fila['respuesta_seguimiento']}\n")

    print(f"Resultados guardados en {salida}")


if __name__ == "__main__":
    main()
