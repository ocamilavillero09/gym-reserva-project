import { useCallback, useEffect, useState } from 'react';
import { adminApi } from '../services/api';

const RED = '#CC0000';
const inputStyle = { width: '100%', padding: '12px 16px', border: '1.5px solid #E5E7EB', borderRadius: 10, fontSize: 14, backgroundColor: '#FAFAFA' };
const card = { backgroundColor: 'white', borderRadius: 18, padding: 26, boxShadow: '0 2px 14px rgba(0,0,0,0.07)', marginBottom: 24 };

// Los tres dominios institucionales y el rol que otorga cada uno (RN01).
const DOMINIOS = [
  { dominio: '@soyudemedellin.edu.co', rol: 'ESTUDIANTE',  etiqueta: 'Estudiante' },
  { dominio: '@udem.edu.co',           rol: 'ENTRENADOR',  etiqueta: 'Entrenador' },
  { dominio: '@udemedellin.edu.co',    rol: 'ADMIN',       etiqueta: 'Administrador' },
];

const ROLE_BADGE = {
  ESTUDIANTE: { bg: '#DBEAFE', fg: '#1D4ED8', label: 'Estudiante' },
  ENTRENADOR: { bg: '#DCFCE7', fg: '#15803D', label: 'Entrenador' },
  ADMIN:      { bg: '#FEE2E2', fg: '#991B1B', label: 'Administrador' },
  SIN_ROL:    { bg: '#E5E7EB', fg: '#4B5563', label: 'Rol retirado' },
};

const rolDeCorreo = (email) =>
  DOMINIOS.find((d) => email.trim().toLowerCase().endsWith(d.dominio))?.rol ?? null;

/**
 * Panel del ADMINISTRADOR — gestión de usuarios.
 *
 *   RF21 / HU21 — El ADMINISTRADOR PRINCIPAL crea cuentas con rol de
 *                 administrador (el rol se deduce del dominio del correo).
 *   RF22 / HU22 — El administrador principal gestiona esas cuentas y puede
 *                 RETIRARLES el rol de administrador.
 */
