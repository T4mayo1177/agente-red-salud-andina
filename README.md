# Asistente de Red Salud Andina

Agente conversacional que responde preguntas básicas de pacientes y familiares de Red Salud Andina (red de salud ficticia). Solo informa, orienta y deriva: no agenda, no consulta citas y no ve datos de pacientes. Lo que sabe está en `backend/agente/base_conocimiento.md`, copia textual del anexo del enunciado. Cuando no sabe algo, lo dice, registra la pregunta (solo el texto) y da el canal para hablar con una persona.

Antes del agente hay un **gateway**: un modelo pequeño de Gemini clasifica cada mensaje. Si es una urgencia, un pedido de consejo médico, un intento de cambiar las reglas o un tema ajeno, responde con un texto fijo aprobado y el agente principal no se llama.

## Arquitectura

```
Navegador (React + Vite, puerto 5173)
   │  POST /chat {session_id, mensaje}
   ▼
FastAPI (backend/main.py, puerto 8080)
   │  Runner de Google ADK + sesiones en memoria
   ▼
Gateway (backend/agente/gateway.py, before_agent_callback)
   │  modelo pequeño (Flash-Lite) → urgencia | consejo_medico | manipulacion | fuera_de_tema | normal
   ├─ caso especial → respuesta fija (sin llamar al agente principal)
   ▼ normal (o si el clasificador falla)
Agente ADK (backend/agente/agent.py)
   ├─ instrucción = instrucciones.md + base_conocimiento.md
   ├─ modelo Gemini (Google AI Studio, clave solo en el servidor)
   └─ herramienta registrar_pregunta_sin_respuesta
          ▼
      almacenamiento/ → data/preguntas_sin_respuesta.jsonl (local) o Firestore (nube)
```

| Archivo | Para qué sirve |
| --- | --- |
| `backend/agente/instrucciones.md` | Cómo se comporta el agente. Es el archivo que se edita para cambiar su conducta. |
| `backend/agente/base_conocimiento.md` | Lo único que el agente sabe (anexo). |
| `backend/agente/gateway.py` | El clasificador con el modelo pequeño y las respuestas fijas de los casos especiales. |
| `backend/agente/herramientas.py` | Registra preguntas sin respuesta, quitando correos y números largos. |
| `backend/agente/agent.py` | Carga el `.env`, une instrucciones + base y crea el agente. |
| `backend/almacenamiento/` | Dónde se guardan las preguntas: `jsonl` (local) o `firestore` (nube). |
| `backend/main.py` | API: `POST /chat` y `GET /health`. Si Gemini falla, responde con los canales de atención. |
| `frontend/src/App.jsx` | La ventana de chat. |
| `pruebas/` | 27 preguntas de prueba y el script que las envía al agente. |

## Requisitos

Python 3.13 y Node.js 20 o superior.

## 1. Clave de Gemini (gratis)

1. Entre a https://aistudio.google.com, inicie sesión y cree una API key («Get API key»). No pide tarjeta.
2. Póngala en **una** de estas dos ubicaciones (el backend busca en este orden):
   - **Opción A:** `backend/.env` (copie `backend/.env.example` y complete `GOOGLE_API_KEY`).
   - **Opción B:** un `.env` en la carpeta raíz del proyecto (copie `.env.example`). Se usa el más cercano subiendo carpetas.
