import { useEffect, useRef, useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

// Mensaje fijo: se muestra sin llamar al modelo (no gasta cuota).
const BIENVENIDA =
  '¡Hola! Qué gusto saludarle. Soy Artemisa, la asistente virtual de Red Salud Andina.\n' +
  'Con mucho gusto le oriento sobre sedes, horarios, citas, requisitos, cuotas y resultados.\n' +
  '¿En qué le puedo ayudar hoy?'

const SUGERENCIAS = [
  '¿Qué llevo a mi cita?',
  'Horarios de las sedes',
  '¿Cuánto es la cuota moderadora?',
  '¿Cómo veo mis resultados de laboratorio?',
]

// Animación del saludo: puntos de "escribiendo" y luego el texto palabra por palabra.
const ESPERA_SALUDO_MS = 900
const MS_POR_PALABRA = 45

function prefiereMenosMovimiento() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

const ERROR_CONEXION =
  'No pude conectarme. Puede llamar al (601) 555 0100 o escribir al WhatsApp +57 300 555 0100, de lunes a viernes de 7:00 a 19:00 y sábados de 8:00 a 14:00. Fuera de ese horario: formulario en citas.redsaludandina.example.'

function nuevoId() {
  const id = crypto.randomUUID()
  try {
    sessionStorage.setItem('session_id', id)
  } catch {
    // Sin sessionStorage la conversación igual funciona mientras la página esté abierta.
  }
  return id
}

function leerId() {
  try {
    return sessionStorage.getItem('session_id') || nuevoId()
  } catch {
    return nuevoId()
  }
}

export default function App() {
  const [sessionId, setSessionId] = useState(leerId)
  const [mensajes, setMensajes] = useState([])
  const [texto, setTexto] = useState('')
  const [esperando, setEsperando] = useState(false)
  // true mientras el saludo inicial se está "escribiendo".
  const [presentando, setPresentando] = useState(true)
  const finRef = useRef(null)

  // Cada conversación nueva empieza con el saludo animado.
  useEffect(() => {
    if (prefiereMenosMovimiento()) {
      setMensajes([{ autor: 'agente', texto: BIENVENIDA }])
      setPresentando(false)
      return
    }
    setMensajes([])
    setPresentando(true)
    const espera = setTimeout(() => {
      setMensajes([{ autor: 'agente', texto: BIENVENIDA, animar: true }])
    }, ESPERA_SALUDO_MS)
    return () => clearTimeout(espera)
  }, [sessionId])

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes, esperando])

  async function enviar(mensaje) {
    const limpio = mensaje.trim()
    if (!limpio || esperando || presentando) return
    setMensajes((previos) => [...previos, { autor: 'persona', texto: limpio }])
    setTexto('')
    setEsperando(true)
    try {
      const respuesta = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, mensaje: limpio }),
      })
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`)
      const datos = await respuesta.json()
      setMensajes((previos) => [...previos, { autor: 'agente', texto: datos.respuesta }])
    } catch {
      setMensajes((previos) => [...previos, { autor: 'agente', texto: ERROR_CONEXION }])
    } finally {
      setEsperando(false)
    }
  }

  function nuevaConversacion() {
    setSessionId(nuevoId()) // el efecto de arriba vuelve a mostrar el saludo animado
    setTexto('')
  }

  function terminarSaludo() {
    setMensajes((previos) => previos.map((m) => ({ ...m, animar: false })))
    setPresentando(false)
  }

  return (
    <div className="chat">
      <header className="encabezado">
        <div className="marca">
          <Logo />
          <div>
            <h1>Red Salud Andina</h1>
            <p className="subtitulo">Artemisa, asistente virtual</p>
          </div>
        </div>
        <button type="button" className="boton-secundario" onClick={nuevaConversacion} disabled={esperando}>
          Nueva conversación
        </button>
      </header>

      <main className="mensajes" aria-live="polite">
        {mensajes.map((m, i) => (
          <div key={i} className={`fila ${m.autor}`}>
            {m.autor === 'agente' && <Avatar />}
            <p className={`burbuja ${m.autor}`}>
              {m.animar ? <TextoAnimado texto={m.texto} alTerminar={terminarSaludo} /> : m.texto}
            </p>
          </div>
        ))}
        {mensajes.length === 1 && !presentando && (
          <div className="sugerencias">
            {SUGERENCIAS.map((s) => (
              <button type="button" key={s} onClick={() => enviar(s)} disabled={esperando}>
                {s}
              </button>
            ))}
          </div>
        )}
        {(esperando || (presentando && mensajes.length === 0)) && (
          <div className="fila agente">
            <Avatar />
            <p className="burbuja agente escribiendo" aria-label="El asistente está escribiendo">
              <span />
              <span />
              <span />
            </p>
          </div>
        )}
        <div ref={finRef} />
      </main>

      <form
        className="entrada"
        onSubmit={(e) => {
          e.preventDefault()
          enviar(texto)
        }}
      >
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Escriba su pregunta"
          maxLength={1000}
          disabled={esperando}
          aria-label="Su pregunta"
        />
        <button type="submit" disabled={esperando || presentando || !texto.trim()}>
          Enviar
        </button>
      </form>
      <p className="aviso">No comparta datos personales. Si es una urgencia, llame al 123.</p>
    </div>
  )
}

// Marca propia: una cruz de salud sobre una montaña (los Andes).
function Logo() {
  return (
    <svg className="logo" viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="20" r="20" fill="var(--white)" />
      <path d="M6 30 L16 16 L21 23 L25 18 L34 30 Z" fill="var(--primary-minus-200)" />
      <rect x="17" y="7" width="6" height="16" rx="1.5" fill="var(--secondary-plus-300)" />
      <rect x="12" y="12" width="16" height="6" rx="1.5" fill="var(--secondary-plus-300)" />
    </svg>
  )
}

// Muestra el texto palabra por palabra, conservando los saltos de línea.
function TextoAnimado({ texto, alTerminar }) {
  const partes = texto.split(/(\s+)/) // palabras y espacios intercalados
  const [visibles, setVisibles] = useState(0)

  useEffect(() => {
    if (visibles >= partes.length) {
      alTerminar()
      return
    }
    const siguiente = setTimeout(() => setVisibles((v) => v + 2), MS_POR_PALABRA)
    return () => clearTimeout(siguiente)
  }, [visibles, partes.length, alTerminar])

  return (
    <>
      <span aria-hidden="true">{partes.slice(0, visibles).join('')}</span>
      {/* Los lectores de pantalla leen el mensaje completo una sola vez. */}
      <span className="solo-lector">{texto}</span>
    </>
  )
}

function Avatar() {
  return (
    <span className="avatar" aria-hidden="true">
      A
    </span>
  )
}
