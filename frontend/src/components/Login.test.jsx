import { describe, it, expect } from 'vitest';
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

  it('anuncia los tres dominios institucionales y su rol', () => {
    render(<Login onLogin={() => {}} />);
    expect(screen.getByText(/Tres tipos de correo institucional/i)).toBeInTheDocument();
    expect(screen.getByText('@soyudemedellin.edu.co')).toBeInTheDocument();
    expect(screen.getByText('@udem.edu.co')).toBeInTheDocument();
    expect(screen.getByText('@udemedellin.edu.co')).toBeInTheDocument();
  });

  it('pide el documento de identidad como contraseña (RF01/RF02)', () => {
    render(<Login onLogin={() => {}} />);
    expect(screen.getByText('Documento de identidad')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ej: 1001234567')).toBeInTheDocument();
    expect(screen.getByText(/Tu documento de identidad es tu contraseña/i)).toBeInTheDocument();
  });

  it('al escribir el correo en el registro indica el rol que se asignará', () => {
    render(<Login onLogin={() => {}} />);
    fireEvent.click(screen.getByText('Registrarse'));
    fireEvent.change(screen.getByPlaceholderText(/nombre@soyudemedellin/i), {
      target: { value: 'jefa@udemedellin.edu.co' },
    });
    expect(screen.getByText(/Entrarás como ADMINISTRADOR/i)).toBeInTheDocument();
  });
});