3. Variables disponibles (ver `backend/.env.example`):
   - `GOOGLE_API_KEY`: la clave. `GOOGLE_GENAI_USE_VERTEXAI=FALSE`: usar AI Studio, no Vertex AI.
   - `GEMINI_MODEL`: agente principal. Vacío = `gemini-3.5-flash-lite`. No use `gemini-3.5-flash`: su nivel gratuito es de solo 20 solicitudes por día.
   - `GEMINI_THINKING`: razonamiento del agente (`MINIMAL`, `LOW`, `MEDIUM`, `HIGH`). Vacío = `LOW`. Con menos, en las pruebas el modelo a veces decía «quedó registrada» sin registrar.
   - `GATEWAY_MODEL`: modelo pequeño del gateway. Vacío = `gemini-3.5-flash-lite`, con razonamiento mínimo (~1,3 s). En las pruebas, `gemini-3.1-flash-lite` daba 503 por saturación. Si usa el mismo modelo del agente, comparten la cuota: cada mensaje gasta 2–3 llamadas de ese modelo. Si el nombre está mal o se agota su cuota, el gateway se salta y responde el agente principal.
   - `STORAGE_BACKEND`: `jsonl` (por defecto) o `firestore`.
   - `ALLOWED_ORIGINS`: de dónde acepta peticiones el backend (por defecto `http://localhost:5173`).
   - `PORT`: puerto del backend (por defecto 8080).

Los archivos `.env` están en `.gitignore`. Nunca ponga la clave en el frontend.

## 2. Correr el backend

```powershell
cd backend
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn main:app --port 8080
```

Comprobar: http://localhost:8080/health responde `{"ok": true}`. Sin clave, `/chat` igual responde: da el mensaje de respaldo con los canales del call center.

## 3. Correr el frontend

```powershell
cd frontend
npm install
npm run dev
```

Abra http://localhost:5173. Para otra URL de backend, cree `frontend/.env` con `VITE_API_URL=...` (ver `frontend/.env.example`).

## Dónde ver las preguntas sin respuesta

`backend/data/preguntas_sin_respuesta.jsonl`, una línea por pregunta:

```json
{"id": "…", "fecha": "2026-11-11T15:04:05+00:00", "pregunta": "¿Cuánto vale una consulta particular?", "tema": "costos"}
```

La operación lo revisa cada lunes y, si corresponde, agrega la respuesta a `base_conocimiento.md`.

## Cambiar una instrucción en vivo

1. Edite `backend/agente/instrucciones.md` (o `base_conocimiento.md`). No use llaves `{ }`: ADK las interpreta como variables (hay una prueba que lo revisa).
2. Reinicie el backend (Ctrl+C y el mismo comando `uvicorn`).
3. Empiece una «Nueva conversación» en el chat.

## Pruebas

```powershell
cd backend
.venv\Scripts\python -m pytest
```

Prueban, sin llamar a Gemini: el gateway (cada categoría da su respuesta fija, `normal` y los fallos pasan al agente, y por el Runner real de ADK una urgencia no llega al agente principal), la limpieza de datos personales, la escritura del JSONL, la validación de `/chat` (mensaje vacío o largo → 422), el mensaje de respaldo cuando Gemini falla, la limpieza de líneas vacías y de ofertas de cierre, que si el modelo dice «quedó registrada» sin llamar la herramienta el backend registra la pregunta (y que no la registra dos veces), `/health` y que los `.md` no tengan llaves.

Conversaciones de prueba con Gemini real (backend corriendo y con clave):

```powershell
backend\.venv\Scripts\python pruebas\correr_casos.py
```

Envía las 27 preguntas de `pruebas/casos.json` (en el anexo, fuera del anexo, ambiguas y adversariales), una sesión nueva por pregunta (más el mensaje de `seguimiento` en la misma sesión cuando el caso lo trae) y con pausa de 6 s, y guarda `pruebas/resultados/<fecha>.jsonl` con pregunta, respuesta, líneas y palabras. Una persona compara cada respuesta con el campo `esperado` del caso.

## Despliegue (Google Cloud Run)

- **Chat:** https://red-salud-frontend-94195021809.us-central1.run.app
- **API:** https://red-salud-backend-94195021809.us-central1.run.app (`/health`, `POST /chat`)

Cada `push` a `main` ejecuta `.github/workflows/deploy.yml` (GitHub Actions):

