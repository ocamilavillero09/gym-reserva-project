/*
 * ARMAZÓN DE LA APLICACIÓN
 *
 * Estado de la sesión, navegación entre pantallas y llamadas al backend.
 * Aquí no hay estilos: la presentación vive en src/styles/app.css.
 */
import { useCallback, useEffect, useState } from 'react';
import Login from './components/Login';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import MyReservations from './components/MyReservations';
import TrainerPanel from './components/TrainerPanel';
import AdminPanel from './components/AdminPanel';
import HistoryView from './components/HistoryView';
import ProfileView from './components/ProfileView';
import { authApi, slotsApi, reservationsApi } from './services/api';
import './styles/app.css';

// La sesión se guarda en el almacenamiento DE LA PESTAÑA, no del navegador.
//
// Con localStorage todas las pestañas compartían una sola sesión: abrir una
// segunda cuenta pisaba la primera y, al recargar, las dos mostraban la misma
// persona —de ahí que a un administrador le apareciera la vista de estudiante—.
// sessionStorage es propio de cada pestaña, así que se pueden tener varias
// sesiones a la vez y recargar (F5) sigue sin cerrarlas.
const SESSION_KEY = 'gym_udem_session';

const readStoredSession = () => {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY)) || null;
  } catch {
    return null;
  }
};

const isStaff = (u) => u?.role === 'ENTRENADOR' || u?.role === 'ADMIN';
const defaultView = (u) => (isStaff(u) ? 'panel' : 'dashboard');

// Qué pantallas puede ver cada rol. Sirve de red de seguridad: si por lo que
// sea la vista guardada no corresponde al rol de quien entra, se vuelve a la
// pantalla propia de ese rol en lugar de mostrar algo que no le toca.
const VISTAS_POR_ROL = {
  ESTUDIANTE: ['dashboard', 'my-reservations', 'history', 'profile'],
  ENTRENADOR: ['panel', 'profile'],
  ADMIN:      ['panel', 'admin', 'profile'],
};

const vistaPermitida = (u, vista) => (VISTAS_POR_ROL[u?.role] || []).includes(vista);
const vistaParaRol = (u, vista) => (vistaPermitida(u, vista) ? vista : defaultView(u));

const TOAST_CLASE = { success: 'exito', warning: 'atencion', info: 'info', error: 'error' };
const TOAST_ICONO = { success: '\u2713', warning: '\u26A0', info: '\u2139', error: '\u2715' };

function Toast({ message, type, onClose }) {
  const variante = TOAST_CLASE[type] || 'exito';
  return (
    <div className={`toast toast--${variante}`}>
      <span className="toast__icono">{TOAST_ICONO[type] || TOAST_ICONO.success}</span>
      <p className="toast__texto">{message}</p>
      <button className="toast__cerrar" onClick={onClose}>×</button>
    </div>
  );
}

/**
 * Aviso permanente dentro de la app: avisa al estudiante que está a pocas
 * INASISTENCIAS de ser penalizado. El texto lo calcula el backend.
 *
 * Las cancelaciones no aparecen aquí: cancelar no penaliza.
 */
function PenaltyAlert({ user }) {
  const aviso = user?.alerta_inasistencias;
  if (!aviso) return null;
  const bloqueado = user.estado === 'PENALIZADO' || user.inasistencias_restantes === 0;
  return (
    <div className={`penalizacion penalizacion--${bloqueado ? 'bloqueado' : 'aviso'}`}>
      <div className="penalizacion__contenido">
        <span className="penalizacion__icono">{bloqueado ? '\u{1F6AB}' : '\u26A0\uFE0F'}</span>
        <div>
          <p className="penalizacion__titulo">
            {bloqueado ? 'Cuenta penalizada' : 'Aviso de penalizaci\u00f3n'}
          </p>
          <p className="penalizacion__texto">{aviso}</p>
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
    if (u) sessionStorage.setItem(SESSION_KEY, JSON.stringify(u));
    else sessionStorage.removeItem(SESSION_KEY);
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
        setView((v) => (v === 'login' ? defaultView(fresh) : vistaParaRol(fresh, v)));
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
      const fresh = await authApi.session(email);
      saveSession(fresh);
      // Si el rol cambió mientras la sesión estaba abierta, la pantalla se
      // ajusta al rol nuevo en vez de quedarse en una que ya no le toca.
      setView((v) => vistaParaRol(fresh, v));
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
      // RF23 / P23 — Notificación de confirmación de la reserva.
      const r = await reservationsApi.create({ email: user.email, slotId: slot.id });
      await refreshData(user.email);
      showToast(
        r.notificacion || `¡Reserva confirmada para las ${slot.hour} del ${reservaFecha?.label ?? 'día siguiente'}!`,
      );
    } catch (err) {
      // RF24 / P24 — Notificación al intentar una segunda reserva del mismo día.
      showToast(err.message, 'warning');
    }
  };

  const handleCancel = async (id) => {
    try {
      const r = await reservationsApi.cancel(id);
      await refreshData(user.email);
      await refreshSession(user.email);
      // RF25 — Notificación de cancelación registrada. Cancelar no penaliza ni
      // suma inasistencias: el aviso es informativo.
      showToast(r.notificacion || 'Reserva cancelada. El cupo quedó liberado.', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const staff = isStaff(user);

  return (
    <div className="app">

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {loading && (
        <div className="cargando"><div className="cargando__icono">⏳</div></div>
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

          {/* Aviso de inasistencias, siempre visible para el estudiante.
              Las cancelaciones no generan aviso: no hay límite ni sanción. */}
          {!staff && <PenaltyAlert user={user} />}

          {/* Los profesores y administradores NO reservan: solo ven el aforo. */}
          {!staff && view === 'dashboard' && (
            <Dashboard
              slots={slots}
              user={user}
              reservaFecha={reservaFecha}
              reservations={reservations}
              onReserve={handleReserve}
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
          {!staff && view === 'history' && <HistoryView user={user} />}

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
