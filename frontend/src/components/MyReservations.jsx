import { useState } from 'react';

const RED = '#CC0000';

function CancelModal({ reservation, onConfirm, onClose }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 999, padding: 24,
    }}>
      <div style={{
        backgroundColor: 'white', borderRadius: 22, padding: '36px 32px',
        maxWidth: 400, width: '100%', animation: 'scaleIn 0.25s ease',
        boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 52, marginBottom: 16 }}>🗑️</div>
        <h3 style={{ fontSize: 22, fontWeight: 900, color: '#1A1A1A', marginBottom: 8 }}>
          ¿Cancelar reserva?
        </h3>
        <p style={{ color: '#666', fontSize: 15, marginBottom: 8 }}>
          Bloque de las <strong style={{ color: RED }}>{reservation.hour}</strong>
        </p>
        <p style={{ color: '#999', fontSize: 13, lineHeight: 1.7, marginBottom: 28 }}>
          El cupo será liberado <strong>inmediatamente</strong> y otro estudiante
          podrá ocuparlo.
        </p>
        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={onClose} style={{
            flex: 1, padding: 14, border: '1.5px solid #E5E7EB', borderRadius: 12,
            cursor: 'pointer', backgroundColor: 'white', color: '#555',
            fontWeight: 600, fontSize: 14,
          }}>
            Mantener
          </button>
          <button onClick={onConfirm} style={{
            flex: 1, padding: 14, border: 'none', borderRadius: 12,
            cursor: 'pointer', backgroundColor: RED, color: 'white',
            fontWeight: 800, fontSize: 14,
            boxShadow: '0 4px 16px rgba(204,0,0,0.35)',
          }}>
            Sí, cancelar
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MyReservations({ reservations, onCancel, onNavigate }) {
  const [cancelTarget, setCancelTarget] = useState(null);

  const handleConfirmCancel = () => {
    onCancel(cancelTarget.id);
    setCancelTarget(null);
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '36px 24px', animation: 'fadeUp 0.4s ease' }}>
      <h2 style={{ fontSize: 30, fontWeight: 900, color: '#1A1A1A', marginBottom: 6, letterSpacing: -0.5 }}>
        Mis reservas
      </h2>
      <p style={{ color: '#999', fontSize: 15, marginBottom: 32 }}>
        Gestiona tus reservas activas
      </p>

      {reservations.length === 0 ? (
        /* Estado vacío */
        <div style={{
          textAlign: 'center', padding: '64px 40px',
          backgroundColor: 'white', borderRadius: 22,
          boxShadow: '0 2px 14px rgba(0,0,0,0.07)',
        }}>
          <div style={{ fontSize: 72, marginBottom: 20 }}>📅</div>
          <h3 style={{ color: '#1A1A1A', fontSize: 22, fontWeight: 800, marginBottom: 10 }}>
            Sin reservas activas
          </h3>
          <p style={{ color: '#999', fontSize: 14, marginBottom: 28, maxWidth: 280, margin: '0 auto 28px' }}>
            No tienes ninguna reserva en este momento. ¡Asegura tu cupo ahora!
          </p>
          <button onClick={() => onNavigate('dashboard')} style={{
            padding: '13px 32px', backgroundColor: RED, color: 'white',
            border: 'none', borderRadius: 12, fontWeight: 800, fontSize: 14,
            cursor: 'pointer', boxShadow: '0 4px 16px rgba(204,0,0,0.35)',
          }}>
            Ir a reservar →
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Banner recordatorio RF08 */}
          <div style={{
            backgroundColor: '#FFFBEB', border: '1.5px solid #FCD34D',
            borderRadius: 14, padding: '14px 18px',
            display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 8,
          }}>
            <span style={{ fontSize: 18, flexShrink: 0 }}>⚠️</span>
            <p style={{ color: '#78350f', fontSize: 13, lineHeight: 1.6, margin: 0 }}>
              Recuerda: si no puedes asistir, <strong>debes cancelar tu reserva</strong> para
              que otro compañero pueda usar ese cupo.
            </p>
          </div>

          {reservations.map(res => (
            <div key={res.id} style={{
              backgroundColor: 'white', borderRadius: 18, padding: '22px 26px',
              boxShadow: '0 2px 14px rgba(0,0,0,0.07)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
                <div style={{
                  width: 60, height: 60, borderRadius: 16,
                  backgroundColor: '#FEE2E2',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 26, flexShrink: 0,
                }}>
                  ⏰
                </div>
                <div>
                  <p style={{ fontSize: 26, fontWeight: 900, color: '#1A1A1A', lineHeight: 1, marginBottom: 4 }}>
                    {res.hour}
                  </p>
                  <p style={{ fontSize: 13, color: '#999', marginBottom: 6, textTransform: 'capitalize' }}>
                    {res.date}
                  </p>
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: 5,
                    backgroundColor: '#dcfce7', color: '#15803d',
                    fontSize: 11, fontWeight: 800, padding: '3px 10px', borderRadius: 24,
                    letterSpacing: 0.2,
                  }}>
                    ● Activa
                  </span>
                </div>
              </div>

              <button onClick={() => setCancelTarget(res)} style={{
                padding: '10px 22px',
                border: '1.5px solid #fca5a5',
                borderRadius: 12, cursor: 'pointer',
                backgroundColor: 'white', color: RED,
                fontWeight: 700, fontSize: 13, whiteSpace: 'nowrap',
                flexShrink: 0,
              }}>
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
