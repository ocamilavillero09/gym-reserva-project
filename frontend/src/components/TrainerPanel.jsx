import { useCallback, useEffect, useState } from 'react';
import { attendanceApi, reportsApi, machinesApi } from '../services/api';

const RED = '#CC0000';
const inputStyle = { width: '100%', padding: '12px 16px', border: '1.5px solid #E5E7EB', borderRadius: 10, fontSize: 14, backgroundColor: '#FAFAFA' };
const card = { backgroundColor: 'white', borderRadius: 18, padding: 26, boxShadow: '0 2px 14px rgba(0,0,0,0.07)', marginBottom: 24 };
const btn = { padding: '10px 18px', border: 'none', borderRadius: 10, background: RED, color: 'white', fontWeight: 800, fontSize: 13, cursor: 'pointer', whiteSpace: 'nowrap' };
const btnGhost = { padding: '10px 18px', border: '1.5px solid #E5E7EB', borderRadius: 10, background: 'white', fontWeight: 700, fontSize: 13, cursor: 'pointer', whiteSpace: 'nowrap' };

/**
 * Panel del Entrenador / Administrador.
 *
 * Este perfil NO reserva cupos (RF12): solo consulta y gestiona la operación.
 *   RF06/RF07/RF12  Bloques horarios establecidos y sus cupos
 *   RF11/HU11       Buscar la reserva de un estudiante por su DOCUMENTO
 *   RF13/HU12       Registrar la asistencia del estudiante
 *   RF14/HU13-HU15  Estudiantes con reserva y sin asistencia registrada
 *   RF15/HU14-HU16  Procesar de forma general las inasistencias de la jornada
 *   RF19/HU17-HU18  Reporte general diario
 *   RF20/HU19-HU20  El reporte general diario en PDF, para imprimir
 */
