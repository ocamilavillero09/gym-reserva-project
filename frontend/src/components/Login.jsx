/*
 * PANTALLA DE ACCESO Y REGISTRO
 *
 * Solo estructura y comportamiento. La presentación vive en
 * src/styles/login.css.
 */
import { useState } from 'react';
import { authApi } from '../services/api';
import '../styles/login.css';

// Tres tipos de correo institucional: el dominio determina el rol. Solo dos de
// ellos pueden registrarse por su cuenta; las cuentas de administrador las crea
// el administrador principal desde su panel.
const DOMINIOS = [
  { dominio: '@soyudemedellin.edu.co', etiqueta: 'Estudiante',    registroPublico: true },
  { dominio: '@udem.edu.co',           etiqueta: 'Entrenador',    registroPublico: true },
  { dominio: '@udemedellin.edu.co',    etiqueta: 'Administrador', registroPublico: false },
];

const dominioDe = (email) =>
  DOMINIOS.find((d) => email.trim().toLowerCase().endsWith(d.dominio)) ?? null;

const REGISTRABLES = DOMINIOS.filter((d) => d.registroPublico);

const CARACTERISTICAS = ['Reservas en línea', 'Horarios en tiempo real', 'Aforo actualizado'];

export default function Login({ onLogin }) {
  const [tab, setTab]               = useState('login');
  const [email, setEmail]           = useState('');
  // El documento de identidad es el dato de registro y, a la vez, la
  // contraseña con la que se inicia sesión.
  const [documento, setDocumento]   = useState('');
  const [name, setName]             = useState('');
  const [error, setError]           = useState('');
  const [registered, setRegistered] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      if (tab === 'register') {
        await authApi.register({ name, email, documento });
        setRegistered(true);
      } else {
        const user = await authApi.login({ email, documento });
        onLogin(user);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoToLogin = () => {
    setRegistered(false);
    setTab('login');
    setDocumento('');
    setName('');
    setError('');
  };

  if (registered) {
    return (
      <div className="registro-ok">
        <div className="registro-ok__tarjeta">
          <div className="registro-ok__icono">✅</div>
          <h2 className="registro-ok__titulo">¡Registro exitoso!</h2>
          <p className="registro-ok__texto">
            Tu cuenta ha sido creada correctamente, <strong>{name}</strong>.
          </p>
          <p className="registro-ok__detalle">
            Ya puedes iniciar sesión con tu correo{' '}
            <strong className="registro-ok__correo">{email}</strong> y tu
            documento de identidad como contraseña.
          </p>
          <button className="acceso__enviar" onClick={handleGoToLogin}>
            Ir a iniciar sesión →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="acceso">
      {/* Columna izquierda — presentación del sistema */}
      <div className="acceso__presentacion">
        <div className="acceso__presentacion-contenido">
          <img
            className="acceso__logo-grande"
            src="/logo-udem.png"
            alt="Universidad de Medellín"
          />
          <p className="acceso__lema">
            Sistema de reserva de cupos para la comunidad universitaria de Medellín
          </p>
          <div className="acceso__caracteristicas">
            {CARACTERISTICAS.map(f => (
              <span key={f} className="acceso__caracteristica">{f}</span>
            ))}
          </div>
          <div className="acceso__cita">
            <p>"Gestiona tu tiempo en el gimnasio de forma fácil y sin filas."</p>
          </div>
        </div>
      </div>

      {/* Columna derecha — formulario */}
      <div className="acceso__formulario">
        <div className="acceso__caja">
          <div className="acceso__logo-caja">
            <img src="/logo-udem.png" alt="Universidad de Medellín" />
          </div>

          <div className="acceso__tarjeta">
            <h2 className="acceso__titulo">
              {tab === 'login' ? 'Bienvenido de nuevo' : 'Crear cuenta'}
            </h2>
            <p className="acceso__descripcion">
              {tab === 'login'
                ? 'Ingresa con tu correo institucional y tu documento de identidad'
                : 'Regístrate con tu nombre, correo institucional y documento de identidad'}
            </p>

            <div className="acceso__pestanas">
              {[
                { id: 'login',    label: 'Iniciar sesión' },
                { id: 'register', label: 'Registrarse' },
              ].map(t => (
                <button
                  key={t.id}
                  className={`acceso__pestana${tab === t.id ? ' acceso__pestana--activa' : ''}`}
                  onClick={() => { setTab(t.id); setError(''); }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <form className="acceso__campos" onSubmit={handleSubmit} noValidate>
              {tab === 'register' && (
                <div>
                  <label className="acceso__etiqueta">Nombre completo</label>
                  <input
                    className="acceso__entrada"
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="Ej: María García"
                    required
                  />
                </div>
              )}

              <div>
                <label className="acceso__etiqueta">Correo institucional</label>
                <input
                  className="acceso__entrada"
                  type="text"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="nombre@soyudemedellin.edu.co"
                  autoCapitalize="none"
                  autoCorrect="off"
                />
                {/* Se avisa en vivo qué rol otorga el dominio escrito */}
                {tab === 'register' && email.trim() !== '' && (() => {
                  const d = dominioDe(email);
                  if (!d) return <p className="acceso__pista acceso__pista--error">⚠ Ese dominio no es institucional</p>;
                  if (!d.registroPublico) {
                    return (
                      <p className="acceso__pista acceso__pista--error">
                        ⚠ Las cuentas de administrador las crea el administrador principal
                      </p>
                    );
                  }
                  return (
                    <p className="acceso__pista acceso__pista--ok">
                      ✓ Entrarás como {d.etiqueta.toUpperCase()}
                    </p>
                  );
                })()}
              </div>

              {/* Documento de identidad: dato de registro y contraseña */}
              <div>
                <label className="acceso__etiqueta">Documento de identidad</label>
                <input
                  className="acceso__entrada"
                  type="password"
                  value={documento}
                  onChange={e => setDocumento(e.target.value)}
                  placeholder="Ej: 1001234567"
                  inputMode="numeric"
                  required
                />
                <p className="acceso__nota">
                  {tab === 'login'
                    ? 'Tu documento de identidad es tu contraseña.'
                    : 'Con este documento iniciarás sesión (mínimo 6 caracteres).'}
                </p>
              </div>

              {error && (
                <div className="acceso__error">
                  <p>⚠ {error}</p>
                </div>
              )}

              <button className="acceso__enviar" type="submit" disabled={submitting}>
                {submitting ? 'Cargando...' : tab === 'login' ? 'Ingresar →' : 'Crear cuenta →'}
              </button>

              <div className="acceso__dominios">
                <p className="acceso__dominios-titulo">
                  🔒 {tab === 'register' ? 'Puedes registrarte con' : 'Correos institucionales'}
                </p>
                {(tab === 'register' ? REGISTRABLES : DOMINIOS).map(d => (
                  <p key={d.dominio} className="acceso__dominio">
                    <strong>{d.dominio}</strong> → {d.etiqueta}
                  </p>
                ))}
                {tab === 'register' && (
                  <p className="acceso__dominio acceso__dominio--nota">
                    Las cuentas de administrador las crea el administrador principal.
                  </p>
                )}
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
