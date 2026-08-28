import { test, expect } from '@playwright/test';

// Flujo end-to-end completo contra el sistema real (front + back + mongo):
// registro → login → reservar el bloque del día siguiente → cancelar.
test('flujo completo de reserva de un estudiante', async ({ page }) => {
  const email = `e2e.${Date.now()}@soyudemedellin.edu.co`;
  // RF01/RF02 — El documento de identidad es el dato de registro y la contraseña.
  const documento = `${Date.now()}`.slice(-10);

  await page.goto('/');

  // --- Registro (el dominio del correo asigna el rol ESTUDIANTE) ---
  await page.getByRole('button', { name: 'Registrarse' }).click();
  await page.getByPlaceholder('Ej: María García').fill('Estudiante E2E');
  await page.getByPlaceholder('nombre@soyudemedellin.edu.co').fill(email);
  await page.getByPlaceholder('Ej: 1001234567').fill(documento);
  await page.getByRole('button', { name: /Crear cuenta/ }).click();

  // Pantalla de éxito → ir a login
  await expect(page.getByText('¡Registro exitoso!')).toBeVisible();
  await page.getByRole('button', { name: /Ir a iniciar sesión/ }).click();

  // --- Login ---
  await page.getByPlaceholder('nombre@soyudemedellin.edu.co').fill(email);
  await page.getByPlaceholder('Ej: 1001234567').fill(documento);
  await page.getByRole('button', { name: /Ingresar/ }).click();

  // --- Dashboard: se anuncia que la reserva es para el día siguiente ---
  await expect(page.getByText(/Hola, Estudiante/)).toBeVisible();
  await expect(page.getByText(/Estás reservando para mañana/i)).toBeVisible();

  // --- Reservar el primer bloque disponible ---
  await page.getByRole('button', { name: 'Reservar cupo' }).first().click();
  await expect(page.getByText('Confirmar reserva')).toBeVisible();
  await expect(page.getByText(/Reserva para mañana/i)).toBeVisible();
  await page.getByRole('button', { name: /Confirmar/ }).click();

  // La tarjeta queda reservada y el resto se bloquea (una reserva por día).
  await expect(page.getByText('✓ Ya reservado').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ya reservaste este día' }).first()).toBeVisible();

  // --- La sesión sobrevive a una recarga de la página ---
  await page.reload();
  await expect(page.getByText(/Hola, Estudiante/)).toBeVisible();

  // --- Mis reservas → cancelar ---
  await page.getByRole('button', { name: 'Mis reservas' }).click();
  await expect(page.getByRole('heading', { name: 'Mis reservas' })).toBeVisible();
  await page.getByRole('button', { name: 'Cancelar' }).first().click();
  await expect(page.getByText('¿Cancelar reserva?')).toBeVisible();
  await page.getByRole('button', { name: 'Sí, cancelar' }).click();

  // Tras cancelar, queda el estado vacío.
  await expect(page.getByText('Sin reservas activas')).toBeVisible();
});