1. **Pruebas:** `pytest` del backend. Si fallan, no se despliega nada.
2. **Backend:** construye `backend/Dockerfile`, sube la imagen a Artifact Registry y la despliega en Cloud Run con `STORAGE_BACKEND=firestore` (colección `preguntas_sin_respuesta`) y `ALLOWED_ORIGINS` = URL del frontend. `--max-instances 1` porque las sesiones viven en memoria (y cuida la cuota de Gemini).
3. **Frontend:** construye `frontend/Dockerfile` (build de Vite con `VITE_API_URL` = URL del backend, servido con nginx) y lo despliega como un segundo servicio de Cloud Run.

Seguridad del despliegue:

- GitHub entra a GCP con **Workload Identity Federation**: no hay llaves JSON guardadas en GitHub, y solo este repositorio puede usar la cuenta de servicio `github-deployer` (permisos: desplegar en Cloud Run y subir imágenes).
- `GOOGLE_API_KEY` vive en **Secret Manager** (`google-api-key`); Cloud Run la lee al arrancar. Nunca pasa por GitHub ni por el frontend.

Para reproducirlo en otro proyecto: cree el secreto, la base de Firestore, el repositorio de Artifact Registry `red-salud`, la cuenta `github-deployer` y el proveedor de Workload Identity, y cambie las variables `env:` al inicio del workflow.

## Decisiones

- **Sin RAG:** el anexo es corto y cabe completo en la instrucción; así el agente siempre ve toda la información y no hay búsquedas que fallen.
- **Un solo agente** con una sola herramienta: más fácil de explicar y de ajustar.
- **Gateway como callback y no como multiagente:** `before_agent_callback` de ADK corre el clasificador antes del agente. Así la etiqueta del clasificador no queda en el historial de la conversación, y los casos sensibles salen con textos aprobados por la operación, no improvisados. Si el clasificador falla, el agente principal responde con sus propias reglas de seguridad (segunda capa).
- **Sesiones en memoria:** suficiente para una prueba; se pierden al reiniciar el backend.
- **Registro en JSONL** en local y Firestore en la nube, detrás de la misma interfaz (`RepositorioPreguntas`).
- **Registro garantizado:** si el modelo dice que registró la pregunta pero no llamó la herramienta, el backend la registra (`main.py`), para no decirle algo falso a la persona.
- **Limpieza final de la respuesta** (`main.py`): quita líneas vacías y, si la respuesta ya tiene contenido, la oferta genérica del final («¿Desea conocer…?», «¿Necesita…?»). El modelo Flash-Lite las agrega aunque las instrucciones lo prohíben; las preguntas de aclaración no se tocan.
- **Bienvenida fija** en el frontend para no gastar cuota del modelo.

## Límites conocidos

- La cuota gratuita se cuenta por proyecto y por modelo: 15 solicitudes por minuto (confirmado en los errores de la API) y unas 500 por día en los Flash-Lite (según fuentes de octubre de 2026; verifíquelo en https://aistudio.google.com/rate-limit). La cuota gratuita de Gemini es limitada por minuto y por día. Si se agota, el agente responde con los canales de atención en lugar de fallar.
- Cada mensaje usa 1 llamada al modelo pequeño del gateway y 1 al agente (2 si registra la pregunta); los casos especiales no llaman al agente. Si el gateway y el agente usan el mismo modelo, comparten la cuota: 15 por minuto alcanza para unos 5 mensajes por minuto, y 500 por día para unos 170–250 mensajes. Unas 10 conversaciones de evaluación de ~4 mensajes son ~40–60 llamadas/día. Antes de entregar, revise el límite diario del modelo en AI Studio y verifique allí el nombre exacto del modelo Flash-Lite. El límite se declara en el correo de entrega.
- La calidad de las respuestas depende del modelo; las instrucciones reducen, pero no eliminan, el riesgo de errores.
- El gateway ve solo el último mensaje y puede equivocarse (falsos positivos o negativos): por eso el agente principal conserva las reglas de urgencia y consejo médico. Agrega unos 0,5–1 s por mensaje.
- No conoce la hora actual: informa horarios, no si una sede está abierta en este momento.
- La limpieza de datos personales del registro solo quita correos y números de 6 o más dígitos; los nombres dependen de que el modelo no los escriba.
