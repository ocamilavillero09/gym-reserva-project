/*
 * MIS RESERVAS
 *
 * Solo estructura y comportamiento. La presentación vive en
 * src/styles/reservas.css.
 */
import { useState } from 'react';
import '../styles/reservas.css';

function CancelModal({ reservation, onConfirm, onClose }) {
  return (
    <div className="cancelar-modal">
      <div className="cancelar-modal__tarjeta">
        <div className="cancelar-modal__icono">🗑️</div>
        <h3 className="cancelar-modal__titulo">¿Cancelar reserva?</h3>
        <p className="cancelar-modal__bloque">
          Bloque de las <strong className="cancelar-modal__hora">{reservation.hour}</strong>
        </p>
        <p className="cancelar-modal__nota">
          El cupo será liberado <strong>inmediatamente</strong> y otro estudiante
          podrá ocuparlo.
        </p>
        <div className="cancelar-modal__acciones">
          <button className="cancelar-modal__boton cancelar-modal__boton--mantener" onClick={onClose}>
            Mantener
          </button>
          <button className="cancelar-modal__boton cancelar-modal__boton--confirmar" onClick={onConfirm}>
            Sí, cancelar
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MyReservations({ reservations, reservaFecha, onCancel, onNavigate }) {
  const [cancelTarget, setCancelTarget] = useState(null);

  const handleConfirmCancel = () => {
    onCancel(cancelTarget.id);
    setCancelTarget(null);
  };

  return (
    <div className="reservas">
      <h2 className="reservas__titulo">Mis reservas</h2>
      <p className="reservas__subtitulo">
        {/* Se deja explícito para qué día es la reserva */}
        Tu reserva de mañana
        {reservaFecha?.label && (
          <strong className="reservas__fecha"> · {reservaFecha.label}</strong>
        )}
      </p>

      {reservations.length === 0 ? (
        <div className="reservas__vacio">
          <div className="reservas__vacio-icono">📅</div>
          <h3 className="reservas__vacio-titulo">Sin reservas activas</h3>
          <p className="reservas__vacio-texto">
            No tienes ninguna reserva en este momento. ¡Asegura tu cupo ahora!
          </p>
          <button className="reservas__vacio-boton" onClick={() => onNavigate('dashboard')}>
            Ir a reservar →
          </button>
        </div>
      ) : (
        <div className="reservas__lista">
          <div className="reservas__recordatorio">
            <span className="reservas__recordatorio-icono">⚠️</span>
            <p className="reservas__recordatorio-texto">
              Recuerda: si no puedes asistir, <strong>cancela tu reserva</strong> para que
              otro compañero pueda usar ese cupo. Cancelar no te penaliza; lo que penaliza
              tu cuenta es <strong>no presentarte</strong> habiendo reservado.
            </p>
          </div>

          {reservations.map(res => (
            <div key={res.id} className="reserva">
              <div className="reserva__datos">
                <div className="reserva__icono">⏰</div>
                <div>
                  <p className="reserva__hora">{res.hour}</p>
                  <p className="reserva__fecha">{res.date}</p>
                  <div className="reserva__marcas">
                    <span className="reserva__marca reserva__marca--activa">● Activa</span>
                    <span className="reserva__marca reserva__marca--manana">📅 Para mañana</span>
                  </div>
                </div>
              </div>

              <button className="reserva__cancelar" onClick={() => setCancelTarget(res)}>
                Cancelar
              </button>
            </div>
          ))}
        </div>
      )}

      {cancelTarget && (
        <CancelModal
          reservation={cancelTarget}
          onConfirm={handleConfirmCancel}
          onClose={() => setCancelTarget(null)}
        />
      )}
    </div>
  );
}
