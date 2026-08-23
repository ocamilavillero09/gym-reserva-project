const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Error en el servidor');
  return data;
}

// RF01/RF02 — Registro e inicio de sesión con nombre, correo institucional y
// DOCUMENTO DE IDENTIDAD (el documento es además la contraseña).
export const authApi = {
  register: (body) => request('/auth/register/', { method: 'POST', body: JSON.stringify(body) }),
  login:    (body) => request('/auth/login/',    { method: 'POST', body: JSON.stringify(body) }),
  // Rehidrata la sesión al recargar la página (la sesión no se pierde con F5).
  session:  (email) => request(`/auth/session/?email=${encodeURIComponent(email)}`),
};

// RF21/RF22 — Gestión de usuarios por el ADMINISTRADOR PRINCIPAL.
export const adminApi = {
  listUsers:  (actorEmail) => request(`/admin/users/?actor_email=${encodeURIComponent(actorEmail)}`),
  createUser: (body)       => request('/admin/users/', { method: 'POST', body: JSON.stringify(body) }),
  // RF22 — accion: 'retirar' | 'restaurar' el rol de administrador.
  setAdminRole: (email, accion, actorEmail) =>
    request(`/admin/users/${encodeURIComponent(email)}/`, {
      method: 'PATCH',
      body: JSON.stringify({ accion, actor_email: actorEmail }),
    }),
};

// RF11/RF13 — El entrenador busca al estudiante por su DOCUMENTO y le registra
// la asistencia. RF14/RF15 — Inasistencias pendientes y su procesamiento general.
export const attendanceApi = {
  lookup: (documento, actorEmail) =>
    request(`/students/lookup/?documento=${encodeURIComponent(documento)}&actor_email=${encodeURIComponent(actorEmail)}`),
  register: (body) => request('/attendance/register/', { method: 'POST', body: JSON.stringify(body) }),
  pending:  (actorEmail, fecha = '') =>
    request(`/attendance/pending/?actor_email=${encodeURIComponent(actorEmail)}&fecha=${fecha}`),
  process:  (actorEmail, fecha = '') =>
    request('/attendance/process/', { method: 'POST', body: JSON.stringify({ actor_email: actorEmail, fecha }) }),
};

export const slotsApi = {
  // Devuelve { fecha, fecha_label, slots } — la fecha es SIEMPRE el día siguiente.
  getAll: () => request('/slots/'),
};

export const reservationsApi = {
  getByEmail: (email) => request(`/reservations/?email=${encodeURIComponent(email)}`),
  create:     (body)  => request('/reservations/', { method: 'POST', body: JSON.stringify(body) }),
  cancel:     (id)    => request(`/reservations/${id}/`, { method: 'DELETE' }),
  // RF16 — el profesor/admin marca una inasistencia.
  noShow:     (id, actorEmail) =>
    request(`/reservations/${id}/no-show/`, { method: 'POST', body: JSON.stringify({ actor_email: actorEmail }) }),
  // RF17 — historial.
  history:    (email) => request(`/reservations/history/?email=${encodeURIComponent(email)}`),
};

// RF04/RF05 — Perfil del estudiante y del personal.
export const profileApi = {
  get:    (email) => request(`/users/profile/?email=${encodeURIComponent(email)}`),
  update: (body)  => request('/users/profile/', { method: 'PUT', body: JSON.stringify(body) }),
};

// RF07/RF12 — aforo · RF18 — reporte personal · RF19/RF20 — reporte diario.
export const reportsApi = {
  occupancy: () => request('/reports/occupancy/'),
  // RF18 — Reporte personal del estudiante: inasistencias y penalizaciones.
  personal:  (email) => request(`/reports/personal/?email=${encodeURIComponent(email)}`),
  // RF19 — Reporte general diario del gimnasio.
  // `cache: no-store` y el parámetro `_` obligan a traer siempre datos frescos:
  // sin ellos el navegador reutilizaba la respuesta anterior y el reporte se
  // quedaba desactualizado tras registrar asistencias.
  daily:     (actorEmail, fecha = '') =>
    request(`/reports/daily/?actor_email=${encodeURIComponent(actorEmail)}`
      + `&fecha=${encodeURIComponent(fecha)}&_=${Date.now()}`, { cache: 'no-store' }),

  // RF20 — El mismo reporte diario en PDF, listo para imprimir.
  // Se pide con fetch y se entrega como archivo en lugar de abrir un enlace:
  // así el navegador no devuelve una copia guardada en caché y el botón
  // funciona aunque estén bloqueadas las ventanas emergentes.
  dailyPdf: async (actorEmail, fecha = '') => {
    const url = `${BASE}/reports/daily.pdf?actor_email=${encodeURIComponent(actorEmail)}`
      + `&fecha=${encodeURIComponent(fecha)}&_=${Date.now()}`;
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) {
      let mensaje = 'No se pudo generar el reporte en PDF.';
      try { mensaje = (await res.json()).error || mensaje; } catch { /* la respuesta no era JSON */ }
      throw new Error(mensaje);
    }
    return res.blob();
  },
};
