import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Login from './Login';

describe('Login', () => {
  it('muestra las pestañas de iniciar sesión y registrarse', () => {
    render(<Login onLogin={() => {}} />);
    expect(screen.getByText('Iniciar sesión')).toBeInTheDocument();
    expect(screen.getByText('Registrarse')).toBeInTheDocument();
  });

  it('al cambiar a Registrarse aparece el campo Nombre completo', () => {
    render(<Login onLogin={() => {}} />);
    fireEvent.click(screen.getByText('Registrarse'));
    expect(screen.getByPlaceholderText(/María García/i)).toBeInTheDocument();
  });

  it('exige correo institucional en el aviso', () => {
    render(<Login onLogin={() => {}} />);
    expect(screen.getByText(/@udem\.edu\.co/i)).toBeInTheDocument();
  });
});
