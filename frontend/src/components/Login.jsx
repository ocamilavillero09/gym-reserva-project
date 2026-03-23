import { useState } from 'react';
import { authApi } from '../services/api';

const RED = '#CC0000';

const inputStyle = {
  width: '100%',
  padding: '12px 16px',
  border: '1.5px solid #E5E7EB',
  borderRadius: 10,
  fontSize: 14,
  color: '#1A1A1A',
  backgroundColor: '#FAFAFA',
  transition: 'border-color 0.2s, box-shadow 0.2s',
};

export default function Login({ onLogin }) {
  const [tab, setTab]               = useState('login');
  const [email, setEmail]           = useState('');
  const [password, setPassword]     = useState('');
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
        await authApi.register({ name, email, password });
        setRegistered(true);
      } else {
        const user = await authApi.login({ email, password });
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
    setPassword('');
    setName('');
    setError('');
  };

  if (registered) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', backgroundColor: '#F4F4F6', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ backgroundColor: 'white', borderRadius: 22, padding: '48px 40px', maxWidth: 440, width: '100%', textAlign: 'center', boxShadow: '0 8px 40px rgba(0,0,0,0.1)', animation: 'scaleIn 0.3s ease' }}>
          <div style={{ width: 80, height: 80, borderRadius: '50%', backgroundColor: '#dcfce7', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px', fontSize: 40 }}>
            ✅
          </div>
          <h2 style={{ fontSize: 24, fontWeight: 900, color: '#1A1A1A', marginBottom: 10 }}>
            ¡Registro exitoso!
          </h2>
          <p style={{ color: '#555', fontSize: 15, lineHeight: 1.7, marginBottom: 8 }}>
            Tu cuenta ha sido creada correctamente, <strong>{name}</strong>.
          </p>
          <p style={{ color: '#888', fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
            Ya puedes iniciar sesión con tu correo <strong style={{ color: RED }}>{email}</strong> para acceder al sistema de reservas.
          </p>
          <button onClick={handleGoToLogin} style={{
            width: '100%', padding: 15, backgroundColor: RED, color: 'white',
            border: 'none', borderRadius: 12, fontWeight: 800, fontSize: 15,
            cursor: 'pointer', boxShadow: '0 4px 16px rgba(204,0,0,0.35)',
          }}>
            Ir a iniciar sesión →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex' }}>
      {/* Panel izquierdo decorativo */}
      <div style={{
        flex: 1,
        background: `linear-gradient(145deg, ${RED} 0%, #990000 100%)`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 60,
        '@media(max-width:768px)': { display: 'none' },
      }}
        className="left-panel"
      >
        <div style={{ textAlign: 'center', color: 'white', animation: 'fadeUp 0.6s ease' }}>
          <img
            src="/logo-udem.png"
            alt="Universidad de Medellín"
            style={{ width: 220, marginBottom: 28, filter: 'drop-shadow(0 4px 16px rgba(0,0,0,0.25))' }}
          />
          <p style={{ fontSize: 17, opacity: 0.88, maxWidth: 300, lineHeight: 1.7 }}>
            Sistema de reserva de cupos para la comunidad universitaria de Medellín
          </p>
          <div style={{ marginTop: 48, display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
            {['Reservas en línea', 'Horarios en tiempo real', 'Confirmación por correo'].map(f => (
              <span key={f} style={{
                backgroundColor: 'rgba(255,255,255,0.18)',
                border: '1px solid rgba(255,255,255,0.3)',
                padding: '8px 16px', borderRadius: 24, fontSize: 13, fontWeight: 500,
              }}>{f}</span>
            ))}
          </div>
          <div style={{ marginTop: 60, padding: '20px 32px', backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: 16, border: '1px solid rgba(255,255,255,0.2)' }}>
            <p style={{ fontSize: 13, opacity: 0.85, lineHeight: 1.7, margin: 0 }}>
              "Gestiona tu tiempo en el gimnasio de forma fácil y sin filas."
            </p>
          </div>
        </div>
      </div>

      {/* Panel derecho — formulario */}
      <div style={{
        flex: 1,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '40px 24px',
        backgroundColor: '#F4F4F6',
      }}>
        <div style={{ width: '100%', maxWidth: 420, animation: 'fadeUp 0.4s ease' }}>

          {/* Logo */}
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <img src="/logo-udem.png" alt="Universidad de Medellín" style={{ width: 180 }} />
          </div>

          <div style={{ backgroundColor: 'white', borderRadius: 22, padding: '36px 32px', boxShadow: '0 8px 40px rgba(0,0,0,0.1)' }}>
            <h2 style={{ color: '#1A1A1A', fontSize: 24, fontWeight: 800, marginBottom: 6 }}>
              {tab === 'login' ? 'Bienvenido de nuevo' : 'Crear cuenta'}
            </h2>
            <p style={{ color: '#888', fontSize: 14, marginBottom: 28 }}>
              {tab === 'login' ? 'Ingresa con tu correo institucional' : 'Regístrate con tu correo @udem.edu.co'}
            </p>

            {/* Tabs */}
            <div style={{ display: 'flex', backgroundColor: '#F4F4F6', borderRadius: 12, padding: 4, marginBottom: 28 }}>
              {[
                { id: 'login',    label: 'Iniciar sesión' },
                { id: 'register', label: 'Registrarse' },
              ].map(t => (
                <button key={t.id} onClick={() => { setTab(t.id); setError(''); }} style={{
                  flex: 1, padding: '10px 0', border: 'none', borderRadius: 9, cursor: 'pointer',
                  backgroundColor: tab === t.id ? 'white' : 'transparent',
                  color: tab === t.id ? RED : '#888',
                  fontWeight: tab === t.id ? 700 : 400,
                  fontSize: 14,
                  boxShadow: tab === t.id ? '0 2px 8px rgba(0,0,0,0.1)' : 'none',
                  transition: 'all 0.2s',
                }}>
                  {t.label}
                </button>
              ))}
            </div>

            <form onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {tab === 'register' && (
                <div>
                  <label style={{ display: 'block', fontSize: 13, color: '#555', marginBottom: 6, fontWeight: 600 }}>
                    Nombre completo
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="Ej: María García"
                    style={inputStyle}
                    required
                  />
                </div>
              )}

              <div>
                <label style={{ display: 'block', fontSize: 13, color: '#555', marginBottom: 6, fontWeight: 600 }}>
                  Correo institucional
                </label>
                <input
                  type="text"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="nombre@soyudemedellin.edu.co"
                  style={inputStyle}
                  autoCapitalize="none"
                  autoCorrect="off"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 13, color: '#555', marginBottom: 6, fontWeight: 600 }}>
                  Contraseña
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                  style={inputStyle}
                  required
                />
              </div>

              {error && (
                <div style={{ backgroundColor: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 10, padding: '10px 14px' }}>
                  <p style={{ color: '#991b1b', fontSize: 13, margin: 0 }}>⚠ {error}</p>
                </div>
              )}

              <button type="submit" disabled={submitting} style={{
                width: '100%', padding: 15, backgroundColor: RED, color: 'white',
                border: 'none', borderRadius: 12, fontWeight: 800, fontSize: 15,
                cursor: submitting ? 'not-allowed' : 'pointer', marginTop: 4,
                boxShadow: '0 4px 16px rgba(204,0,0,0.35)',
                opacity: submitting ? 0.7 : 1,
              }}>
                {submitting ? 'Cargando...' : tab === 'login' ? 'Ingresar →' : 'Crear cuenta →'}
              </button>

              <div style={{ padding: '12px 16px', backgroundColor: '#FFF8F0', borderRadius: 10, border: '1px solid #FFD9A0' }}>
                <p style={{ fontSize: 12, color: '#92400e', margin: 0, textAlign: 'center' }}>
                  🔒 Solo se permiten correos <strong>@soyudemedellin.edu.co</strong> o <strong>@udem.edu.co</strong>
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
