import { describe, it, expect, beforeEach, vi } from 'vitest';
import { authApi, slotsApi, reservationsApi, adminApi, attendanceApi, reportsApi } from './api';

function mockFetch(responseData, ok = true) {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok, json: () => Promise.resolve(responseData) })
  );
}

describe('api service', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('login hace POST a /auth/login/ con el correo y el documento (RF02)', async () => {
    mockFetch({ name: 'Juan', email: 'j@soyudemedellin.edu.co', role: 'ESTUDIANTE' });
    const res = await authApi.login({ email: 'j@soyudemedellin.edu.co', documento: '1001234567' });
    expect(res.role).toBe('ESTUDIANTE');
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/auth/login/');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body).email).toBe('j@soyudemedellin.edu.co');
    expect(JSON.parse(opts.body).documento).toBe('1001234567');
  });

  it('register envía nombre, correo y documento de identidad (RF01)', async () => {
    mockFetch({ message: 'Registro exitoso.', role: 'ESTUDIANTE' }, true);
    await authApi.register({ name: 'Juan', email: 'j@soyudemedellin.edu.co', documento: '1001234567' });
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/auth/register/');
    expect(JSON.parse(opts.body)).toMatchObject({ name: 'Juan', documento: '1001234567' });
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
      documento: '3005554442',
    });
    expect(res.role).toBe('ADMIN');
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/admin/users/');
    expect(opts.method).toBe('POST');
  });

  it('lookup busca al estudiante por su documento (RF11)', async () => {
    mockFetch({ estudiante: { name: 'Ana', documento: '1001234567' }, tiene_reserva: true, reservas: [] });
    const res = await attendanceApi.lookup('1001234567', 'coach@udem.edu.co');
    expect(res.tiene_reserva).toBe(true);
    expect(global.fetch.mock.calls[0][0]).toContain('/students/lookup/?documento=1001234567');
  });

  it('register de asistencia hace POST a /attendance/register/ (RF13)', async () => {
    mockFetch({ message: 'Asistencia registrada.' });
    await attendanceApi.register({ actor_email: 'coach@udem.edu.co', documento: '1001234567' });
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/attendance/register/');
    expect(opts.method).toBe('POST');
  });

  it('pending lista a los estudiantes sin asistencia registrada (RF14)', async () => {
    mockFetch({ total: 2, pendientes: [{}, {}] });
    const res = await attendanceApi.pending('coach@udem.edu.co');
    expect(res.total).toBe(2);
    expect(global.fetch.mock.calls[0][0]).toContain('/attendance/pending/?actor_email=');
  });

  it('process procesa de forma general las inasistencias (RF15)', async () => {
    mockFetch({ total_procesadas: 3, total_penalizados: 1, message: 'ok' });
    const res = await attendanceApi.process('coach@udem.edu.co');
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/attendance/process/');
    expect(opts.method).toBe('POST');
    expect(res.total_procesadas).toBe(3);
  });

  it('personal devuelve el reporte de inasistencias del estudiante (RF18)', async () => {
    mockFetch({ no_show_count: 2, no_show_limite: 5, inasistencias_restantes: 3 });
    const res = await reportsApi.personal('j@soyudemedellin.edu.co');
    expect(res.inasistencias_restantes).toBe(3);
    expect(global.fetch.mock.calls[0][0]).toContain('/reports/personal/?email=');
  });

  it('daily devuelve los totales del reporte general diario (RF19)', async () => {
    mockFetch({ totales: { asistencias: 4, cancelaciones: 1, inasistencias: 2, estudiantes_penalizados: 1 } });
    const res = await reportsApi.daily('coach@udem.edu.co');
    expect(res.totales.asistencias).toBe(4);
    expect(global.fetch.mock.calls[0][0]).toContain('/reports/daily/?actor_email=');
  });

  it('dailyPdfUrl apunta al PDF del reporte diario (RF20)', () => {
    expect(reportsApi.dailyPdfUrl('coach@udem.edu.co')).toContain('/reports/daily.pdf?actor_email=');
  });

  it('setAdminRole retira el rol de administrador (RF22)', async () => {
    mockFetch({ message: 'Se retiró el rol.', role: 'SIN_ROL' });
    await adminApi.setAdminRole('otra@udemedellin.edu.co', 'retirar', 'jefe@udemedellin.edu.co');
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/admin/users/otra%40udemedellin.edu.co/');
    expect(opts.method).toBe('PATCH');
    expect(JSON.parse(opts.body).accion).toBe('retirar');
  });

  it('lanza Error con el mensaje del servidor cuando !ok', async () => {
    mockFetch({ error: 'No hay cupos disponibles en este horario.' }, false);
    await expect(reservationsApi.create({ email: 'j@soyudemedellin.edu.co', slotId: 1 }))
      .rejects.toThrow('No hay cupos disponibles');
  });
});
