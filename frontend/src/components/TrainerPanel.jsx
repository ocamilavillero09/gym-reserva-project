import { useState } from 'react';
import { reservationsApi } from '../services/api';

const RED = '#CC0000';

const inputStyle = {
  width: '100%', padding: '12px 16px', border: '1.5px solid #E5E7EB',
  borderRadius: 10, fontSize: 14, backgroundColor: '#FAFAFA',
};

const card = {
  backgroundColor: 'white', borderRadius: 18, padding: 26,
  boxShadow: '0 2px 14px rgba(0,0,0,0.07)', marginBottom: 24,
};

/**
 * Panel del Entrenador / Admin (RF07 + RN09).
 *  - Reservar un cupo para un estudiante que lo solicita presencialmente.
 *  - Consultar las reservas activas de un estudiante y marcar inasistencias.
 */
export default function TrainerPanel({ user, slots, onChanged, showToast }) {
  const [resEmail, setResEmail]   = useState('');
  const [resSlot, setResSlot]     = useState(slots[0]?.id || 1);
  const [lookupEmail, setLookup]  = useState('');
  const [studentRes, setStudentRes] = useState(null);

  const reserveForStudent = async (e) => {
    e.preventDefault();
    try {
      await reservationsApi.create({ email: resEmail.trim().toLowerCase(), slotId: Number(resSlot), actor_email: user.email });
      showToast(`Reserva creada para ${resEmail}.`, 'success');
      setResEmail('');
      onChanged?.();
    } catch (err) { showToast(err.message, 'warning'); }
  };

  const lookupStudent = async (e) => {
    e.preventDefault();
    try {
      const data = await reservationsApi.getByEmail(lookupEmail.trim().toLowerCase());
      setStudentRes(data);
    } catch (err) { showToast(err.message, 'error'); }
  };

  const markNoShow = async (id) => {
    try {
      const r = await reservationsApi.noShow(id, user.email);
      showToast(r.penalizado ? 'Inasistencia registrada. El estudiante quedó PENALIZADO.' : 'Inasistencia registrada.', 'info');
      setStudentRes((prev) => prev.filter((x) => x.id !== id));
      onChanged?.();
    } catch (err) { showToast(err.message, 'error'); }
  };

  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '36px 24px', animation: 'fadeUp 0.4s ease' }}>
      <h2 style={{ fontSize: 30, fontWeight: 900, color: '#1A1A1A', marginBottom: 4 }}>Panel del entrenador</h2>
      <p style={{ color: '#999', fontSize: 15, marginBottom: 28 }}>
        Gestión de reservas presenciales e inasistencias ({user.role})
      </p>

      {/* RF07 — Reserva manual para un tercero */}
      <div style={card}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>📝 Reservar para un estudiante</h3>
        <form onSubmit={reserveForStudent} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <input type="email" placeholder="correo del estudiante" value={resEmail}
                 onChange={(e) => setResEmail(e.target.value)} style={inputStyle} required />
          <select value={resSlot} onChange={(e) => setResSlot(e.target.value)} style={inputStyle}>
            {slots.map((s) => (
              <option key={s.id} value={s.id} disabled={s.available === 0}>
                {s.hour} — {s.available} cupos
              </option>
            ))}
          </select>
          <button type="submit" style={{
            padding: 13, border: 'none', borderRadius: 12, backgroundColor: RED,
            color: 'white', fontWeight: 800, fontSize: 14, cursor: 'pointer',
          }}>Crear reserva</button>
        </form>
      </div>

      {/* RN09 — Marcar inasistencias */}
      <div style={card}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>⚠️ Registrar inasistencia (No-Show)</h3>
        <form onSubmit={lookupStudent} style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input type="email" placeholder="correo del estudiante" value={lookupEmail}
                 onChange={(e) => setLookup(e.target.value)} style={inputStyle} required />
          <button type="submit" style={{
            padding: '12px 20px', border: '1.5px solid #E5E7EB', borderRadius: 10,
            backgroundColor: 'white', fontWeight: 700, fontSize: 14, cursor: 'pointer', whiteSpace: 'nowrap',
          }}>Buscar</button>
        </form>

        {studentRes && studentRes.length === 0 && (
          <p style={{ color: '#999', fontSize: 14 }}>Sin reservas activas.</p>
        )}
        {studentRes && studentRes.map((r) => (
          <div key={r.id} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '12px 0', borderBottom: '1px solid #F0F0F0',
          }}>
            <span style={{ fontWeight: 700 }}>{r.hour} <span style={{ color: '#999', fontWeight: 400, fontSize: 13 }}>· {r.date}</span></span>
            <button onClick={() => markNoShow(r.id)} style={{
              padding: '8px 16px', border: '1.5px solid #fca5a5', borderRadius: 10,
              backgroundColor: 'white', color: RED, fontWeight: 700, fontSize: 13, cursor: 'pointer',
            }}>Marcar No-Show</button>
          </div>
        ))}
      </div>
    </div>
  );
}