export default function TrainerPanel({ user, reservaFecha, onChanged, showToast }) {
  const [documento, setDocumento] = useState('');
  const [busqueda, setBusqueda] = useState(null);       // RF11
  const [pendientes, setPendientes] = useState(null);   // RF14
  const [diario, setDiario] = useState(null);           // RF19
  const [occupancy, setOccupancy] = useState([]);       // RF06/RF07
  const [machines, setMachines] = useState([]);
  const [newMachine, setNewMachine] = useState('');
  const [procesando, setProcesando] = useState(false);

  const esAdmin = user.role === 'ADMIN';

  const refrescar = useCallback(() => {
    reportsApi.occupancy().then(setOccupancy).catch(() => {});
    attendanceApi.pending(user.email).then(setPendientes).catch(() => {});
    reportsApi.daily(user.email).then(setDiario).catch(() => {});
    machinesApi.list().then(setMachines).catch(() => {});
  }, [user.email]);

  useEffect(refrescar, [refrescar]);

  // ── RF11 / HU11 — Buscar al estudiante por su documento de identidad ─────
  const buscar = async (e) => {
    e.preventDefault();
    setBusqueda(null);
    try {
      setBusqueda(await attendanceApi.lookup(documento.trim(), user.email));
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // ── RF13 / HU12 — Registrar la asistencia del estudiante ────────────────
  const registrarAsistencia = async (reservationId) => {
    try {
      const r = await attendanceApi.register({
        actor_email: user.email,
        reservation_id: reservationId,
      });
      showToast(r.notificacion || 'Asistencia registrada.', 'success');
      setBusqueda(null);
      setDocumento('');
      onChanged?.();
      refrescar();
    } catch (err) { showToast(err.message, 'error'); }
  };

  // ── RF15 / HU14 / HU16 — Procesar de forma general las inasistencias ────
  const procesarInasistencias = async () => {
    const total = pendientes?.total ?? 0;
    if (total === 0) { showToast('No hay inasistencias pendientes por procesar.', 'info'); return; }
    if (!window.confirm(
      `Se marcarán ${total} inasistencias y se aplicarán las penalizaciones correspondientes. ¿Continuar?`
    )) return;
    setProcesando(true);
    try {
      const r = await attendanceApi.process(user.email);
      showToast(r.message, r.total_penalizados > 0 ? 'warning' : 'success');
      onChanged?.();
      refrescar();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setProcesando(false);
    }
  };

  const toggleMachine = async (m) => {
    const next = m.estado === 'DISPONIBLE' ? 'FUERA_DE_SERVICIO' : 'DISPONIBLE';
    try { await machinesApi.setEstado(m.machineId, next, '', user.email); refrescar(); }
    catch (err) { showToast(err.message, 'error'); }
  };

  const addMachine = async (e) => {
    e.preventDefault();
    try { await machinesApi.create(newMachine.trim(), user.email); setNewMachine(''); refrescar(); }
    catch (err) { showToast(err.message, 'error'); }
  };

  const totalReservados = occupancy.reduce((s, o) => s + o.reservados, 0);
  const totalCupos = occupancy.reduce((s, o) => s + o.total, 0);
  const t = diario?.totales;

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: '36px 24px', animation: 'fadeUp 0.4s ease' }}>
      <h2 style={{ fontSize: 30, fontWeight: 900, marginBottom: 4 }}>Panel del gimnasio</h2>
      <p style={{ color: '#999', fontSize: 15, marginBottom: 28 }}>
        {esAdmin ? 'Administrador' : 'Entrenador'} · {user.name}
      </p>

      {/* ── RF06 / RF07 / RF12 — Bloques horarios y sus cupos ──────────────── */}
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
          <div>
            <h3 style={{ fontSize: 18, fontWeight: 800 }}>🕒 Bloques horarios y cupos</h3>
            <p style={{ fontSize: 13, color: '#777', marginTop: 4, textTransform: 'capitalize' }}>
              Disponibilidad para mañana{reservaFecha?.label ? ` · ${reservaFecha.label}` : ''}
            </p>
          </div>
          <span style={{ background: '#FEE2E2', color: RED, fontSize: 13, fontWeight: 800, padding: '8px 16px', borderRadius: 20 }}>
            {totalReservados} ocupados / {totalCupos} cupos
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px,1fr))', gap: 12 }}>
          {occupancy.map((o) => (
            <div key={o.slotId} style={{ border: '1px solid #eee', borderRadius: 12, padding: 14 }}>
              <div style={{ fontWeight: 900, fontSize: 20 }}>{o.hour}</div>
              <div style={{ fontSize: 13, color: '#666', margin: '4px 0' }}>
                {o.reservados} ocupados · {o.available} libres
              </div>
              <div style={{ height: 6, background: '#F0F0F0', borderRadius: 6, overflow: 'hidden', marginTop: 6 }}>
                <div style={{ height: '100%', width: `${o.ocupacion_pct}%`, background: o.ocupacion_pct >= 80 ? '#dc2626' : '#16a34a' }} />
              </div>
              <div style={{ fontSize: 12, color: '#999', marginTop: 6 }}>{o.ocupacion_pct}% de aforo</div>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 12, color: '#999', marginTop: 14 }}>
          Los entrenadores y administradores consultan la disponibilidad; las reservas son
          exclusivas de los estudiantes.
        </p>
      </div>

      {/* ── RF11 / RF13 — Buscar por documento y registrar asistencia ─────── */}
      <div style={card}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 6 }}>🪪 Registrar asistencia</h3>
        <p style={{ fontSize: 13, color: '#777', marginBottom: 16 }}>
          Busca al estudiante por su documento de identidad para verificar si tiene reserva.
        </p>
        <form onSubmit={buscar} style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input
            type="text"
            placeholder="Documento de identidad del estudiante"
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            style={inputStyle}
            inputMode="numeric"
            required
          />
          <button type="submit" style={btnGhost}>Buscar</button>
        </form>

        {busqueda && (
          <div style={{ border: '1px solid #eee', borderRadius: 12, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
              <div>
                <p style={{ fontWeight: 800, fontSize: 15 }}>{busqueda.estudiante.name}</p>
                <p style={{ fontSize: 12, color: '#999' }}>
                  Doc. {busqueda.estudiante.documento} · {busqueda.estudiante.email}
                </p>
              </div>
              <span style={{
                fontSize: 11, fontWeight: 800, padding: '4px 12px', borderRadius: 20, height: 'fit-content',
                background: busqueda.estudiante.estado === 'PENALIZADO' ? '#FEE2E2' : '#DCFCE7',
                color: busqueda.estudiante.estado === 'PENALIZADO' ? '#991B1B' : '#15803D',
              }}>
                {busqueda.estudiante.estado}
              </span>
            </div>
            <p style={{ fontSize: 12, color: '#777', marginBottom: 12 }}>
              Inasistencias: {busqueda.estudiante.no_show_count} de {busqueda.estudiante.no_show_limite}
            </p>

            {!busqueda.tiene_reserva ? (
              <p style={{ color: '#991B1B', fontSize: 14, fontWeight: 700 }}>
                ⚠ Este estudiante no tiene ninguna reserva activa.
              </p>
            ) : busqueda.reservas.map((r) => (
              <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: '12px 0', borderTop: '1px solid #F0F0F0', flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 700 }}>
                  {r.hour}
                  <span style={{ color: '#999', fontWeight: 400, fontSize: 13 }}> · {r.date}</span>
                  {r.es_de_hoy && (
                    <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 800, color: '#15803D' }}>HOY</span>
                  )}
                </span>
                <button onClick={() => registrarAsistencia(r.id)} style={btn}>
                  Registrar asistencia
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── RF14 / RF15 — Sin asistencia registrada + proceso general ──────── */}
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10, marginBottom: 6 }}>
          <div>
            <h3 style={{ fontSize: 18, fontWeight: 800 }}>⏳ Sin asistencia registrada</h3>
            <p style={{ fontSize: 13, color: '#777', marginTop: 4 }}>
              Estudiantes con reserva que no han registrado asistencia
              {pendientes?.fecha_label ? ` · ${pendientes.fecha_label}` : ''}.
            </p>
          </div>
          <button onClick={procesarInasistencias} disabled={procesando} style={{ ...btn, opacity: procesando ? 0.6 : 1 }}>
            {procesando ? 'Procesando...' : 'Procesar inasistencias'}
          </button>
        </div>
        <p style={{ fontSize: 12, color: '#999', marginBottom: 16 }}>
          Al procesar se registra la inasistencia de cada uno y se penaliza a quien llegue
          a {pendientes?.no_show_limite ?? 5} inasistencias.
        </p>

        {!pendientes || pendientes.total === 0 ? (
          <p style={{ color: '#999', fontSize: 14 }}>
            No hay estudiantes pendientes: todas las reservas de la jornada están procesadas.
          </p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 520 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: '#777' }}>
                  <th style={{ padding: '8px 6px' }}>Estudiante</th>
                  <th style={{ padding: '8px 6px' }}>Documento</th>
                  <th style={{ padding: '8px 6px' }}>Bloque</th>
                  <th style={{ padding: '8px 6px', textAlign: 'center' }}>Inasistencias</th>
                  <th style={{ padding: '8px 6px' }} />
                </tr>
              </thead>
              <tbody>
                {pendientes.pendientes.map((p) => (
                  <tr key={p.id} style={{ borderTop: '1px solid #F0F0F0' }}>
                    <td style={{ padding: '10px 6px' }}>
                      <div style={{ fontWeight: 700 }}>{p.name}</div>
                      <div style={{ color: '#999', fontSize: 12 }}>{p.email}</div>
                    </td>
                    <td style={{ padding: '10px 6px' }}>{p.documento}</td>
                    <td style={{ padding: '10px 6px' }}>{p.hour}<div style={{ color: '#999', fontSize: 12 }}>{p.date}</div></td>
                    <td style={{ padding: '10px 6px', textAlign: 'center', fontWeight: 800 }}>
                      {p.no_show_count}
                      <div style={{ fontSize: 10, fontWeight: 500, color: '#999' }}>
                        faltan {p.inasistencias_restantes}
                      </div>
                    </td>
                    <td style={{ padding: '10px 6px', textAlign: 'right' }}>
                      <button onClick={() => registrarAsistencia(p.id)} style={{ ...btnGhost, color: '#15803d', borderColor: '#86efac' }}>
                        Asistió
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── RF19 / RF20 — Reporte general diario y su impresión en PDF ─────── */}
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10, marginBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: 18, fontWeight: 800 }}>📄 Reporte general diario</h3>
            <p style={{ fontSize: 13, color: '#777', marginTop: 4, textTransform: 'capitalize' }}>
              {diario?.fecha_label || 'Actividad del día'}
            </p>
          </div>
          <a
            href={reportsApi.dailyPdfUrl(user.email)}
            target="_blank"
            rel="noreferrer"
            style={{ ...btn, textDecoration: 'none', display: 'inline-block' }}
          >
            🖨️ Generar PDF
          </a>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px,1fr))', gap: 12, marginBottom: 18 }}>
          <Total label="Asistencias" value={t?.asistencias ?? 0} color="#15803D" />
          <Total label="Cancelaciones" value={t?.cancelaciones ?? 0} color="#4B5563" />
          <Total label="Inasistencias" value={t?.inasistencias ?? 0} color="#B45309" />
          <Total label="Estudiantes penalizados" value={t?.estudiantes_penalizados ?? 0} color={RED} />
        </div>

        {diario?.penalizados?.length > 0 && (
          <div>
            <p style={{ fontSize: 13, fontWeight: 700, color: '#555', marginBottom: 8 }}>
              Estudiantes penalizados
            </p>
            {diario.penalizados.map((p) => (
              <div key={p.email} style={{ display: 'flex', justifyContent: 'space-between', gap: 10, padding: '8px 0', borderBottom: '1px solid #F0F0F0', fontSize: 13 }}>
                <span style={{ fontWeight: 700 }}>{p.name}<span style={{ color: '#999', fontWeight: 400 }}> · doc. {p.documento}</span></span>
                <span style={{ color: RED, fontWeight: 800 }}>{p.no_show_count} inasistencias</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Extra — Mantenimiento de máquinas */}
      <div style={card}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>🛠️ Máquinas</h3>
        {machines.map((m) => (
          <div key={m.machineId} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #F0F0F0' }}>
            <span style={{ fontWeight: 600 }}>{m.name}
              <span style={{ marginLeft: 10, fontSize: 12, fontWeight: 800, color: m.estado === 'DISPONIBLE' ? '#15803d' : RED }}>
                {m.estado === 'DISPONIBLE' ? '● Disponible' : '● Fuera de servicio'}
              </span>
            </span>
            <button onClick={() => toggleMachine(m)} style={{ ...btnGhost, padding: '6px 14px', fontSize: 12 }}>
              {m.estado === 'DISPONIBLE' ? 'Marcar fuera' : 'Reactivar'}
            </button>
          </div>
        ))}
        <form onSubmit={addMachine} style={{ display: 'flex', gap: 10, marginTop: 14 }}>
          <input value={newMachine} onChange={(e) => setNewMachine(e.target.value)} placeholder="Nueva máquina" style={inputStyle} required />
          <button type="submit" style={btn}>Agregar</button>
        </form>
      </div>
    </div>
  );
}

function Total({ label, value, color }) {
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 12, padding: 16, textAlign: 'center' }}>
      <p style={{ fontSize: 32, fontWeight: 900, color, lineHeight: 1 }}>{value}</p>
      <p style={{ fontSize: 12, fontWeight: 700, color: '#555', marginTop: 8 }}>{label}</p>
    </div>
  );
}
