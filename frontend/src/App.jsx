import { useCallback, useEffect, useState } from 'react';
import Login from './components/Login';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import MyReservations from './components/MyReservations';
import TrainerPanel from './components/TrainerPanel';
import AdminPanel from './components/AdminPanel';
import HistoryView from './components/HistoryView';
import ProfileView from './components/ProfileView';
import { authApi, slotsApi, reservationsApi, waitlistApi } from './services/api';

// Clave de la sesión guardada en el navegador: gracias a esto, recargar la
// página (F5) NO cierra la sesión.
const SESSION_KEY = 'gym_udem_session';

const readStoredSession = () => {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY)) || null;
  } catch {
    return null;
  }
};

const isStaff = (u) => u?.role === 'ENTRENADOR' || u?.role === 'ADMIN';
const defaultView = (u) => (isStaff(u) ? 'panel' : 'dashboard');

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

/**
 * RN10 — Alerta permanente dentro de la app: avisa al estudiante que está a
 * pocas cancelaciones de ser penalizado. El texto lo calcula el backend.
 */
function PenaltyAlert({ user }) {
  if (!user?.alerta) return null;
  const bloqueado = user.estado === 'PENALIZADO' || user.cancelaciones_restantes === 0;
  return (
    <div style={{
      backgroundColor: bloqueado ? '#FEE2E2' : '#FFF7ED',
      borderBottom: `2px solid ${bloqueado ? '#DC2626' : '#F59E0B'}`,
      padding: '14px 24px',
    }}>
      <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <span style={{ fontSize: 20, flexShrink: 0 }}>{bloqueado ? '🚫' : '⚠️'}</span>
        <div>
          <p style={{ fontWeight: 800, fontSize: 14, color: bloqueado ? '#991B1B' : '#92400E', marginBottom: 2 }}>
            {bloqueado ? 'Cuenta penalizada' : 'Aviso de cancelaciones'}
          </p>
          <p style={{ fontSize: 13, color: bloqueado ? '#991B1B' : '#78350F', lineHeight: 1.6, margin: 0 }}>
            {user.alerta}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const stored = readStoredSession();
  const [view, setView]                 = useState(stored ? defaultView(stored) : 'login');
  const [user, setUser]                 = useState(stored);
  const [slots, setSlots]               = useState([]);
  const [reservaFecha, setReservaFecha] = useState(null);   // { fecha, label }
  const [reservations, setReservations] = useState([]);
  const [toast, setToast]               = useState(null);
  const [loading, setLoading]           = useState(false);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const saveSession = (u) => {
    setUser(u);
    if (u) localStorage.setItem(SESSION_KEY, JSON.stringify(u));
    else localStorage.removeItem(SESSION_KEY);
  };

  const refreshData = useCallback(async (email) => {
    const [slotsData, resData] = await Promise.all([
      slotsApi.getAll(),
      reservationsApi.getByEmail(email),
    ]);
    setSlots(slotsData.slots || []);
    setReservaFecha({ fecha: slotsData.fecha, label: slotsData.fecha_label });
    setReservations(resData);
  }, []);

  // Al montar (o al recargar la página) se rehidrata la sesión guardada: se
  // piden datos frescos al servidor y solo se cierra sesión si el usuario ya
  // no existe. Recargar deja de expulsar al usuario.
  useEffect(() => {
    const restored = readStoredSession();
    if (!restored?.email) return;
    let cancelado = false;
    (async () => {
      setLoading(true);
      try {
        const fresh = await authApi.session(restored.email);
        if (cancelado) return;
        saveSession(fresh);
        setView((v) => (v === 'login' ? defaultView(fresh) : v));
        await refreshData(fresh.email);
      } catch {
        if (!cancelado) {
          saveSession(null);
          setView('login');
        }
      } finally {
        if (!cancelado) setLoading(false);
      }
    })();
    return () => { cancelado = true; };
  }, [refreshData]);

  // Mantiene la sesión al día tras reservar/cancelar (contadores y alerta).
  const refreshSession = async (email) => {
    try {
      saveSession(await authApi.session(email));
    } catch { /* si falla, se conserva la sesión actual */ }
  };

  const handleLogin = async (userData) => {
    setLoading(true);
    try {
      await refreshData(userData.email);
      saveSession(userData);
      setView(defaultView(userData));
    } catch {
      showToast('No se pudo conectar con el servidor.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    saveSession(null);
    setView('login');
    setReservations([]);
    setSlots([]);
    setReservaFecha(null);
  };

  const handleReserve = async (slot) => {
    try {
      await reservationsApi.create({ email: user.email, slotId: slot.id });
      await refreshData(user.email);
      showToast(`¡Reserva confirmada para las ${slot.hour} del ${reservaFecha?.label ?? 'día siguiente'}!`);
    } catch (err) {
      showToast(err.message, 'warning');
    }
  };

  const handleJoinWaitlist = async (slot) => {
    try {
      const r = await waitlistApi.join(slot.id, user.email);
      showToast(`Estás en la lista de espera de las ${slot.hour} (posición ${r.posicion}).`, 'info');
    } catch (err) {
      showToast(err.message, 'warning');
    }
  };

  const handleCancel = async (id) => {
    try {
      const r = await reservationsApi.cancel(id);
      await refreshData(user.email);
      await refreshSession(user.email);
      // RN10 — tras cancelar se informa el contador y, si aplica, la alerta.
      if (r.penalizado) {
        showToast(`Reserva cancelada. Llegaste a ${r.cancel_count} cancelaciones: tu cuenta quedó PENALIZADA.`, 'error');
      } else if (r.alerta) {
        showToast(r.alerta, 'warning');
      } else {
        showToast(`Reserva cancelada. El cupo fue liberado. Llevas ${r.cancel_count} de ${r.cancelacion_limite} cancelaciones.`, 'info');
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const staff = isStaff(user);

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

      {!user ? (
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

          {/* RN10 — alerta de cancelaciones, siempre visible para el estudiante */}
          {!staff && <PenaltyAlert user={user} />}

          {/* Los profesores y administradores NO reservan: solo ven el aforo. */}
          {!staff && view === 'dashboard' && (
            <Dashboard
              slots={slots}
              user={user}
              reservaFecha={reservaFecha}
              reservations={reservations}
              onReserve={handleReserve}
              onJoinWaitlist={handleJoinWaitlist}
            />
          )}
          {!staff && view === 'my-reservations' && (
            <MyReservations
              reservations={reservations}
              reservaFecha={reservaFecha}
              onCancel={handleCancel}
              onNavigate={setView}
            />
          )}
          {!staff && view === 'history' && <HistoryView user={user} showToast={showToast} />}

          {view === 'profile' && <ProfileView user={user} showToast={showToast} />}

          {staff && view === 'panel' && (
            <TrainerPanel
              user={user}
              reservaFecha={reservaFecha}
              showToast={showToast}
              onChanged={() => refreshData(user.email)}
            />
          )}
          {user?.role === 'ADMIN' && view === 'admin' && (
            <AdminPanel user={user} showToast={showToast} />
          )}
        </>
      )}
    </div>
  );
}
