import { useEffect, useState } from 'react';
import { reservationsApi, reportsApi, machinesApi } from '../services/api';

const RED = '#CC0000';
const inputStyle = { width: '100%', padding: '12px 16px', border: '1.5px solid #E5E7EB', borderRadius: 10, fontSize: 14, backgroundColor: '#FAFAFA' };
const card = { backgroundColor: 'white', borderRadius: 18, padding: 26, boxShadow: '0 2px 14px rgba(0,0,0,0.07)', marginBottom: 24 };

/**
 * Panel del Profesor / Administrador.
 *
 * Este perfil NO reserva cupos: la interfaz de reserva es exclusiva de los
 * estudiantes. Aquí solo se CONSULTA EL AFORO y se gestiona la operación:
 *   RF16 aforo proyectado · RF17 asistencia/No-Show · RF18 máquinas
 *   RF17/RF19 reporte POR ESTUDIANTE y su exportación.
 */
export default function TrainerPanel({ user, reservaFecha, onChanged, showToast }) {
  const [lookupEmail, setLookup] = useState('');
  const [studentRes, setStudentRes] = useState(null);
  const [occupancy, setOccupancy] = useState([]);
  const [machines, setMachines] = useState([]);
  const [reporte, setReporte] = useState({ estudiantes: [], cancelacion_limite: 5 });
  const [newMachine, setNewMachine] = useState('');

  const refreshReports = () => {
    reportsApi.occupancy().then(setOccupancy).catch(() => {});
    machinesApi.list().then(setMachines).catch(() => {});
    reportsApi.students().then(setReporte).catch(() => {});
  };
  useEffect(refreshReports, []);

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

  const totalReservados = occupancy.reduce((s, o) => s + o.reservados, 0);
  const totalCupos = occupancy.reduce((s, o) => s + o.total, 0);
  const estudiantes = reporte.estudiantes || [];

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '36px 24px', animation: 'fadeUp 0.4s ease' }}>
      <h2 style={{ fontSize: 30, fontWeight: 900, marginBottom: 4 }}>Aforo del gimnasio</h2>
      <p style={{ color: '#999', fontSize: 15, marginBottom: 28 }}>
        {user.role === 'ADMIN' ? 'Administrador' : 'Profesor'} · {user.name}
      </p>

      {/* RF16 — Aforo proyectado del día siguiente */}
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
          <div>
            <h3 style={{ fontSize: 18, fontWeight: 800 }}>📊 Aforo proyectado</h3>
            {/* RN03 — se indica de qué día es el aforo que se está viendo */}
            <p style={{ fontSize: 13, color: '#777', marginTop: 4, textTransform: 'capitalize' }}>
              Reservas para mañana{reservaFecha?.label ? ` · ${reservaFecha.label}` : ''}
            </p>
          </div>
          <span style={{ background: '#FEE2E2', color: RED, fontSize: 13, fontWeight: 800, padding: '8px 16px', borderRadius: 20 }}>
            {totalReservados} / {totalCupos} cupos ocupados
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px,1fr))', gap: 12 }}>
          {occupancy.map((o) => (
            <div key={o.slotId} style={{ border: '1px solid #eee', borderRadius: 12, padding: 14 }}>
              <div style={{ fontWeight: 900, fontSize: 20 }}>{o.hour}</div>
              <div style={{ fontSize: 13, color: '#666', margin: '4px 0' }}>{o.reservados}/{o.total} · {o.ocupacion_pct}%</div>
              <div style={{ height: 6, background: '#F0F0F0', borderRadius: 6, overflow: 'hidden', marginTop: 6 }}>
                <div style={{ height: '100%', width: `${o.ocupacion_pct}%`, background: o.ocupacion_pct >= 80 ? '#dc2626' : '#16a34a' }} />
              </div>
              {o.enEspera > 0 && <div style={{ fontSize: 12, color: RED, marginTop: 6 }}>⏳ {o.enEspera} en espera</div>}
            </div>
          ))}
        </div>
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

      {/* RF17 — Reporte POR ESTUDIANTE + RF19 — Exportar */}
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6, flexWrap: 'wrap', gap: 8 }}>
          <h3 style={{ fontSize: 18, fontWeight: 800 }}>🧑‍🎓 Reporte por estudiante</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <a href={reportsApi.csvUrl} style={{ padding: '8px 14px', border: '1px solid #ddd', borderRadius: 8, fontSize: 12, fontWeight: 700, textDecoration: 'none', color: '#333' }}>⬇ CSV</a>
            <a href={reportsApi.pdfUrl} style={{ padding: '8px 14px', border: '1px solid #ddd', borderRadius: 8, fontSize: 12, fontWeight: 700, textDecoration: 'none', color: '#333' }}>⬇ PDF</a>
          </div>
        </div>
        <p style={{ fontSize: 13, color: '#777', marginBottom: 16 }}>
          Actividad individual de cada estudiante. Se penaliza al llegar a {reporte.cancelacion_limite} cancelaciones.
        </p>

        {estudiantes.length === 0 ? (
          <p style={{ color: '#999', fontSize: 14 }}>Aún no hay estudiantes registrados.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 560 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: '#777' }}>
                  <th style={{ padding: '8px 6px' }}>Estudiante</th>
                  <th style={{ padding: '8px 6px', textAlign: 'center' }}>Activas</th>
                  <th style={{ padding: '8px 6px', textAlign: 'center' }}>Asistió</th>
                  <th style={{ padding: '8px 6px', textAlign: 'center' }}>Canceló</th>
                  <th style={{ padding: '8px 6px', textAlign: 'center' }}>No-Show</th>
                  <th style={{ padding: '8px 6px', textAlign: 'center' }}>Estado</th>
                </tr>
              </thead>
              <tbody>
                {estudiantes.map((s) => (
                  <tr key={s.email} style={{ borderTop: '1px solid #F0F0F0', background: s.en_alerta ? '#FFFBEB' : 'transparent' }}>
                    <td style={{ padding: '10px 6px' }}>
                      <div style={{ fontWeight: 700 }}>{s.name}</div>
                      <div style={{ color: '#999', fontSize: 12 }}>{s.email}</div>
                    </td>
                    <td style={{ padding: '10px 6px', textAlign: 'center' }}>{s.activas}</td>
                    <td style={{ padding: '10px 6px', textAlign: 'center' }}>{s.completadas}</td>
                    <td style={{ padding: '10px 6px', textAlign: 'center', fontWeight: 800, color: s.en_alerta ? '#B45309' : '#333' }}>
                      {s.cancel_count}
                      <div style={{ fontSize: 10, fontWeight: 500, color: '#999' }}>
                        quedan {s.cancelaciones_restantes}
                      </div>
                    </td>
                    <td style={{ padding: '10px 6px', textAlign: 'center' }}>{s.no_show}</td>
                    <td style={{ padding: '10px 6px', textAlign: 'center' }}>
                      <span style={{
                        fontSize: 11, fontWeight: 800, padding: '3px 10px', borderRadius: 20,
                        background: s.estado === 'PENALIZADO' ? '#FEE2E2' : '#DCFCE7',
                        color: s.estado === 'PENALIZADO' ? '#991B1B' : '#15803D',
                      }}>
                        {s.estado}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
