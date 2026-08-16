import { describe, it, expect, beforeEach, vi } from 'vitest';
import { authApi, slotsApi, reservationsApi, adminApi } from './api';

function mockFetch(responseData, ok = true) {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok, json: () => Promise.resolve(responseData) })
  );
}

describe('api service', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('login hace POST a /auth/login/ con el body', async () => {
    mockFetch({ name: 'Juan', email: 'j@soyudemedellin.edu.co', role: 'ESTUDIANTE' });
    const res = await authApi.login({ email: 'j@soyudemedellin.edu.co', password: 'x' });
    expect(res.role).toBe('ESTUDIANTE');
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/auth/login/');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body).email).toBe('j@soyudemedellin.edu.co');
  });

  it('session rehidrata la sesión con GET y el correo en la query', async () => {
    mockFetch({ email: 'j@soyudemedellin.edu.co', role: 'ESTUDIANTE', cancel_count: 2 });
    const res = await authApi.session('j@soyudemedellin.edu.co');
    expect(res.cancel_count).toBe(2);
    expect(global.fetch.mock.calls[0][0]).toContain('/auth/session/?email=');
  });

  it('getAll de slots devuelve la fecha del día siguiente y los bloques', async () => {
    mockFetch({
      fecha: '2026-08-17',
      fecha_label: 'lunes 17 de agosto de 2026',
      slots: [{ id: 1, hour: '06:00', available: 20, total: 20 }],
    });
    const data = await slotsApi.getAll();
    expect(data.slots).toHaveLength(1);
    expect(data.fecha_label).toContain('agosto');
    expect(global.fetch.mock.calls[0][0]).toContain('/slots/');
  });

  it('noShow envía actor_email al endpoint correcto', async () => {
    mockFetch({ message: 'ok', penalizado: false });
    await reservationsApi.noShow('abc123', 'profe@udem.edu.co');
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/reservations/abc123/no-show/');
    expect(JSON.parse(opts.body).actor_email).toBe('profe@udem.edu.co');
  });

  it('el admin crea usuarios con POST a /admin/users/', async () => {
    mockFetch({ message: 'Usuario creado con rol ADMIN.', role: 'ADMIN' }, true);
    const res = await adminApi.createUser({
      actor_email: 'jefe@udemedellin.edu.co',
      name: 'Nueva Admin',
      email: 'nueva@udemedellin.edu.co',
      password: 'secreto123',
    });
    expect(res.role).toBe('ADMIN');
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/admin/users/');
    expect(opts.method).toBe('POST');
  });

  it('lanza Error con el mensaje del servidor cuando !ok', async () => {
    mockFetch({ error: 'No hay cupos disponibles en este horario.' }, false);
    await expect(reservationsApi.create({ email: 'j@soyudemedellin.edu.co', slotId: 1 }))
      .rejects.toThrow('No hay cupos disponibles');
  });
});
