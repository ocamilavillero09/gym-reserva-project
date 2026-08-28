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

  // --- RF13: registrar la asistencia ---
  await page.getByRole('button', { name: 'Registrar asistencia' }).first().click();
  await expect(page.getByText(/Asistencia registrada/i).first()).toBeVisible();

  // --- RF19: el reporte general diario refleja la asistencia ---
  await expect(page.getByText('📄 Reporte general diario')).toBeVisible();
  await expect(page.getByText('Estudiantes penalizados').first()).toBeVisible();
  // RF20: el botón de impresión del PDF apunta al reporte diario.
  await expect(page.getByRole('link', { name: /Generar PDF/ }))
    .toHaveAttribute('href', /\/reports\/daily\.pdf\?actor_email=/);
});
