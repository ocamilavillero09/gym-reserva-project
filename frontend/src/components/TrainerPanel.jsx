import { useEffect, useState } from 'react';
import { reservationsApi, reportsApi, machinesApi, pushApi } from '../services/api';

const RED = '#CC0000';
const inputStyle = { width: '100%', padding: '12px 16px', border: '1.5px solid #E5E7EB', borderRadius: 10, fontSize: 14, backgroundColor: '#FAFAFA' };
const card = { backgroundColor: 'white', borderRadius: 18, padding: 26, boxShadow: '0 2px 14px rgba(0,0,0,0.07)', marginBottom: 24 };

/**
 * Panel del Entrenador / Admin. Reúne:
 *  RF07 reserva a terceros · RF17 asistencia/No-Show · RF16 aforo proyectado
 *  RF18 máquinas · RF17 reporte inasistencias · RF19 exportar · RF14 recordatorios push
 */
export default function TrainerPanel({ user, slots, onChanged, showToast }) {
  const [resEmail, setResEmail] = useState('');
  const [resSlot, setResSlot] = useState(slots[0]?.id || 1);
  const [lookupEmail, setLookup] = useState('');
  const [studentRes, setStudentRes] = useState(null);
  const [occupancy, setOccupancy] = useState([]);
  const [machines, setMachines] = useState([]);
  const [noShows, setNoShows] = useState([]);
  const [newMachine, setNewMachine] = useState('');

  const refreshReports = () => {
    reportsApi.occupancy().then(setOccupancy).catch(() => {});
    machinesApi.list().then(setMachines).catch(() => {});
    reportsApi.noShows().then(setNoShows).catch(() => {});
  };
  useEffect(refreshReports, []);

  const reserveForStudent = async (e) => {
    e.preventDefault();
    try {
      await reservationsApi.create({ email: resEmail.trim().toLowerCase(), slotId: Number(resSlot), actor_email: user.email });
      showToast(`Reserva creada para ${resEmail}.`, 'success');
      setResEmail(''); onChanged?.(); refreshReports();
    } catch (err) { showToast(err.message, 'warning'); }
  };

  const lookupStudent = async (e) => {
    e.preventDefault();
    try { setStudentRes(await reservationsApi.getByEmail(lookupEmail.trim().toLowerCase())); }
    catch (err) { showToast(err.message, 'error'); }
  };

  const markNoShow = async (id) => {
    try {
      const r = await reservationsApi.noShow(id, user.email);
      showToast(r.penalizado ? 'No-Show. El estudiante quedó PENALIZADO.' : 'Inasistencia registrada.', 'info');
      setStudentRes((p) => p.filter((x) => x.id !== id)); onChanged?.(); refreshReports();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const markComplete = async (id) => {
    try {
      await reservationsApi.complete(id, user.email);
      showToast('Asistencia confirmada.', 'success');
      setStudentRes((p) => p.filter((x) => x.id !== id)); onChanged?.(); refreshReports();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const toggleMachine = async (m) => {
    const next = m.estado === 'DISPONIBLE' ? 'FUERA_DE_SERVICIO' : 'DISPONIBLE';
    try { await machinesApi.setEstado(m.machineId, next, '', user.email); refreshReports(); }
    catch (err) { showToast(err.message, 'error'); }
  };

  const addMachine = async (e) => {
    e.preventDefault();
    try { await machinesApi.create(newMachine.trim(), user.email); setNewMachine(''); refreshReports(); }
    catch (err) { showToast(err.message, 'error'); }
  };

  const sendReminder = async (slotId) => {
    try {
      const r = await pushApi.remind(slotId, user.email);
      showToast(`Recordatorios enviados: ${r.enviados ?? 0}.`, 'info');
    } catch (err) { showToast(err.message, 'warning'); }
  };

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '36px 24px', animation: 'fadeUp 0.4s ease' }}>
      <h2 style={{ fontSize: 30, fontWeight: 900, marginBottom: 4 }}>Panel del entrenador</h2>
      <p style={{ color: '#999', fontSize: 15, marginBottom: 28 }}>{user.role}</p>

      {/* RF16 — Dashboard de aforo proyectado */}
      <div style={card}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>📊 Aforo proyectado</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px,1fr))', gap: 12 }}>
          {occupancy.map((o) => (
            <div key={o.slotId} style={{ border: '1px solid #eee', borderRadius: 12, padding: 14 }}>
              <div style={{ fontWeight: 900, fontSize: 20 }}>{o.hour}</div>
              <div style={{ fontSize: 13, color: '#666', margin: '4px 0' }}>{o.reservados}/{o.total} · {o.ocupacion_pct}%</div>
              {o.enEspera > 0 && <div style={{ fontSize: 12, color: RED }}>⏳ {o.enEspera} en espera</div>}
              <button onClick={() => sendReminder(o.slotId)} style={{ marginTop: 8, width: '100%', padding: '6px 0', border: '1px solid #ddd', borderRadius: 8, background: 'white', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                🔔 Recordar
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* RF07 — Reserva para un tercero */}
      <div style={card}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>📝 Reservar para un estudiante</h3>
        <form onSubmit={reserveForStudent} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <input type="email" placeholder="correo del estudiante" value={resEmail} onChange={(e) => setResEmail(e.target.value)} style={inputStyle} required />
          <select value={resSlot} onChange={(e) => setResSlot(e.target.value)} style={inputStyle}>
            {slots.map((s) => <option key={s.id} value={s.id} disabled={s.available === 0}>{s.hour} — {s.available} cupos</option>)}
          </select>
          <button type="submit" style={{ padding: 13, border: 'none', borderRadius: 12, background: RED, color: 'white', fontWeight: 800, cursor: 'pointer' }}>Crear reserva</button>
        </form>
      </div>

      {/* RF17 — Asistencia / No-Show */}
      <div style={card}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>✔️ Asistencia e inasistencias</h3>
        <form onSubmit={lookupStudent} style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input type="email" placeholder="correo del estudiante" value={lookupEmail} onChange={(e) => setLookup(e.target.value)} style={inputStyle} required />
          <button type="submit" style={{ padding: '12px 20px', border: '1.5px solid #E5E7EB', borderRadius: 10, background: 'white', fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' }}>Buscar</button>
        </form>
        {studentRes && studentRes.length === 0 && <p style={{ color: '#999', fontSize: 14 }}>Sin reservas activas.</p>}
        {studentRes && studentRes.map((r) => (
          <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #F0F0F0', gap: 8 }}>
            <span style={{ fontWeight: 700 }}>{r.hour} <span style={{ color: '#999', fontWeight: 400, fontSize: 13 }}>· {r.date}</span></span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => markComplete(r.id)} style={{ padding: '8px 14px', border: '1.5px solid #86efac', borderRadius: 10, background: 'white', color: '#15803d', fontWeight: 700, fontSize: 13, cursor: 'pointer' }}>Asistió</button>
              <button onClick={() => markNoShow(r.id)} style={{ padding: '8px 14px', border: '1.5px solid #fca5a5', borderRadius: 10, background: 'white', color: RED, fontWeight: 700, fontSize: 13, cursor: 'pointer' }}>No-Show</button>
            </div>
          </div>
        ))}
      </div>

      {/* RF18 — Máquinas */}
      <div style={card}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>🛠️ Máquinas</h3>
        {machines.map((m) => (
          <div key={m.machineId} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #F0F0F0' }}>
            <span style={{ fontWeight: 600 }}>{m.name}
              <span style={{ marginLeft: 10, fontSize: 12, fontWeight: 800, color: m.estado === 'DISPONIBLE' ? '#15803d' : RED }}>
                {m.estado === 'DISPONIBLE' ? '● Disponible' : '● Fuera de servicio'}
              </span>
            </span>
            <button onClick={() => toggleMachine(m)} style={{ padding: '6px 14px', border: '1px solid #ddd', borderRadius: 8, background: 'white', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
              {m.estado === 'DISPONIBLE' ? 'Marcar fuera' : 'Reactivar'}
            </button>
          </div>
        ))}
        <form onSubmit={addMachine} style={{ display: 'flex', gap: 10, marginTop: 14 }}>
          <input value={newMachine} onChange={(e) => setNewMachine(e.target.value)} placeholder="Nueva máquina" style={inputStyle} required />
          <button type="submit" style={{ padding: '12px 20px', border: 'none', borderRadius: 10, background: RED, color: 'white', fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' }}>Agregar</button>
        </form>
      </div>

      {/* RF17 — Reporte de inasistencias + RF19 — Exportar */}
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: 18, fontWeight: 800 }}>⚠️ Reporte de inasistencias</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <a href={reportsApi.csvUrl} style={{ padding: '8px 14px', border: '1px solid #ddd', borderRadius: 8, fontSize: 12, fontWeight: 700, textDecoration: 'none', color: '#333' }}>⬇ CSV</a>
            <a href={reportsApi.pdfUrl} style={{ padding: '8px 14px', border: '1px solid #ddd', borderRadius: 8, fontSize: 12, fontWeight: 700, textDecoration: 'none', color: '#333' }}>⬇ PDF</a>
          </div>
        </div>
        {noShows.length === 0 ? <p style={{ color: '#999', fontSize: 14 }}>Sin inasistencias registradas.</p> : noShows.map((n) => (
          <div key={n.email} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #F0F0F0', fontSize: 14 }}>
            <span>{n.name} <span style={{ color: '#999' }}>({n.email})</span></span>
            <span style={{ fontWeight: 800, color: n.estado === 'PENALIZADO' ? RED : '#333' }}>{n.no_show_count} · {n.estado}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
