/*
 * HISTORIAL DE ENTRENAMIENTOS  (RF17)
 *
 * Solo estructura y comportamiento. La presentación vive en
 * src/styles/reservas.css.
 */
import { useEffect, useState } from 'react';
import { reservationsApi } from '../services/api';
import '../styles/reservas.css';

const ESTADO = {
  COMPLETADA: { clase: 'asistio',   label: 'Asistió' },
  CANCELADA:  { clase: 'cancelada', label: 'Cancelada' },
  NO_SHOW:    { clase: 'falto',     label: 'No asistió' },
};

export default function HistoryView({ user }) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    reservationsApi.history(user.email).then(setHistory).catch(() => setHistory([]));
  }, [user.email]);

  return (
    <div className="reservas">
      <h2 className="reservas__titulo">Mi historial</h2>
      <p className="reservas__subtitulo">Tus entrenamientos pasados</p>

      {history.length === 0 ? (
        <div className="historial__vacio">
          <div className="historial__vacio-icono">📖</div>
          <p>Aún no tienes historial.</p>
        </div>
      ) : (
        <div className="historial__lista">
          {history.map((h) => {
            const estado = ESTADO[h.estado] || { clase: 'otro', label: h.estado };
            return (
              <div key={h.id} className="historial__fila">
                <span className="historial__hora">
                  {h.hour} <span className="historial__fecha">· {h.date}</span>
                </span>
                <span className={`historial__estado historial__estado--${estado.clase}`}>
                  {estado.label}
                </span>
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}
