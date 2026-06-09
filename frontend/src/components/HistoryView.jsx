import { useEffect, useState } from 'react';
import { reservationsApi, ratingsApi } from '../services/api';

const RED = '#CC0000';

const BADGE = {
  COMPLETADA: { bg: '#dcfce7', fg: '#15803d', label: 'Asistió' },
  CANCELADA:  { bg: '#e5e7eb', fg: '#4b5563', label: 'Cancelada' },
  NO_SHOW:    { bg: '#fee2e2', fg: '#991b1b', label: 'No asistió' },
};

// RF11 — Historial de entrenamiento + RF15 — calificación del servicio.
export default function HistoryView({ user, showToast }) {
  const [history, setHistory] = useState([]);
  const [stars, setStars] = useState(5);
  const [comment, setComment] = useState('');

  useEffect(() => {
    reservationsApi.history(user.email).then(setHistory).catch(() => setHistory([]));
  }, [user.email]);

  const sendRating = async (e) => {
    e.preventDefault();
    try {
      await ratingsApi.create({ email: user.email, stars: Number(stars), comment });
      showToast('¡Gracias por tu calificación!', 'success');
      setComment('');
    } catch (err) { showToast(err.message, 'error'); }
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '36px 24px', animation: 'fadeUp 0.4s ease' }}>
      <h2 style={{ fontSize: 30, fontWeight: 900, marginBottom: 4 }}>Mi historial</h2>
      <p style={{ color: '#999', fontSize: 15, marginBottom: 28 }}>Tus entrenamientos pasados</p>

      {history.length === 0 ? (
        <div style={{ background: 'white', borderRadius: 18, padding: 40, textAlign: 'center', boxShadow: '0 2px 14px rgba(0,0,0,0.07)' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📖</div>
          <p style={{ color: '#999' }}>Aún no tienes historial.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 32 }}>
          {history.map((h) => {
            const b = BADGE[h.estado] || { bg: '#eee', fg: '#555', label: h.estado };
            return (
              <div key={h.id} style={{ background: 'white', borderRadius: 14, padding: '16px 20px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 700 }}>{h.hour} <span style={{ color: '#999', fontWeight: 400, fontSize: 13 }}>· {h.date}</span></span>
                <span style={{ background: b.bg, color: b.fg, fontSize: 12, fontWeight: 800, padding: '4px 12px', borderRadius: 20 }}>{b.label}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* RF15 — Calificación */}
      <div style={{ background: 'white', borderRadius: 18, padding: 26, boxShadow: '0 2px 14px rgba(0,0,0,0.07)' }}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>⭐ Califica el servicio</h3>
        <form onSubmit={sendRating} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            {[1, 2, 3, 4, 5].map((n) => (
              <button type="button" key={n} onClick={() => setStars(n)} aria-label={`${n} estrellas`} style={{
                fontSize: 28, border: 'none', background: 'none', cursor: 'pointer',
                color: n <= stars ? '#f59e0b' : '#d1d5db',
              }}>★</button>
            ))}
          </div>
          <textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Comentario (opcional)"
                    rows={3} style={{ padding: 12, border: '1.5px solid #E5E7EB', borderRadius: 10, fontSize: 14, fontFamily: 'inherit' }} />
          <button type="submit" style={{ padding: 13, border: 'none', borderRadius: 12, background: RED, color: 'white', fontWeight: 800, cursor: 'pointer' }}>
            Enviar calificación
          </button>
        </form>
      </div>
    </div>
  );
}
