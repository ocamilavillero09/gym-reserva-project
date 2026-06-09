import { test, expect } from '@playwright/test';

// Flujo end-to-end completo contra el sistema real (front + back + mongo):
// registro → login → reservar un bloque → cancelar la reserva.
test('flujo completo de reserva de un estudiante', async ({ page }) => {
  const email = `e2e.${Date.now()}@udem.edu.co`;
  const password = 'secreto123';

  await page.goto('/');

  // --- Registro ---
  await page.getByRole('button', { name: 'Registrarse' }).click();
  await page.getByPlaceholder('Ej: María García').fill('Estudiante E2E');
  await page.getByPlaceholder('nombre@soyudemedellin.edu.co').fill(email);
  await page.getByPlaceholder('Mínimo 6 caracteres').fill(password);
  await page.getByRole('button', { name: /Crear cuenta/ }).click();

  // Pantalla de éxito → ir a login
  await expect(page.getByText('¡Registro exitoso!')).toBeVisible();
  await page.getByRole('button', { name: /Ir a iniciar sesión/ }).click();

  // --- Login ---
  await page.getByPlaceholder('nombre@soyudemedellin.edu.co').fill(email);
  await page.getByPlaceholder('Mínimo 6 caracteres').fill(password);
  await page.getByRole('button', { name: /Ingresar/ }).click();

  // --- Dashboard ---
  await expect(page.getByText(/Hola, Estudiante/)).toBeVisible();

  // --- Reservar el primer bloque disponible ---
  await page.getByRole('button', { name: 'Reservar cupo' }).first().click();
  await expect(page.getByText('Confirmar reserva')).toBeVisible();
  await page.getByRole('button', { name: /Confirmar/ }).click();

  // Aparece confirmación (toast) y la tarjeta queda como reservada.
  await expect(page.getByText('✓ Ya reservado').first()).toBeVisible();

  // --- Mis reservas → cancelar ---
  await page.getByRole('button', { name: 'Mis reservas' }).click();
  await expect(page.getByRole('heading', { name: 'Mis reservas' })).toBeVisible();
  await page.getByRole('button', { name: 'Cancelar' }).first().click();
  await expect(page.getByText('¿Cancelar reserva?')).toBeVisible();
  await page.getByRole('button', { name: 'Sí, cancelar' }).click();

  // Tras cancelar, queda el estado vacío.
  await expect(page.getByText('Sin reservas activas')).toBeVisible();
});
