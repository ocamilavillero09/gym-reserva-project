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

export const authApi = {
  register: (body) => request('/auth/register/', { method: 'POST', body: JSON.stringify(body) }),
  login:    (body) => request('/auth/login/',    { method: 'POST', body: JSON.stringify(body) }),
};

export const slotsApi = {
  getAll: () => request('/slots/'),
};

export const reservationsApi = {
  getByEmail: (email) => request(`/reservations/?email=${encodeURIComponent(email)}`),
  create:     (body)  => request('/reservations/', { method: 'POST', body: JSON.stringify(body) }),
  cancel:     (id)    => request(`/reservations/${id}/`, { method: 'DELETE' }),
  // RN09 — el entrenador/admin marca una inasistencia (No-Show).
  noShow:     (id, actorEmail) =>
    request(`/reservations/${id}/no-show/`, { method: 'POST', body: JSON.stringify({ actor_email: actorEmail }) }),
  // RF17 — el entrenador confirma asistencia.
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

// RF16 / RF17 — Reportes para el entrenador.
export const reportsApi = {
  occupancy: () => request('/reports/occupancy/'),
  noShows:   () => request('/reports/no-shows/'),
  csvUrl:    `${BASE}/reports/usage.csv`,
  pdfUrl:    `${BASE}/reports/usage.pdf`,
};

// RF18 — Máquinas.
export const machinesApi = {
  list:      ()                         => request('/machines/'),
  create:    (name, actorEmail)         => request('/machines/', { method: 'POST', body: JSON.stringify({ name, actor_email: actorEmail }) }),
  setEstado: (id, estado, note, actor)  => request(`/machines/${id}/`, { method: 'PATCH', body: JSON.stringify({ estado, note, actor_email: actor }) }),
};

// RF14 — Push.
export const pushApi = {
  publicKey: ()              => request('/push/public-key/'),
  subscribe: (email, sub)    => request('/push/subscribe/', { method: 'POST', body: JSON.stringify({ email, subscription: sub }) }),
  remind:    (slotId, actor) => request('/push/remind/', { method: 'POST', body: JSON.stringify({ slotId, actor_email: actor }) }),
};
