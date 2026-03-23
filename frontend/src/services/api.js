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
};
