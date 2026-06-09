import { describe, it, expect, beforeEach, vi } from 'vitest';
import { authApi, slotsApi, reservationsApi } from './api';

function mockFetch(responseData, ok = true) {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok, json: () => Promise.resolve(responseData) })
  );
}

describe('api service', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('login hace POST a /auth/login/ con el body', async () => {
    mockFetch({ name: 'Juan', email: 'j@udem.edu.co', role: 'ESTUDIANTE' });
    const res = await authApi.login({ email: 'j@udem.edu.co', password: 'x' });
    expect(res.role).toBe('ESTUDIANTE');
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/auth/login/');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body).email).toBe('j@udem.edu.co');
  });

  it('getAll de slots hace GET', async () => {
    mockFetch([{ id: 1, hour: '06:00', available: 20, total: 20 }]);
    const slots = await slotsApi.getAll();
    expect(slots).toHaveLength(1);
    expect(global.fetch.mock.calls[0][0]).toContain('/slots/');
  });

  it('noShow envía actor_email al endpoint correcto', async () => {
    mockFetch({ message: 'ok', penalizado: false });
    await reservationsApi.noShow('abc123', 'coach@udem.edu.co');
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/reservations/abc123/no-show/');
    expect(JSON.parse(opts.body).actor_email).toBe('coach@udem.edu.co');
  });

  it('lanza Error con el mensaje del servidor cuando !ok', async () => {
    mockFetch({ error: 'No hay cupos disponibles en este horario.' }, false);
    await expect(reservationsApi.create({ email: 'j@udem.edu.co', slotId: 1 }))
      .rejects.toThrow('No hay cupos disponibles');
  });
});
