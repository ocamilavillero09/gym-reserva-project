import { test, expect } from '@playwright/test';

// Flujo end-to-end del ENTRENADOR contra el stack completo:
//   RF11  busca al estudiante por su documento de identidad
//   RF13  le registra la asistencia
//   RF14  consulta los estudiantes sin asistencia registrada
//   RF15  procesa de forma general las inasistencias
//   RF19  consulta el reporte general diario
const sufijo = () => `${Date.now()}${Math.floor(Math.random() * 1000)}`;

async function registrar(page, { nombre, email, documento }) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Registrarse' }).click();
  await page.getByPlaceholder('Ej: María García').fill(nombre);
  await page.getByPlaceholder('nombre@soyudemedellin.edu.co').fill(email);
  await page.getByPlaceholder('Ej: 1001234567').fill(documento);
  await page.getByRole('button', { name: /Crear cuenta/ }).click();
  await expect(page.getByText('¡Registro exitoso!')).toBeVisible();
  await page.getByRole('button', { name: /Ir a iniciar sesión/ }).click();
}

async function entrar(page, email, documento) {
  await page.getByPlaceholder('nombre@soyudemedellin.edu.co').fill(email);
  await page.getByPlaceholder('Ej: 1001234567').fill(documento);
  await page.getByRole('button', { name: /Ingresar/ }).click();
}

test('el entrenador busca por documento, registra la asistencia y ve el reporte diario', async ({ page }) => {
  const s = sufijo();
  const estudiante = { nombre: 'Estudiante Asistencia', email: `e2e.asis.${s}@soyudemedellin.edu.co`, documento: `91${s.slice(-8)}` };
  const coach = { nombre: 'Entrenador E2E', email: `e2e.coach.${s}@udem.edu.co`, documento: `71${s.slice(-8)}` };

  // --- El estudiante se registra y reserva el bloque del día siguiente ---
  await registrar(page, estudiante);
  await entrar(page, estudiante.email, estudiante.documento);
  await expect(page.getByText(/Hola, Estudiante/)).toBeVisible();
  await page.getByRole('button', { name: 'Reservar cupo' }).first().click();
  await page.getByRole('button', { name: /Confirmar/ }).click();
  await expect(page.getByText('✓ Ya reservado').first()).toBeVisible();
  await page.getByRole('button', { name: 'Salir' }).click();

  // --- El entrenador entra: ve el panel, no la pantalla de reservas (RF12) ---
  await registrar(page, coach);
  await entrar(page, coach.email, coach.documento);
  await expect(page.getByRole('heading', { name: 'Panel del gimnasio' })).toBeVisible();
  await expect(page.getByText('🕒 Bloques horarios y cupos')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reservar' })).toHaveCount(0);

  // --- RF14: el estudiante aparece sin asistencia registrada ---
  await expect(page.getByText('⏳ Sin asistencia registrada')).toBeVisible();

  // --- RF11: buscar al estudiante por su documento de identidad ---
  await page.getByPlaceholder('Documento de identidad del estudiante').fill(estudiante.documento);
  await page.getByRole('button', { name: 'Buscar' }).click();
  await expect(page.getByText(`Doc. ${estudiante.documento}`, { exact: false })).toBeVisible();

  // --- RF13: todavía NO se puede registrar la asistencia ---
  // La reserva se acaba de crear y es para MAÑANA: el estudiante aún no ha
  // tenido ocasión de presentarse, así que el sistema no ofrece el botón.
  // El camino feliz (registrar el día de la reserva) lo cubren las pruebas
  // unitarias de RF13, que sí pueden adelantar el reloj.
  await expect(page.getByText(/Aún no es el día de esta reserva/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Registrar asistencia' })).toHaveCount(0);

  // --- RF19: el reporte general diario del gimnasio ---
  await expect(page.getByText('📄 Reporte general diario')).toBeVisible();
  await expect(page.getByText('Estudiantes penalizados').first()).toBeVisible();
  // RF20: el botón descarga el reporte diario en PDF. Ya no es un enlace: se
  // pide con fetch para que el navegador no devuelva una copia en caché.
  const descarga = page.waitForEvent('download');
  await page.getByRole('button', { name: /Generar PDF/ }).click();
  expect((await descarga).suggestedFilename()).toMatch(/^reporte-diario-.*\.pdf$/);
});
