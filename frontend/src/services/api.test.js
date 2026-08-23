/**
 * PRUEBAS UNITARIAS DEL CLIENTE HTTP DEL FRONTEND
 *
 * Comprueban que cada función arma la petición que le corresponde y trata bien
 * la respuesta. El servidor no interviene: `fetch` está sustituido por un
 * doble, así que estas pruebas corren solas y en milisegundos.
 *
 *     cd frontend && npm test
 *
 * REQUISITOS QUE SE PRUEBAN AQUÍ
 *     RF01/RF02  Registro e inicio de sesión
 *     RF03       El rol lo decide el dominio del correo
 *     RF04/RF05  Perfil del estudiante y del personal
 *     RF08/RF09  Reserva para el día siguiente y su límite diario
 *     RF10       Consulta de las reservas hechas
 *     RF11/RF13  Búsqueda por documento y registro de asistencia
 *     RF12       Consulta del aforo por el personal
 *     RF17       Historial
 *     RF18       Reporte personal
 *     RF25       Notificación de cancelación de reserva
 *
 * Los demás requisitos quedaron fuera del alcance de pruebas acordado con el
 * equipo; en el código aparecen marcados como [IGNORADO].
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  authApi, profileApi, slotsApi, reservationsApi,
  attendanceApi, reportsApi,
} from './api';

const BASE = 'http://localhost:8000/api';

/** Deja preparado un `fetch` que responde lo que se le indique. */
function responderCon(cuerpo, { ok = true, status = 200 } = {}) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => cuerpo,
  });
}

/** La petición que se envió: [url, opciones]. */
const peticion = () => global.fetch.mock.calls[0];
const urlPedida = () => peticion()[0];
const opciones  = () => peticion()[1] ?? {};
const cuerpoEnviado = () => JSON.parse(opciones().body);

beforeEach(() => {
  vi.restoreAllMocks();
});

// ── RF01 · Registro ───────────────────────────────────────────────────────
describe('RF01 — Registro de usuarios', () => {
  it('envía nombre, correo y documento al recurso de registro', async () => {
    responderCon({ message: 'Registro exitoso.', role: 'ESTUDIANTE' });
    await authApi.register({
      name: 'Ana Gómez',
      email: 'ana@soyudemedellin.edu.co',
      documento: '1001234567',
    });
    expect(urlPedida()).toBe(`${BASE}/auth/register/`);
    expect(opciones().method).toBe('POST');
    expect(cuerpoEnviado()).toEqual({
      name: 'Ana Gómez',
      email: 'ana@soyudemedellin.edu.co',
      documento: '1001234567',
    });
  });

  it('devuelve el rol que asignó el servidor', async () => {
    responderCon({ role: 'ENTRENADOR' });
    const r = await authApi.register({ email: 'coach@udem.edu.co' });
    expect(r.role).toBe('ENTRENADOR');
  });
});

// ── RF02 · Inicio de sesión ───────────────────────────────────────────────
describe('RF02 — Inicio de sesión', () => {
  it('envía el correo y el documento como credenciales', async () => {
    responderCon({ email: 'ana@soyudemedellin.edu.co', role: 'ESTUDIANTE' });
    await authApi.login({ email: 'ana@soyudemedellin.edu.co', documento: '1001234567' });
    expect(urlPedida()).toBe(`${BASE}/auth/login/`);
    expect(cuerpoEnviado().documento).toBe('1001234567');
  });

  it('propaga el mensaje de error cuando el servidor rechaza el acceso', async () => {
    responderCon({ error: 'Correo o documento de identidad incorrectos.' },
                 { ok: false, status: 401 });
    await expect(authApi.login({ email: 'x', documento: 'y' }))
      .rejects.toThrow('Correo o documento de identidad incorrectos.');
  });

  it('recupera la sesión guardada al recargar la página', async () => {
    responderCon({ email: 'ana@soyudemedellin.edu.co' });
    await authApi.session('ana@soyudemedellin.edu.co');
    expect(urlPedida()).toContain('/auth/session/?email=');
  });

  it('codifica el correo para que la arroba no rompa la dirección', async () => {
    responderCon({});
    await authApi.session('ana@soyudemedellin.edu.co');
    expect(urlPedida()).toContain('ana%40soyudemedellin.edu.co');
  });
});

