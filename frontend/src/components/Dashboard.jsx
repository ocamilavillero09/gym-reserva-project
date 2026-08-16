import { useState } from 'react';

const RED = '#CC0000';

function SlotCard({ slot, isReserved, yaReservoElDia, onReserve, onJoinWaitlist }) {
  const isFull       = slot.available === 0;
  const isAlmostFull = slot.available > 0 && slot.available <= 4;
  const pct          = Math.round((slot.available / slot.total) * 100);
  const barColor     = isFull ? '#dc2626' : isAlmostFull ? '#d97706' : '#16a34a';
  const statusLabel  = isFull ? 'Sin cupos' : isAlmostFull ? 'Casi lleno' : 'Disponible';
  // RN05 — una sola reserva por día: si ya reservó otro bloque, este se bloquea.
  const bloqueadoPorLimite = yaReservoElDia && !isReserved;
  const deshabilitado = isFull || isReserved || bloqueadoPorLimite;

  return (
    <div
      style={{
        backgroundColor: 'white',
        borderRadius: 18,
        padding: 26,
        boxShadow: isReserved
          ? `0 0 0 2.5px ${RED}, 0 6px 24px rgba(204,0,0,0.14)`
          : '0 2px 14px rgba(0,0,0,0.07)',
        transition: 'transform 0.2s, box-shadow 0.2s',
        position: 'relative',
        overflow: 'hidden',
        opacity: bloqueadoPorLimite ? 0.65 : 1,
        cursor: deshabilitado ? 'default' : 'pointer',
      }}
      onMouseEnter={e => { if (!deshabilitado) e.currentTarget.style.transform = 'translateY(-5px)'; }}
      onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; }}
    >
      {/* Badge reservado */}
      {isReserved && (
        <div style={{
          position: 'absolute', top: 14, right: 14,
          backgroundColor: RED, color: 'white',
          fontSize: 11, fontWeight: 800, padding: '4px 12px', borderRadius: 24,
          letterSpacing: 0.3,
        }}>
          ✓ Reservado
        </div>
      )}

      {/* Hora */}
      <p style={{ fontSize: 13, color: '#AAA', fontWeight: 600, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>
        Bloque
      </p>
      <div style={{ fontSize: 42, fontWeight: 900, color: '#1A1A1A', lineHeight: 1, marginBottom: 16 }}>
        {slot.hour}
      </div>

      {/* Barra de disponibilidad */}
      <div style={{ height: 7, backgroundColor: '#F0F0F0', borderRadius: 6, marginBottom: 10, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`,
          backgroundColor: barColor,
          borderRadius: 6,
          transition: 'width 0.6s ease',
        }} />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 22 }}>
        <span style={{ fontSize: 13, color: '#666' }}>
          <strong style={{ color: '#1A1A1A' }}>{slot.available}</strong> / {slot.total} cupos
        </span>
        <span style={{ fontSize: 12, fontWeight: 700, color: barColor }}>
          ● {statusLabel}
        </span>
      </div>

      {/* Botón */}
      {/* RF12 — Si el bloque está lleno y no lo tienes reservado, ofrece lista de espera */}
      {isFull && !isReserved && !bloqueadoPorLimite ? (
        <button
          onClick={() => onJoinWaitlist(slot)}
          style={{
            width: '100%', padding: '13px 0', border: `1.5px solid ${RED}`, borderRadius: 12,
            cursor: 'pointer', backgroundColor: 'white', color: RED, fontWeight: 700, fontSize: 14,
          }}
        >
          ⏳ Unirme a la lista de espera
        </button>
      ) : (
        <button
          onClick={() => !deshabilitado && onReserve(slot)}
          disabled={deshabilitado}
          style={{
            width: '100%', padding: '13px 0', border: 'none', borderRadius: 12,
            cursor: deshabilitado ? 'not-allowed' : 'pointer',
            backgroundColor: deshabilitado ? '#F5F5F5' : RED,
            color: deshabilitado ? '#999' : 'white',
            fontWeight: 700, fontSize: 14,
            boxShadow: !deshabilitado ? '0 4px 14px rgba(204,0,0,0.3)' : 'none',
          }}
        >
          {isReserved ? '✓ Ya reservado'
            : bloqueadoPorLimite ? 'Ya reservaste este día'
            : isFull ? 'Sin cupos'
            : 'Reservar cupo'}
        </button>
      )}
    </div>
  );
}

function ReserveModal({ slot, fechaLabel, onConfirm, onClose }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 999, padding: 24,
    }}>
      <div style={{
        backgroundColor: 'white', borderRadius: 22, padding: '36px 32px',
        maxWidth: 440, width: '100%', animation: 'scaleIn 0.25s ease',
        boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ fontSize: 52, marginBottom: 12 }}>📋</div>
          <h3 style={{ fontSize: 22, fontWeight: 900, color: '#1A1A1A', marginBottom: 8 }}>
            Confirmar reserva
          </h3>
          <p style={{ color: '#666', fontSize: 15 }}>
            Bloque de las <strong style={{ color: RED }}>{slot.hour}</strong>
          </p>
        </div>

        {/* RN03 — la fecha efectiva de la reserva, siempre a la vista */}
        <div style={{
          backgroundColor: '#F4F4F6', borderRadius: 14, padding: '14px 18px',
          marginBottom: 18, textAlign: 'center',
        }}>
          <p style={{ fontSize: 12, color: '#888', fontWeight: 700, letterSpacing: 0.6, textTransform: 'uppercase', marginBottom: 4 }}>
            Reserva para mañana
          </p>
          <p style={{ fontSize: 15, fontWeight: 800, color: '#1A1A1A', textTransform: 'capitalize', margin: 0 }}>
            {fechaLabel || 'el día siguiente'}
          </p>
        </div>

        {/* Aviso RF08 / RN05 */}
        <div style={{
          backgroundColor: '#FFF8E6', border: '1.5px solid #FFC107',
          borderRadius: 14, padding: '16px 18px', marginBottom: 26,
        }}>
          <p style={{ fontWeight: 700, color: '#92400e', fontSize: 14, marginBottom: 6 }}>
            ⚠️ Política de asistencia
          </p>
          <p style={{ color: '#78350f', fontSize: 13, lineHeight: 1.7, margin: 0 }}>
            Solo puedes tener <strong>una reserva por día</strong>. Si no puedes asistir,
            tienes la <strong>obligación de cancelarla</strong> con anticipación; ten en
            cuenta que las cancelaciones se acumulan y pueden penalizar tu cuenta.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={onClose} style={{
            flex: 1, padding: 14, border: '1.5px solid #E5E7EB', borderRadius: 12,
            cursor: 'pointer', backgroundColor: 'white', color: '#555',
            fontWeight: 600, fontSize: 14,
          }}>
            Cancelar
          </button>
          <button onClick={onConfirm} style={{
            flex: 1, padding: 14, border: 'none', borderRadius: 12,
            cursor: 'pointer', backgroundColor: RED, color: 'white',
            fontWeight: 800, fontSize: 14,
            boxShadow: '0 4px 16px rgba(204,0,0,0.35)',
          }}>
            Confirmar ✓
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard({ slots, user, reservaFecha, reservations, onReserve, onJoinWaitlist }) {
  const [pendingSlot, setPendingSlot] = useState(null);

  const hoy = new Date().toLocaleDateString('es-CO', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  const totalAvailable = slots.reduce((sum, s) => sum + s.available, 0);
  // RN05 — con una reserva activa para el día siguiente ya no puede reservar más.
  const yaReservoElDia = reservations.length > 0;

  const handleConfirm = () => {
    onReserve(pendingSlot);
    setPendingSlot(null);
  };

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '36px 24px', animation: 'fadeUp 0.4s ease' }}>

      {/* Saludo */}
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 30, fontWeight: 900, color: '#1A1A1A', marginBottom: 4, letterSpacing: -0.5 }}>
          Hola, {user?.name?.split(' ')[0]} 👋
        </h2>
        <p style={{ color: '#999', fontSize: 15, textTransform: 'capitalize' }}>Hoy es {hoy}</p>
      </div>

      {/* RN03 — Banner de la fecha de reserva: se reserva para el DÍA SIGUIENTE */}
      <div style={{
        background: `linear-gradient(120deg, ${RED} 0%, #990000 100%)`,
        borderRadius: 18, padding: '22px 26px', marginBottom: 24,
        display: 'flex', gap: 18, alignItems: 'center', color: 'white',
        boxShadow: '0 6px 24px rgba(204,0,0,0.25)',
      }}>
        <span style={{ fontSize: 38, flexShrink: 0 }}>📅</span>
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', opacity: 0.85, marginBottom: 4 }}>
            Estás reservando para mañana
          </p>
          <p style={{ fontSize: 22, fontWeight: 900, textTransform: 'capitalize', lineHeight: 1.2 }}>
            {reservaFecha?.label || 'Cargando fecha...'}
          </p>
          <p style={{ fontSize: 13, opacity: 0.9, marginTop: 6 }}>
            Los cupos del gimnasio se reservan con un día de anticipación, y solo puedes tomar
            <strong> un bloque por día</strong>.
          </p>
        </div>
      </div>

      {/* Estadísticas rápidas */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 28 }}>
        <StatCard icon="✅" label="Cupos disponibles" value={totalAvailable} />
        <StatCard icon="📌" label="Mi reserva de mañana" value={`${reservations.length}/1`} />
        <StatCard
          icon="🚫"
          label={`Cancelaciones (límite ${user?.cancelacion_limite ?? 5})`}
          value={user?.cancel_count ?? 0}
          highlight={(user?.cancelaciones_restantes ?? 99) <= 2}
        />
      </div>

      {/* Título de sección */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 style={{ fontSize: 20, fontWeight: 800, color: '#1A1A1A' }}>
          Disponibilidad en tiempo real
        </h3>
        <span style={{ fontSize: 12, color: RED, backgroundColor: '#fee2e2', padding: '6px 14px', borderRadius: 20, fontWeight: 700 }}>
          🔴 En vivo
        </span>
      </div>

      {/* Grid de slots */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(270px, 1fr))', gap: 20 }}>
        {slots.map(slot => (
          <SlotCard
            key={slot.id}
            slot={slot}
            isReserved={reservations.some(r => r.slotId === slot.id)}
            yaReservoElDia={yaReservoElDia}
            onReserve={setPendingSlot}
            onJoinWaitlist={onJoinWaitlist}
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
    <div style={{
      backgroundColor: 'white', borderRadius: 16, padding: '20px 24px',
      boxShadow: '0 2px 12px rgba(0,0,0,0.07)',
      border: highlight ? '1.5px solid #F59E0B' : '1.5px solid transparent',
      display: 'flex', alignItems: 'center', gap: 16,
    }}>
      <div style={{ fontSize: 32 }}>{icon}</div>
      <div>
        <p style={{ fontSize: 26, fontWeight: 900, color: highlight ? '#B45309' : '#1A1A1A', lineHeight: 1 }}>{value}</p>
        <p style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{label}</p>
      </div>
    </div>
  );
}
