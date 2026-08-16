import { useEffect, useState } from 'react';
import { profileApi } from '../services/api';

const RED = '#CC0000';
const inputStyle = { width: '100%', padding: '12px 16px', border: '1.5px solid #E5E7EB', borderRadius: 10, fontSize: 14, backgroundColor: '#FAFAFA' };

const ROLE_LABEL = { ESTUDIANTE: 'Estudiante', ENTRENADOR: 'Profesor', ADMIN: 'Administrador' };

// RF13 — Perfil de usuario y metas + RN10 — contador de cancelaciones.
export default function ProfileView({ user, showToast }) {
  const [peso, setPeso] = useState('');
  const [altura, setAltura] = useState('');
  const [meta, setMeta] = useState('');
  const [datos, setDatos] = useState(null);

  useEffect(() => {
    profileApi.get(user.email).then((p) => {
      setDatos(p);
      setPeso(p.peso ?? '');
      setAltura(p.altura ?? '');
      setMeta(p.meta ?? '');
    }).catch(() => {});
  }, [user.email]);

  const save = async (e) => {
    e.preventDefault();
    try {
      const actualizado = await profileApi.update({
        email: user.email,
        peso: peso === '' ? null : Number(peso),
        altura: altura === '' ? null : Number(altura),
        meta,
      });
      setDatos(actualizado);
      showToast('Perfil actualizado.', 'success');
    } catch (err) { showToast(err.message, 'error'); }
  };

  const esEstudiante = (datos?.role ?? user.role) === 'ESTUDIANTE';
  const restantes = datos?.cancelaciones_restantes ?? 0;
  const enAlerta = esEstudiante && restantes <= 2;

  return (
    <div style={{ maxWidth: 560, margin: '0 auto', padding: '36px 24px', animation: 'fadeUp 0.4s ease' }}>
      <h2 style={{ fontSize: 30, fontWeight: 900, marginBottom: 4 }}>Mi perfil</h2>
      <p style={{ color: '#999', fontSize: 15, marginBottom: 28 }}>
        {user.name} · {user.email} · <strong>{ROLE_LABEL[datos?.role ?? user.role] || user.role}</strong>
      </p>

      {/* RN10 — El estudiante ve cuántas veces ha cancelado */}
      {esEstudiante && datos && (
        <div style={{
          background: 'white', borderRadius: 18, padding: 26, marginBottom: 20,
          boxShadow: '0 2px 14px rgba(0,0,0,0.07)',
          border: enAlerta ? '1.5px solid #F59E0B' : '1.5px solid transparent',
        }}>
          <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>📊 Mi comportamiento</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px,1fr))', gap: 14 }}>
            <Contador
              label="Veces que he cancelado"
              value={datos.cancel_count}
              sub={`de ${datos.cancelacion_limite} permitidas`}
              alerta={enAlerta}
            />
            <Contador
              label="Cancelaciones restantes"
              value={restantes}
              sub="antes de la penalización"
              alerta={enAlerta}
            />
            <Contador
              label="Inasistencias (No-Show)"
              value={datos.no_show_count}
              sub={`estado: ${datos.estado}`}
              alerta={datos.estado === 'PENALIZADO'}
            />
          </div>

          {datos.alerta && (
            <div style={{
              marginTop: 18, backgroundColor: restantes === 0 ? '#FEE2E2' : '#FFF7ED',
              border: `1.5px solid ${restantes === 0 ? '#DC2626' : '#F59E0B'}`,
              borderRadius: 12, padding: '14px 16px',
            }}>
              <p style={{ fontSize: 13, lineHeight: 1.6, color: restantes === 0 ? '#991B1B' : '#78350F', margin: 0 }}>
                ⚠️ {datos.alerta}
              </p>
            </div>
          )}
        </div>
      )}

      <form onSubmit={save} style={{ background: 'white', borderRadius: 18, padding: 26, boxShadow: '0 2px 14px rgba(0,0,0,0.07)', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#555' }}>Peso (kg)</label>
          <input type="number" value={peso} onChange={(e) => setPeso(e.target.value)} style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#555' }}>Altura (cm)</label>
          <input type="number" value={altura} onChange={(e) => setAltura(e.target.value)} style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#555' }}>Meta de entrenamiento</label>
          <input type="text" value={meta} onChange={(e) => setMeta(e.target.value)} placeholder="Ej: Ganar resistencia" style={inputStyle} />
        </div>
        <button type="submit" style={{ padding: 13, border: 'none', borderRadius: 12, background: RED, color: 'white', fontWeight: 800, cursor: 'pointer' }}>
          Guardar perfil
        </button>
      </form>
    </div>
  );
}

function Contador({ label, value, sub, alerta }) {
  return (
    <div style={{ border: `1px solid ${alerta ? '#FCD34D' : '#eee'}`, background: alerta ? '#FFFBEB' : 'white', borderRadius: 12, padding: 14 }}>
      <p style={{ fontSize: 28, fontWeight: 900, color: alerta ? '#B45309' : '#1A1A1A', lineHeight: 1 }}>{value}</p>
      <p style={{ fontSize: 12, fontWeight: 700, color: '#555', marginTop: 6 }}>{label}</p>
      <p style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{sub}</p>
    </div>
  );
}
