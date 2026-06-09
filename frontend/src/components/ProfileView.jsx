import { useEffect, useState } from 'react';
import { profileApi } from '../services/api';
import { enablePush } from '../services/push';

const RED = '#CC0000';
const inputStyle = { width: '100%', padding: '12px 16px', border: '1.5px solid #E5E7EB', borderRadius: 10, fontSize: 14, backgroundColor: '#FAFAFA' };

// RF13 — Perfil de usuario y metas + RF14 — activar notificaciones push.
export default function ProfileView({ user, showToast }) {
  const [peso, setPeso] = useState('');
  const [altura, setAltura] = useState('');
  const [meta, setMeta] = useState('');

  useEffect(() => {
    profileApi.get(user.email).then((p) => {
      setPeso(p.peso ?? '');
      setAltura(p.altura ?? '');
      setMeta(p.meta ?? '');
    }).catch(() => {});
  }, [user.email]);

  const save = async (e) => {
    e.preventDefault();
    try {
      await profileApi.update({
        email: user.email,
        peso: peso === '' ? null : Number(peso),
        altura: altura === '' ? null : Number(altura),
        meta,
      });
      showToast('Perfil actualizado.', 'success');
    } catch (err) { showToast(err.message, 'error'); }
  };

  const activarPush = async () => {
    try {
      await enablePush(user.email);
      showToast('Notificaciones activadas en este dispositivo.', 'success');
    } catch (err) { showToast(err.message, 'warning'); }
  };

  return (
    <div style={{ maxWidth: 560, margin: '0 auto', padding: '36px 24px', animation: 'fadeUp 0.4s ease' }}>
      <h2 style={{ fontSize: 30, fontWeight: 900, marginBottom: 4 }}>Mi perfil</h2>
      <p style={{ color: '#999', fontSize: 15, marginBottom: 28 }}>{user.name} · {user.email}</p>

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

      {/* RF14 — Push */}
      <div style={{ background: 'white', borderRadius: 18, padding: 26, marginTop: 20, boxShadow: '0 2px 14px rgba(0,0,0,0.07)' }}>
        <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 8 }}>🔔 Recordatorios</h3>
        <p style={{ color: '#777', fontSize: 13, marginBottom: 14 }}>
          Activa las notificaciones para recibir un recordatorio antes de tu bloque.
        </p>
        <button onClick={activarPush} style={{ padding: '10px 18px', border: `1.5px solid ${RED}`, borderRadius: 10, background: 'white', color: RED, fontWeight: 700, cursor: 'pointer' }}>
          Activar notificaciones
        </button>
      </div>
    </div>
  );
}
