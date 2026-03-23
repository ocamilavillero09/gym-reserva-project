import { useState } from 'react';
import Login from './components/Login';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import MyReservations from './components/MyReservations';
import { slotsApi, reservationsApi } from './services/api';

function Toast({ message, type, onClose }) {
  const styles = {
    success: { bg: '#dcfce7', border: '#16a34a', text: '#15803d', icon: '✓' },
    warning: { bg: '#fef9c3', border: '#ca8a04', text: '#92400e', icon: '⚠' },
    info:    { bg: '#dbeafe', border: '#2563eb', text: '#1d4ed8', icon: 'ℹ' },
    error:   { bg: '#fee2e2', border: '#dc2626', text: '#991b1b', icon: '✕' },
  };
  const c = styles[type] || styles.success;
  return (
    <div style={{
      position: 'fixed', top: 20, right: 20, zIndex: 9999,
      backgroundColor: c.bg, border: `1px solid ${c.border}`,
      borderRadius: 14, padding: '16px 20px', maxWidth: 400,
      boxShadow: '0 4px 24px rgba(0,0,0,0.15)',
      display: 'flex', alignItems: 'flex-start', gap: 12,
      animation: 'toastIn 0.3s ease',
    }}>
      <span style={{ fontSize: 18, color: c.border, flexShrink: 0, marginTop: 1 }}>{c.icon}</span>
      <p style={{ margin: 0, color: c.text, fontSize: 14, lineHeight: 1.6, flex: 1 }}>{message}</p>
      <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: c.text, fontSize: 20, lineHeight: 1, flexShrink: 0 }}>×</button>
    </div>
  );
}

export default function App() {
  const [view, setView]               = useState('login');
  const [user, setUser]               = useState(null);
  const [slots, setSlots]             = useState([]);
  const [reservations, setReservations] = useState([]);
  const [toast, setToast]             = useState(null);
  const [loading, setLoading]         = useState(false);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const refreshData = async (email) => {
    const [slotsData, resData] = await Promise.all([
      slotsApi.getAll(),
      reservationsApi.getByEmail(email),
    ]);
    setSlots(slotsData);
    setReservations(resData);
  };

  const handleLogin = async (userData) => {
    setLoading(true);
    try {
      await refreshData(userData.email);
      setUser(userData);
      setView('dashboard');
    } catch {
      showToast('No se pudo conectar con el servidor.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setUser(null);
    setView('login');
    setReservations([]);
    setSlots([]);
  };

  const handleReserve = async (slot) => {
    try {
      await reservationsApi.create({ email: user.email, slotId: slot.id });
      await refreshData(user.email);
      showToast(`¡Reserva confirmada para las ${slot.hour}! Correo enviado a ${user.email}.`);
    } catch (err) {
      showToast(err.message, 'warning');
    }
  };

  const handleCancel = async (id) => {
    try {
      await reservationsApi.cancel(id);
      await refreshData(user.email);
      showToast('Reserva cancelada. El cupo fue liberado inmediatamente.', 'info');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#F4F4F6', fontFamily: "'Segoe UI', Arial, sans-serif" }}>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        @keyframes toastIn { from { transform: translateX(110%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes fadeUp  { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes scaleIn { from { opacity: 0; transform: scale(0.92); } to { opacity: 1; transform: scale(1); } }
        button { transition: filter 0.15s, transform 0.1s; }
        button:not(:disabled):hover  { filter: brightness(0.93); }
        button:not(:disabled):active { transform: scale(0.97); }
        input:focus { border-color: #CC0000 !important; box-shadow: 0 0 0 3px rgba(204,0,0,0.1); outline: none; }
      `}</style>

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {loading && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(255,255,255,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 8888 }}>
          <div style={{ fontSize: 40 }}>⏳</div>
        </div>
      )}

      {view === 'login' ? (
        <Login onLogin={handleLogin} />
      ) : (
        <>
          <Navbar
            user={user}
            view={view}
            reservationCount={reservations.length}
            onNavigate={setView}
            onLogout={handleLogout}
          />
          {view === 'dashboard' && (
            <Dashboard
              slots={slots}
              user={user}
              reservations={reservations}
              onReserve={handleReserve}
            />
          )}
          {view === 'my-reservations' && (
            <MyReservations
              reservations={reservations}
              onCancel={handleCancel}
              onNavigate={setView}
            />
          )}
        </>
      )}
    </div>
  );
}
