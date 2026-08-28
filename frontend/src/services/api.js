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
  // RN09 — el profesor/admin marca una inasistencia (No-Show).
  noShow:     (id, actorEmail) =>
    request(`/reservations/${id}/no-show/`, { method: 'POST', body: JSON.stringify({ actor_email: actorEmail }) }),
  // RF17 — el profesor confirma asistencia.
  complete:   (id, actorEmail) =>
    request(`/reservations/${id}/complete/`, { method: 'POST', body: JSON.stringify({ actor_email: actorEmail }) }),
  // RF11 — historial.
  history:    (email) => request(`/reservations/history/?email=${encodeURIComponent(email)}`),
};

// RF12 — Lista de espera.
export const waitlistApi = {
  join: (slotId, email) => request(`/slots/${slotId}/waitlist/`, { method: 'POST', body: JSON.stringify({ email }) }),
};

// RF13 — Perfil y metas.
export const profileApi = {
  get:    (email) => request(`/users/profile/?email=${encodeURIComponent(email)}`),
  update: (body)  => request('/users/profile/', { method: 'PUT', body: JSON.stringify(body) }),
};

// RF15 — Calificación del servicio.
export const ratingsApi = {
  list:   ()     => request('/ratings/'),
  create: (body) => request('/ratings/', { method: 'POST', body: JSON.stringify(body) }),
};

// Reportes: aforo, por estudiante, personal (RF18) y general diario (RF19/RF20).
export const reportsApi = {
  occupancy: () => request('/reports/occupancy/'),
  students:  () => request('/reports/students/'),
  // RF18 — Reporte personal del estudiante: inasistencias y penalizaciones.
  personal:  (email) => request(`/reports/personal/?email=${encodeURIComponent(email)}`),
  // RF19 — Reporte general diario del gimnasio.
  daily:     (actorEmail, fecha = '') =>
    request(`/reports/daily/?actor_email=${encodeURIComponent(actorEmail)}&fecha=${fecha}`),
  // RF20 — El mismo reporte diario en PDF, listo para imprimir.
  dailyPdfUrl: (actorEmail, fecha = '') =>
    `${BASE}/reports/daily.pdf?actor_email=${encodeURIComponent(actorEmail)}&fecha=${fecha}`,
  csvUrl:    `${BASE}/reports/usage.csv`,
  pdfUrl:    `${BASE}/reports/usage.pdf`,
};

// RF18 — Máquinas.
export const machinesApi = {
  list:      ()                         => request('/machines/'),
  create:    (name, actorEmail)         => request('/machines/', { method: 'POST', body: JSON.stringify({ name, actor_email: actorEmail }) }),
  setEstado: (id, estado, note, actor)  => request(`/machines/${id}/`, { method: 'PATCH', body: JSON.stringify({ estado, note, actor_email: actor }) }),
};