export default function AdminPanel({ user, showToast }) {
  const [users, setUsers] = useState([]);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [documento, setDocumento] = useState('');
  const [enviando, setEnviando] = useState(false);

  const cargar = useCallback(() => {
    adminApi.listUsers(user.email).then(setUsers).catch(() => setUsers([]));
  }, [user.email]);

  useEffect(cargar, [cargar]);

  const crear = async (e) => {
    e.preventDefault();
    setEnviando(true);
    try {
      const r = await adminApi.createUser({
        actor_email: user.email,
        name: name.trim(),
        email: email.trim().toLowerCase(),
        documento: documento.trim(),
      });
      showToast(r.message, 'success');
      setName(''); setEmail(''); setDocumento('');
      cargar();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setEnviando(false);
    }
  };

  // RF22 — Retirar o restaurar el rol de administrador de otra cuenta.
  const cambiarRol = async (objetivo, accion) => {
    const verbo = accion === 'retirar' ? 'retirar el rol de administrador a' : 'restaurar el rol de administrador a';
    if (!window.confirm(`¿Seguro que deseas ${verbo} ${objetivo.name}?`)) return;
    try {
      const r = await adminApi.setAdminRole(objetivo.email, accion, user.email);
      showToast(r.message, accion === 'retirar' ? 'warning' : 'success');
      cargar();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const rolDetectado = rolDeCorreo(email);
  const porRol = (rol) => users.filter((u) => u.role === rol).length;
  // Solo el administrador principal gestiona las cuentas de administrador.
  const esPrincipal = user.es_principal ?? false;

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '36px 24px', animation: 'fadeUp 0.4s ease' }}>
      <h2 style={{ fontSize: 30, fontWeight: 900, marginBottom: 4 }}>Gestión de usuarios</h2>
      <p style={{ color: '#999', fontSize: 15, marginBottom: 28 }}>
        {esPrincipal ? 'Administrador principal' : 'Administrador'} · {user.email}
      </p>

      {!esPrincipal && (
        <div style={{ background: '#FFF7ED', border: '1.5px solid #F59E0B', borderRadius: 12, padding: '14px 16px', marginBottom: 20 }}>
          <p style={{ fontSize: 13, color: '#78350F', margin: 0, lineHeight: 1.6 }}>
            ⚠️ Solo el <strong>administrador principal</strong> puede crear cuentas de administrador
            y retirarles el rol. Desde aquí puedes consultar los usuarios y crear estudiantes o entrenadores.
          </p>
        </div>
      )}

      {/* Crear usuario (incluye nuevos administradores) */}
      <div style={card}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 6 }}>➕ Crear usuario</h3>
        <p style={{ color: '#777', fontSize: 13, marginBottom: 18, lineHeight: 1.6 }}>
          El rol se asigna automáticamente según el dominio del correo. Para crear otro
          <strong> administrador</strong> (RF21), usa un correo <strong>@udemedellin.edu.co</strong>.
          El documento de identidad será su contraseña de ingreso.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px,1fr))', gap: 10, marginBottom: 20 }}>
          {DOMINIOS.map((d) => {
            const b = ROLE_BADGE[d.rol];
            return (
              <div key={d.dominio} style={{ border: '1px solid #eee', borderRadius: 12, padding: '12px 14px' }}>
                <span style={{ background: b.bg, color: b.fg, fontSize: 11, fontWeight: 800, padding: '3px 10px', borderRadius: 20 }}>
                  {b.label}
                </span>
                <p style={{ fontSize: 12, color: '#555', marginTop: 8, wordBreak: 'break-all' }}>{d.dominio}</p>
              </div>
            );
          })}
        </div>

        <form onSubmit={crear} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre completo" style={inputStyle} required />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="correo@udemedellin.edu.co"
            style={inputStyle}
            autoCapitalize="none"
            required
          />
          <input
            type="text"
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            placeholder="Documento de identidad (mínimo 6 caracteres)"
            style={inputStyle}
            inputMode="numeric"
            required
          />

          {email && (
            <p style={{ fontSize: 13, color: rolDetectado ? '#15803D' : '#991B1B', margin: 0 }}>
              {rolDetectado
                ? `✓ Este correo creará un usuario con rol ${ROLE_BADGE[rolDetectado].label.toUpperCase()}.`
                : '⚠ El correo no pertenece a ninguno de los tres dominios institucionales.'}
            </p>
          )}

          <button type="submit" disabled={enviando} style={{
            padding: 13, border: 'none', borderRadius: 12, background: RED, color: 'white',
            fontWeight: 800, cursor: enviando ? 'not-allowed' : 'pointer', opacity: enviando ? 0.7 : 1,
          }}>
            {enviando ? 'Creando...' : 'Crear usuario'}
          </button>
        </form>
      </div>

      {/* Listado de usuarios */}
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
          <h3 style={{ fontSize: 18, fontWeight: 800 }}>👥 Usuarios registrados ({users.length})</h3>
          <span style={{ fontSize: 12, color: '#777' }}>
            {porRol('ESTUDIANTE')} estudiantes · {porRol('ENTRENADOR')} profesores · {porRol('ADMIN')} administradores
          </span>
        </div>

        {users.length === 0 ? (
          <p style={{ color: '#999', fontSize: 14 }}>Sin usuarios para mostrar.</p>
        ) : users.map((u) => {
          const b = ROLE_BADGE[u.role] || { bg: '#eee', fg: '#555', label: u.role };
          return (
            <div key={u.email} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid #F0F0F0' }}>
              <div style={{ minWidth: 0 }}>
                <p style={{ fontWeight: 700, fontSize: 14 }}>
                  {u.name}
                  {u.es_principal && (
                    <span style={{ marginLeft: 8, fontSize: 10, fontWeight: 800, color: RED }}>★ PRINCIPAL</span>
                  )}
                </p>
                <p style={{ fontSize: 12, color: '#999', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {u.email} · doc. {u.documento || '—'}
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
                {u.estado === 'PENALIZADO' && (
                  <span style={{ fontSize: 11, fontWeight: 800, color: RED }}>PENALIZADO</span>
                )}
                <span style={{ background: b.bg, color: b.fg, fontSize: 11, fontWeight: 800, padding: '4px 12px', borderRadius: 20 }}>
                  {b.label}
                </span>
                {/* RF22 — Retirar o restaurar el rol de administrador */}
                {esPrincipal && !u.es_principal && u.role === 'ADMIN' && (
                  <button onClick={() => cambiarRol(u, 'retirar')} style={{
                    padding: '6px 12px', border: '1.5px solid #fca5a5', borderRadius: 8,
                    background: 'white', color: RED, fontSize: 11, fontWeight: 800, cursor: 'pointer',
                  }}>
                    Retirar rol
                  </button>
                )}
                {esPrincipal && u.role === 'SIN_ROL' && (
                  <button onClick={() => cambiarRol(u, 'restaurar')} style={{
                    padding: '6px 12px', border: '1.5px solid #86efac', borderRadius: 8,
                    background: 'white', color: '#15803d', fontSize: 11, fontWeight: 800, cursor: 'pointer',
                  }}>
                    Restaurar
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