// ── RF04 / RF05 · Perfil ──────────────────────────────────────────────────
describe('RF04 y RF05 — Perfil del estudiante y del personal', () => {
  it('consulta el perfil por correo', async () => {
    responderCon({ name: 'Ana', role: 'ESTUDIANTE' });
    await profileApi.get('ana@soyudemedellin.edu.co');
    expect(urlPedida()).toContain('/users/profile/?email=');
  });

  it('guarda edad, peso, altura y objetivo con PUT', async () => {
    responderCon({ edad: 21 });
    await profileApi.update({
      email: 'ana@soyudemedellin.edu.co', edad: 21, peso: 68, altura: 170,
      meta: 'Ganar resistencia',
    });
    expect(opciones().method).toBe('PUT');
    expect(cuerpoEnviado().meta).toBe('Ganar resistencia');
  });
});

// ── RF08 · Reserva ────────────────────────────────────────────────────────
describe('RF08 — Reserva para el día siguiente', () => {
  it('envía el correo y el bloque elegido', async () => {
    responderCon({ estado: 'ACTIVA' });
    await reservationsApi.create({ email: 'ana@soyudemedellin.edu.co', slotId: 1 });
    expect(urlPedida()).toBe(`${BASE}/reservations/`);
    expect(cuerpoEnviado()).toEqual({ email: 'ana@soyudemedellin.edu.co', slotId: 1 });
  });

  it('la consulta de bloques trae la fecha del día siguiente', async () => {
    responderCon({ fecha: '2026-08-23', fecha_label: 'domingo 23 de agosto de 2026', slots: [] });
    const r = await slotsApi.getAll();
    expect(urlPedida()).toBe(`${BASE}/slots/`);
    expect(r.fecha).toBe('2026-08-23');
  });

  it('propaga el aviso cuando ya hay una reserva ese día', async () => {
    responderCon({ error: 'Ya tienes una reserva para el domingo.' },
                 { ok: false, status: 409 });
    await expect(reservationsApi.create({ email: 'ana@x.co', slotId: 2 }))
      .rejects.toThrow('Ya tienes una reserva para el domingo.');
  });
});

// ── RF10 · Consulta de reservas ───────────────────────────────────────────
describe('RF10 — Consulta de las reservas hechas', () => {
  it('pide las reservas del estudiante indicado', async () => {
    responderCon([]);
    await reservationsApi.getByEmail('ana@soyudemedellin.edu.co');
    expect(urlPedida()).toContain('/reservations/?email=');
  });

  it('devuelve tal cual la lista que envía el servidor', async () => {
    responderCon([{ id: '1', hour: '06:00' }]);
    const r = await reservationsApi.getByEmail('ana@x.co');
    expect(r).toHaveLength(1);
    expect(r[0].hour).toBe('06:00');
  });
});

// ── RF11 / RF13 · Búsqueda y asistencia ───────────────────────────────────
describe('RF11 y RF13 — Búsqueda por documento y registro de asistencia', () => {
  it('busca al estudiante por documento indicando quién consulta', async () => {
    responderCon({ estudiante: {}, reservas: [] });
    await attendanceApi.lookup('1001234567', 'coach@udem.edu.co');
    expect(urlPedida()).toContain('documento=1001234567');
    expect(urlPedida()).toContain('actor_email=coach%40udem.edu.co');
  });

  it('registra la asistencia con el identificador de la reserva', async () => {
    responderCon({ message: 'Asistencia registrada.' });
    await attendanceApi.register({ actor_email: 'coach@udem.edu.co', reservation_id: 'abc' });
    expect(urlPedida()).toBe(`${BASE}/attendance/register/`);
    expect(cuerpoEnviado().reservation_id).toBe('abc');
  });

  it('avisa cuando todavía no es el día de la reserva', async () => {
    responderCon({ error: 'La asistencia solo puede registrarse el día de la reserva.' },
                 { ok: false, status: 409 });
    await expect(attendanceApi.register({ actor_email: 'coach@udem.edu.co' }))
      .rejects.toThrow(/solo puede registrarse el día de la reserva/);
  });
});

