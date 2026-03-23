import { useState } from 'react';

const RED = '#CC0000';

function SlotCard({ slot, isReserved, onReserve }) {
  const isFull    = slot.available === 0;
  const isAlmostFull = slot.available > 0 && slot.available <= 4;
  const pct       = Math.round((slot.available / slot.total) * 100);
  const barColor  = isFull ? '#dc2626' : isAlmostFull ? '#d97706' : '#16a34a';
  const statusLabel = isFull ? 'Sin cupos' : isAlmostFull ? 'Casi lleno' : 'Disponible';

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
        cursor: isFull || isReserved ? 'default' : 'pointer',
      }}
      onMouseEnter={e => { if (!isFull && !isReserved) e.currentTarget.style.transform = 'translateY(-5px)'; }}
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
      <button
        onClick={() => !isFull && !isReserved && onReserve(slot)}
        disabled={isFull || isReserved}
        style={{
          width: '100%', padding: '13px 0', border: 'none', borderRadius: 12,
          cursor: isFull || isReserved ? 'not-allowed' : 'pointer',
          backgroundColor: isReserved ? '#F5F5F5' : isFull ? '#EFEFEF' : RED,
          color: isReserved ? '#999' : isFull ? '#BBB' : 'white',
          fontWeight: 700, fontSize: 14,
          boxShadow: !isFull && !isReserved ? '0 4px 14px rgba(204,0,0,0.3)' : 'none',
        }}
      >
        {isReserved ? '✓ Ya reservado' : isFull ? 'Sin cupos disponibles' : 'Reservar cupo'}
      </button>
    </div>
  );
}

function ReserveModal({ slot, onConfirm, onClose }) {
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

        {/* Aviso RF08 */}
        <div style={{
          backgroundColor: '#FFF8E6', border: '1.5px solid #FFC107',
          borderRadius: 14, padding: '16px 18px', marginBottom: 26,
        }}>
          <p style={{ fontWeight: 700, color: '#92400e', fontSize: 14, marginBottom: 6 }}>
            ⚠️ Política de asistencia
          </p>
          <p style={{ color: '#78350f', fontSize: 13, lineHeight: 1.7, margin: 0 }}>
            Si realizas esta reserva y <strong>no puedes asistir</strong>, tienes la
            <strong> obligación de cancelarla</strong> con anticipación para liberar el cupo
            y permitir el ingreso de otros compañeros.
          </p>
        </div>

        <p style={{ fontSize: 13, color: '#888', textAlign: 'center', marginBottom: 24 }}>
          Al confirmar, recibirás un correo de confirmación automático.
        </p>

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

export default function Dashboard({ slots, user, reservations, onReserve }) {
  const [pendingSlot, setPendingSlot] = useState(null);

  const today = new Date().toLocaleDateString('es-CO', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  const totalAvailable = slots.reduce((sum, s) => sum + s.available, 0);

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
        <p style={{ color: '#999', fontSize: 15, textTransform: 'capitalize' }}>{today}</p>
      </div>

      {/* Estadísticas rápidas */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 28 }}>
        <StatCard icon="🕐" label="Horarios hoy" value="6" />
        <StatCard icon="✅" label="Cupos disponibles" value={totalAvailable} />
        <StatCard icon="📌" label="Mis reservas" value={reservations.length} />
      </div>

      {/* Banner de advertencia RF08 */}
      <div style={{
        backgroundColor: '#FFFBEB', border: '1.5px solid #FCD34D',
        borderRadius: 16, padding: '16px 22px', marginBottom: 32,
        display: 'flex', gap: 14, alignItems: 'flex-start',
      }}>
        <span style={{ fontSize: 22, flexShrink: 0, marginTop: 1 }}>⚠️</span>
        <div>
          <p style={{ fontWeight: 700, color: '#92400e', fontSize: 15, marginBottom: 4 }}>
            Política de asistencia — léela antes de reservar
          </p>
          <p style={{ color: '#78350f', fontSize: 13, lineHeight: 1.7, margin: 0 }}>
            Si realizas una reserva y no puedes asistir, <strong>tienes la obligación de cancelarla</strong> para
            liberar el cupo y permitir el ingreso de otros compañeros. El incumplimiento repetido puede
            generar restricciones en el uso del sistema.
          </p>
        </div>
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
            onReserve={setPendingSlot}
          />
        ))}
      </div>

      {pendingSlot && (
        <ReserveModal
          slot={pendingSlot}
          onConfirm={handleConfirm}
          onClose={() => setPendingSlot(null)}
        />
      )}
    </div>
  );
}

function StatCard({ icon, label, value }) {
  return (
    <div style={{
      backgroundColor: 'white', borderRadius: 16, padding: '20px 24px',
      boxShadow: '0 2px 12px rgba(0,0,0,0.07)',
      display: 'flex', alignItems: 'center', gap: 16,
    }}>
      <div style={{ fontSize: 32 }}>{icon}</div>
      <div>
        <p style={{ fontSize: 26, fontWeight: 900, color: '#1A1A1A', lineHeight: 1 }}>{value}</p>
        <p style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{label}</p>
      </div>
    </div>
  );
}
