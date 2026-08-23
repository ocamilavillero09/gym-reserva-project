/*
 * PANEL DEL GIMNASIO (ENTRENADOR / ADMINISTRADOR)
 *
 * Este perfil NO reserva cupos: solo consulta el aforo y gestiona la
 * operación diaria — registrar asistencias, procesar inasistencias y revisar
 * el reporte del día.
 *
 * Solo estructura y comportamiento. La presentación vive en
 * src/styles/panel.css.
 */
import { useCallback, useEffect, useState } from 'react';
import { attendanceApi, reportsApi } from '../services/api';
import '../styles/panel.css';

export default function TrainerPanel({ user, reservaFecha, onChanged, showToast }) {
  const [documento, setDocumento] = useState('');
  const [busqueda, setBusqueda] = useState(null);
  const [pendientes, setPendientes] = useState(null);
  const [diario, setDiario] = useState(null);
  const [occupancy, setOccupancy] = useState([]);
  const [procesando, setProcesando] = useState(false);
  const [generandoPdf, setGenerandoPdf] = useState(false);

  const esAdmin = user.role === 'ADMIN';

  const refrescar = useCallback(() => {
    reportsApi.occupancy().then(setOccupancy).catch(() => {});
    attendanceApi.pending(user.email).then(setPendientes).catch(() => {});
    reportsApi.daily(user.email).then(setDiario).catch(() => {});
  }, [user.email]);

  useEffect(refrescar, [refrescar]);

  // Buscar al estudiante por su documento de identidad.
  const buscar = async (e) => {
    e.preventDefault();
    setBusqueda(null);
    try {
      setBusqueda(await attendanceApi.lookup(documento.trim(), user.email));
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Registrar la asistencia del estudiante.
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

  // Procesar de forma general las inasistencias de la jornada.
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

  // Descarga del reporte diario en PDF.
  //
  // Antes era un enlace <a target="_blank"> y daba dos problemas: el navegador
  // devolvía el PDF guardado en caché (por eso «no se actualizaba») y el clic
  // se perdía cuando el bloqueador de ventanas emergentes lo interceptaba.
  // Ahora se refresca el reporte, se pide el archivo y se entrega directamente.
  const descargarPdf = async () => {
    setGenerandoPdf(true);
    try {
      const fecha = diario?.fecha ?? '';
      // Primero se refresca lo que se ve en pantalla, para que el PDF y el
      // panel muestren exactamente lo mismo.
      const fresco = await reportsApi.daily(user.email, fecha).catch(() => null);
      if (fresco) setDiario(fresco);

      const blob = await reportsApi.dailyPdf(user.email, fecha);
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = `reporte-diario-${fecha || 'hoy'}.pdf`;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(url);
      showToast('Reporte diario generado.', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setGenerandoPdf(false);
    }
  };

  const totalReservados = occupancy.reduce((s, o) => s + o.reservados, 0);
  const totalCupos = occupancy.reduce((s, o) => s + o.total, 0);
  const t = diario?.totales;

  return (
    <div className="panel">
      <h2 className="panel__titulo">Panel del gimnasio</h2>
      <p className="panel__subtitulo">
        {esAdmin ? 'Administrador' : 'Entrenador'} · {user.name}
      </p>

      {/* Bloques horarios establecidos y sus cupos */}
      <div className="panel__tarjeta">
        <div className="panel__encabezado">
          <div>
            <h3 className="panel__seccion">🕒 Bloques horarios y cupos</h3>
            <p className="panel__descripcion panel__fecha">
              Disponibilidad para mañana{reservaFecha?.label ? ` · ${reservaFecha.label}` : ''}
            </p>
          </div>
          <span className="panel__aforo">
            {totalReservados} ocupados / {totalCupos} cupos
          </span>
        </div>
        <div className="panel__bloques">
          {occupancy.map((o) => (
            <div key={o.slotId} className="aforo">
              <div className="aforo__hora">{o.hour}</div>
              <div className="aforo__cifras">
                {o.reservados} ocupados · {o.available} libres
              </div>
              <div className="aforo__barra">
                <div
                  className={`aforo__barra-relleno aforo__barra-relleno--${o.ocupacion_pct >= 80 ? 'alto' : 'normal'}`}
                  style={{ width: `${o.ocupacion_pct}%` }}
                />
              </div>
              <div className="aforo__porcentaje">{o.ocupacion_pct}% de aforo</div>
            </div>
          ))}
        </div>
        <p className="panel__nota">
          Los entrenadores y administradores consultan la disponibilidad; las reservas son
          exclusivas de los estudiantes.
        </p>
      </div>

      {/* Buscar por documento y registrar asistencia */}
      <div className="panel__tarjeta">
        <h3 className="panel__seccion">🪪 Registrar asistencia</h3>
        <p className="panel__descripcion">
          Busca al estudiante por su documento de identidad para verificar si tiene reserva.
        </p>
        <form className="panel__busqueda" onSubmit={buscar}>
          <input
            className="panel__entrada"
            type="text"
            placeholder="Documento de identidad del estudiante"
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            inputMode="numeric"
            required
          />
          <button className="panel__boton panel__boton--claro" type="submit">Buscar</button>
        </form>

        {busqueda && (
          <div className="hallazgo">
            <div className="hallazgo__cabecera">
              <div>
                <p className="hallazgo__nombre">{busqueda.estudiante.name}</p>
                <p className="hallazgo__correo">
                  Doc. {busqueda.estudiante.documento} · {busqueda.estudiante.email}
                </p>
              </div>
              <span className={`hallazgo__estado hallazgo__estado--${
                busqueda.estudiante.estado === 'PENALIZADO' ? 'penalizado' : 'activo'}`}>
                {busqueda.estudiante.estado}
              </span>
            </div>
            <p className="hallazgo__cuenta">
              Inasistencias: {busqueda.estudiante.no_show_count} de {busqueda.estudiante.no_show_limite}
            </p>

            {!busqueda.tiene_reserva ? (
              <p className="hallazgo__sin-reserva">
                ⚠ Este estudiante no tiene ninguna reserva activa.
              </p>
            ) : busqueda.reservas.map((r) => (
              <div key={r.id} className="hallazgo__reserva">
                <span className="hallazgo__hora">
                  {r.hour}
                  <span className="hallazgo__fecha"> · {r.date}</span>
                  {r.es_de_hoy && <span className="hallazgo__hoy">HOY</span>}
                </span>
                {/* La asistencia solo se registra el día de la reserva: si es
                    para más adelante, el estudiante aún no ha podido venir. */}
                {r.se_puede_registrar ? (
                  <button className="panel__boton" onClick={() => registrarAsistencia(r.id)}>
                    Registrar asistencia
                  </button>
                ) : (
                  <span className="hallazgo__pendiente">
                    🗓️ Aún no es el día de esta reserva
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Sin asistencia registrada + proceso general de la jornada */}
      <div className="panel__tarjeta">
        <div className="panel__encabezado">
          <div>
            <h3 className="panel__seccion">⏳ Sin asistencia registrada</h3>
            <p className="panel__descripcion">
              Estudiantes con reserva que no han registrado asistencia
              {pendientes?.fecha_label ? ` · ${pendientes.fecha_label}` : ''}.
            </p>
          </div>
          <button className="panel__boton" onClick={procesarInasistencias} disabled={procesando}>
            {procesando ? 'Procesando...' : 'Procesar inasistencias'}
          </button>
        </div>
        <p className="panel__nota">
          Al procesar se registra la inasistencia de cada uno y se penaliza a quien llegue
          a {pendientes?.no_show_limite ?? 5} inasistencias.
        </p>

        {!pendientes || pendientes.total === 0 ? (
          <p className="panel__vacio">
            No hay estudiantes pendientes: todas las reservas de la jornada están procesadas.
          </p>
        ) : (
          <div className="panel__tabla-marco">
            <table className="panel__tabla">
              <thead>
                <tr>
                  <th>Estudiante</th>
                  <th>Documento</th>
                  <th>Bloque</th>
                  <th className="panel__tabla-centro">Inasistencias</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {pendientes.pendientes.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <div className="pendiente__nombre">{p.name}</div>
                      <div className="pendiente__correo">{p.email}</div>
                    </td>
                    <td>{p.documento}</td>
                    <td>
                      {p.hour}
                      <div className="pendiente__correo">{p.date}</div>
                    </td>
                    <td className="panel__tabla-centro pendiente__contador">
                      {p.no_show_count}
                      <div className="pendiente__restante">
                        faltan {p.inasistencias_restantes}
                      </div>
                    </td>
                    <td className="panel__tabla-derecha">
                      <button
                        className="panel__boton panel__boton--asistio"
                        onClick={() => registrarAsistencia(p.id)}
                      >
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

      {/* Reporte general diario y su impresión en PDF */}
      <div className="panel__tarjeta">
        <div className="panel__encabezado">
          <div>
            <h3 className="panel__seccion">📄 Reporte general diario</h3>
            <p className="panel__descripcion panel__fecha">
              {diario?.fecha_label || 'Actividad del día'}
            </p>
          </div>
          <div className="panel__acciones">
            <button
              className="panel__boton panel__boton--claro"
              onClick={refrescar}
              type="button"
            >
              🔄 Actualizar
            </button>
            <button
              className="panel__boton"
              onClick={descargarPdf}
              disabled={generandoPdf}
              type="button"
            >
              {generandoPdf ? 'Generando...' : '🖨️ Generar PDF'}
            </button>
          </div>
        </div>

        <div className="panel__totales">
          <Total label="Asistencias" value={t?.asistencias ?? 0} tipo="asistencias" />
          <Total label="Cancelaciones" value={t?.cancelaciones ?? 0} tipo="cancelaciones" />
          <Total label="Inasistencias" value={t?.inasistencias ?? 0} tipo="inasistencias" />
          <Total label="Estudiantes penalizados" value={t?.estudiantes_penalizados ?? 0} tipo="penalizados" />
        </div>

        {diario?.penalizados?.length > 0 && (
          <div>
            <p className="panel__lista-titulo">Estudiantes penalizados</p>
            {diario.penalizados.map((p) => (
              <div key={p.email} className="penalizado">
                <span className="penalizado__nombre">
                  {p.name}
                  <span className="penalizado__documento"> · doc. {p.documento}</span>
                </span>
                <span className="penalizado__faltas">{p.no_show_count} inasistencias</span>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}

function Total({ label, value, tipo }) {
  return (
    <div className={`total total--${tipo}`}>
      <p className="total__valor">{value}</p>
      <p className="total__label">{label}</p>
    </div>
  );
}
