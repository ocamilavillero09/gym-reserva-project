/*
 * TABLERO DE RESERVA DEL ESTUDIANTE
 *
 * Solo estructura y comportamiento. La presentación vive en
 * src/styles/dashboard.css.
 */
import { useState } from 'react';
import '../styles/dashboard.css';

/** Devuelve el estado de ocupación de un bloque: libre, pocos o lleno. */
const nivelDeOcupacion = (slot) => {
  if (slot.available === 0) return 'lleno';
  if (slot.available <= 4)  return 'pocos';
  return 'libre';
};

const ROTULO_ESTADO = { lleno: 'Sin cupos', pocos: 'Casi lleno', libre: 'Disponible' };

function SlotCard({ slot, isReserved, yaReservoElDia, onReserve }) {
  const nivel = nivelDeOcupacion(slot);
  const isFull = nivel === 'lleno';
  const pct = Math.round((slot.available / slot.total) * 100);
  // Una sola reserva por día: si ya reservó otro bloque, este se bloquea.
  const bloqueadoPorLimite = yaReservoElDia && !isReserved;
  const deshabilitado = isFull || isReserved || bloqueadoPorLimite;

  const clases = ['bloque'];
  if (isReserved) clases.push('bloque--reservado');
  if (bloqueadoPorLimite) clases.push('bloque--limitado');
  if (deshabilitado) clases.push('bloque--deshabilitado');

  return (
    <div className={clases.join(' ')}>
      {isReserved && <div className="bloque__insignia">✓ Reservado</div>}

      <p className="bloque__rotulo">Bloque</p>
      <div className="bloque__hora">{slot.hour}</div>

      <div className="bloque__barra">
        <div
          className={`bloque__barra-relleno bloque__barra-relleno--${nivel}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="bloque__cifras">
        <span className="bloque__cupos">
          <strong>{slot.available}</strong> / {slot.total} cupos
        </span>
        <span className={`bloque__estado bloque__estado--${nivel}`}>
          ● {ROTULO_ESTADO[nivel]}
        </span>
      </div>

      <button
        className="bloque__accion"
        onClick={() => !deshabilitado && onReserve(slot)}
        disabled={deshabilitado}
      >
        {isReserved ? '✓ Ya reservado'
          : bloqueadoPorLimite ? 'Ya reservaste este día'
          : isFull ? 'Sin cupos'
          : 'Reservar cupo'}
      </button>
    </div>
  );
}

function ReserveModal({ slot, fechaLabel, onConfirm, onClose }) {
  return (
    <div className="confirmar">
      <div className="confirmar__tarjeta">
        <div className="confirmar__cabecera">
          <div className="confirmar__icono">📋</div>
          <h3 className="confirmar__titulo">Confirmar reserva</h3>
          <p className="confirmar__bloque">
            Bloque de las <strong className="confirmar__hora">{slot.hour}</strong>
          </p>
        </div>

        {/* La fecha efectiva de la reserva, siempre a la vista */}
        <div className="confirmar__fecha">
          <p className="confirmar__fecha-rotulo">Reserva para mañana</p>
          <p className="confirmar__fecha-valor">{fechaLabel || 'el día siguiente'}</p>
        </div>

        <div className="confirmar__politica">
          <p className="confirmar__politica-titulo">⚠️ Política de asistencia</p>
          <p className="confirmar__politica-texto">
            Solo puedes tener <strong>una reserva por día</strong>. Si no puedes asistir,
            <strong> cancela tu reserva</strong>: cancelar a tiempo devuelve el cupo y
            no te penaliza. Lo que sí penaliza tu cuenta es <strong>no presentarte</strong>
            habiendo reservado.
          </p>
        </div>

        <div className="confirmar__acciones">
          <button className="confirmar__boton confirmar__boton--cancelar" onClick={onClose}>
            Cancelar
          </button>
          <button className="confirmar__boton confirmar__boton--aceptar" onClick={onConfirm}>
            Confirmar ✓
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard({ slots, user, reservaFecha, reservations, onReserve }) {
  const [pendingSlot, setPendingSlot] = useState(null);

  const hoy = new Date().toLocaleDateString('es-CO', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  const totalAvailable = slots.reduce((sum, s) => sum + s.available, 0);
  // Con una reserva activa para el día siguiente ya no puede reservar más.
  const yaReservoElDia = reservations.length > 0;

  const handleConfirm = () => {
    onReserve(pendingSlot);
    setPendingSlot(null);
  };

  return (
    <div className="tablero">
      <div className="tablero__saludo">
        <h2 className="tablero__titulo">Hola, {user?.name?.split(' ')[0]} 👋</h2>
        <p className="tablero__fecha-hoy">Hoy es {hoy}</p>
      </div>

      {/* La reserva es para el DÍA SIGUIENTE: la fecha se anuncia siempre */}
      <div className="tablero__franja">
        <span className="tablero__franja-icono">📅</span>
        <div>
          <p className="tablero__franja-rotulo">Estás reservando para mañana</p>
          <p className="tablero__franja-fecha">
            {reservaFecha?.label || 'Cargando fecha...'}
          </p>
          <p className="tablero__franja-nota">
            Los cupos del gimnasio se reservan con un día de anticipación, y solo puedes tomar
            <strong> un bloque por día</strong>.
          </p>
        </div>
      </div>

      <div className="tablero__cifras">
        <StatCard icon="✅" label="Cupos disponibles" value={totalAvailable} />
        <StatCard icon="📌" label="Mi reserva de mañana" value={`${reservations.length}/1`} />
        {/* Las inasistencias son las que penalizan; las cancelaciones no. */}
        <StatCard
          icon="⚠️"
          label={`Inasistencias (límite ${user?.no_show_limite ?? 5})`}
          value={user?.no_show_count ?? 0}
          highlight={(user?.inasistencias_restantes ?? 99) <= 2}
        />
      </div>

      <div className="tablero__encabezado">
        <h3 className="tablero__seccion">Disponibilidad en tiempo real</h3>
        <span className="tablero__en-vivo">🔴 En vivo</span>
      </div>

      <div className="tablero__bloques">
        {slots.map(slot => (
          <SlotCard
            key={slot.id}
            slot={slot}
            isReserved={reservations.some(r => r.slotId === slot.id)}
            yaReservoElDia={yaReservoElDia}
            onReserve={setPendingSlot}
          />
        ))}
      </div>

      {pendingSlot && (
        <ReserveModal
          slot={pendingSlot}
          fechaLabel={reservaFecha?.label}
          onConfirm={handleConfirm}
          onClose={() => setPendingSlot(null)}
        />
      )}
    </div>
  );
}

function StatCard({ icon, label, value, highlight }) {
  return (
    <div className={`cifra${highlight ? ' cifra--alerta' : ''}`}>
      <div className="cifra__icono">{icon}</div>
      <div>
        <p className="cifra__valor">{value}</p>
        <p className="cifra__rotulo">{label}</p>
      </div>
    </div>
  );
}
