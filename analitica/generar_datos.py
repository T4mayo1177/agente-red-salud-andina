"""Arma los archivos de la analítica a partir de la última corrida de pruebas/evaluar.py.

Uso: python analitica/generar_datos.py
Lee pruebas/resultados/evaluacion_*.jsonl (la más reciente) y analitica/calificacion.json,
y escribe analitica/datos/{pruebas,call_center,supuestos,quejas}.json.
Las cifras del call center y de las quejas son las del anexo del enunciado.
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "analitica" / "datos"
TIPOS = {"en_anexo": "En el anexo", "fuera_anexo": "Fuera del anexo", "ambigua": "Ambigua",
         "adversarial": "Intenta que falle", "gateway": "Prueba del gateway"}


def pruebas():
    corrida = sorted((RAIZ / "pruebas" / "resultados").glob("evaluacion_*.jsonl"))[-1]
    calif = json.loads((RAIZ / "analitica" / "calificacion.json").read_text(encoding="utf-8"))
    innecesarios = set(calif["_registro_innecesario"])
    filas = []
    for linea in corrida.read_text(encoding="utf-8").splitlines():
        caso = json.loads(linea)
        turnos = caso["turnos"]
        registros = [r for t in turnos for r in t["registros"]]
        c = calif[caso["id"]]
        filas.append({
            "id": caso["id"],
            "tipo": TIPOS[caso["tipo"]],
            "motivo": caso["motivo"],
            "pregunta": caso["mensajes"][0],
            "trampa": caso["trampa"],
            "respuesta": turnos[0]["respuesta"],
            "veredicto": c["veredicto"],
            "accion": c["accion"],
            "detalle": c["detalle"],
            "gateway_esperado": caso["gateway"],
            "gateway_observado": turnos[0]["gateway"],
            "gateway_ok": caso["gateway_ok"],
            "registro": "Sí" if registros else "No",
            "registro_justificado": "No aplica" if not registros else ("No" if caso["id"] in innecesarios else "Sí"),
            "registro_por": "Agente" if any(t["registro_agente"] for t in turnos) else ("Backend" if any(t["registro_backend"] for t in turnos) else ""),
            "pregunta_registrada": registros[0]["pregunta"] if registros else "",
            "tema_registrado": registros[0]["tema"] if registros else "",
            "mensajes_hasta_resolver": len(turnos),
            "lineas_max": max(t["lineas"] for t in turnos),
            "palabras": turnos[0]["palabras"],
            "segundos": turnos[0]["segundos"],
            "informativa": caso["motivo"] in {"Horarios y ubicación", "Requisitos", "Cuotas y costos"}
                           and caso["tipo"] in {"en_anexo", "ambigua", "gateway"},
        })
    meta = [{"label": "Corrida", "value": corrida.name},
            {"label": "Cómo se generó", "value": "pruebas/evaluar.py contra Gemini (gemini-3.5-flash-lite) el 12/11/2026; calificación manual en analitica/calificacion.json"}]
    return {"rows": filas, "meta": meta}


CALL_CENTER = [
    # motivo, %, llamadas/día, minutos, resueltas 1a llamada, alcance del agente
    ("Horarios y ubicación", 14, 126, 2.5, 95, "Informativa: el agente la resuelve"),
    ("Agendar una cita", 28, 252, 7.5, 78, "Trámite: el agente no agenda"),
    ("Cancelar o reprogramar", 12, 108, 4.0, 85, "Trámite: el agente no cancela"),
    ("Requisitos", 13, 117, 4.5, 60, "Informativa: el agente la resuelve"),
    ("Cuotas y costos", 6, 54, 3.5, 70, "Informativa: el agente la resuelve"),
    ("Resultados de laboratorio", 8, 72, 5.0, 55, "Necesita datos del paciente"),
    ("Historia clínica y certificados", 4, 36, 5.0, 60, "Trámite en sede"),
    ("Estado de una autorización", 7, 63, 8.0, 40, "Necesita datos del paciente"),
    ("Quejas y reclamos", 5, 45, 9.0, 35, "Trámite: lo atiende una persona"),
    ("Otros", 3, 27, 6.0, 50, "Sin detalle en el anexo"),
]

SUPUESTOS = [
    ("costo_minuto", 665, "Anexo: costo medio por minuto de asesor", "Dato del anexo"),
    ("dias_mes", 22, "Anexo: mes típico de 22 días hábiles", "Dato del anexo"),
    ("minutos_jornada", 480, "Anexo: cada asesor trabaja 8 horas diarias", "Dato del anexo"),
    ("costo_mensual", 98000000, "Anexo: costo mensual del call center", "Dato del anexo"),
    ("llamadas_dia", 900, "Anexo: llamadas atendidas por día hábil", "Dato del anexo"),
    ("quejas_mes", 310, "Anexo: quejas formales al mes (call center y portal)", "Dato del anexo"),
    ("adopcion_baja", 0.29, "Supuesto: 34% de la encuesta menos 5 puntos de margen", "Medirlo en un piloto: chats iniciados / llamadas de esos motivos"),
    ("adopcion_alta", 0.39, "Supuesto: 34% de la encuesta más 5 puntos de margen", "Medirlo en un piloto: chats iniciados / llamadas de esos motivos"),
]

QUEJAS = [
    ("Espera larga en la línea", 32, "Indirecto: libera asesores de llamadas informativas", ""),
    ("Información distinta según quien responda", 21, "Directo: una sola fuente para requisitos, horarios y cuotas", "T05, T06, T15"),
    ("Cita perdida por falta de autorización u orden", 17, "Directo: anticipa orden, autorización y los 3 días hábiles", "T04, T13, T15"),
    ("Cobro inesperado", 11, "Directo: informa la cuota y quién no paga", "T07, T08, T30"),
    ("No encuentra o no recibe sus resultados", 9, "Directo: dice dónde y cuándo salen", "T10"),
    ("Trato del asesor", 6, "No lo aborda", ""),
    ("Otros", 4, "No lo aborda", ""),
]


def main():
    DATOS.mkdir(parents=True, exist_ok=True)
    escribir = lambda nombre, valor: (DATOS / nombre).write_text(json.dumps(valor, ensure_ascii=False, indent=1), encoding="utf-8")
    escribir("pruebas.json", pruebas())
    escribir("call_center.json", {"rows": [
        {"motivo": m, "porcentaje": p, "llamadas_dia": n, "duracion_min": d, "resueltas_primera_pct": r,
         "alcance": a, "incluida": a.startswith("Informativa")} for m, p, n, d, r, a in CALL_CENTER],
        "meta": [{"label": "Fuente", "value": "Anexo del enunciado, tabla «Por qué llaman (llamadas atendidas)»"}]})
    escribir("supuestos.json", {"rows": [
        {"parametro": k, "valor": v, "fuente": f, "como_comprobarlo": c} for k, v, f, c in SUPUESTOS],
        "meta": [{"label": "Fuente", "value": "Anexo del enunciado y supuestos declarados"}]})
    escribir("quejas.json", {"rows": [
        {"motivo": m, "porcentaje": p, "relacion_agente": r, "pruebas": t} for m, p, r, t in QUEJAS],
        "meta": [{"label": "Fuente", "value": "Anexo: 310 quejas formales al mes y su distribución por motivo"}]})
    print("Listo:", sorted(p.name for p in DATOS.glob("*.json")))


if __name__ == "__main__":
    main()