// ── RF12 · Aforo para el personal ─────────────────────────────────────────
describe('RF12 — El personal consulta el aforo', () => {
  it('pide el reporte de ocupación', async () => {
    responderCon([{ slotId: 1, available: 19, total: 20 }]);
    const r = await reportsApi.occupancy();
    expect(urlPedida()).toBe(`${BASE}/reports/occupancy/`);
    expect(r[0].available).toBe(19);
  });
});

// ── RF17 · Historial ──────────────────────────────────────────────────────
describe('RF17 — Historial del estudiante', () => {
  it('pide el historial del correo indicado', async () => {
    responderCon([]);
    await reservationsApi.history('ana@soyudemedellin.edu.co');
    expect(urlPedida()).toContain('/reservations/history/?email=');
  });
});

// ── RF18 · Reporte personal ───────────────────────────────────────────────
describe('RF18 — Reporte personal de inasistencias', () => {
  it('pide el reporte del estudiante', async () => {
    responderCon({ no_show_count: 0, no_show_limite: 5 });
    const r = await reportsApi.personal('ana@soyudemedellin.edu.co');
    expect(urlPedida()).toContain('/reports/personal/?email=');
    expect(r.no_show_limite).toBe(5);
  });
});

// ── RF25 · Cancelación ────────────────────────────────────────────────────
describe('RF25 — Cancelación de la reserva', () => {
  it('cancela con DELETE sobre la reserva indicada', async () => {
    responderCon({ tipo: 'RESERVA_CANCELADA', notificacion: 'Cancelaste tu reserva.' });
    await reservationsApi.cancel('abc123');
    expect(urlPedida()).toBe(`${BASE}/reservations/abc123/`);
    expect(opciones().method).toBe('DELETE');
  });

  it('devuelve el aviso de cancelación', async () => {
    responderCon({ tipo: 'RESERVA_CANCELADA', notificacion: 'El cupo quedó liberado.' });
    const r = await reservationsApi.cancel('abc123');
    expect(r.tipo).toBe('RESERVA_CANCELADA');
    expect(r.notificacion).toContain('liberado');
  });

  it('cancelar no informa de ninguna penalización', async () => {
    responderCon({ tipo: 'RESERVA_CANCELADA', cancel_count: 5, no_show_count: 0 });
    const r = await reservationsApi.cancel('abc123');
    expect(r.no_show_count).toBe(0);
    expect(r.penalizado).toBeUndefined();
  });

  it('propaga el error si la reserva ya no está activa', async () => {
    responderCon({ error: 'La reserva ya no está activa.' }, { ok: false, status: 409 });
    await expect(reservationsApi.cancel('abc123'))
      .rejects.toThrow('La reserva ya no está activa.');
  });
});

// ── Comportamiento común del cliente ──────────────────────────────────────
describe('Cliente HTTP — comportamiento común', () => {
  it('usa un mensaje genérico cuando el error no trae texto', async () => {
    responderCon({}, { ok: false, status: 500 });
    await expect(slotsApi.getAll()).rejects.toThrow('Error en el servidor');
  });

  it('envía siempre el tipo de contenido JSON', async () => {
    responderCon({});
    await slotsApi.getAll();
    expect(opciones().headers['Content-Type']).toBe('application/json');
  });
});
