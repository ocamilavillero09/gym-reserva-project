/*
 * BARRA DE NAVEGACIÓN SUPERIOR
 *
 * Solo estructura y comportamiento. La presentación vive en
 * src/styles/navbar.css.
 */
import '../styles/navbar.css';

const ROLE_LABEL = {
  ESTUDIANTE: 'Estudiante',
  ENTRENADOR: 'Entrenador',
  ADMIN:      'Administrador',
};

export default function Navbar({ user, view, reservationCount, onNavigate, onLogout }) {
  const initials = user?.name
    ? user.name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
    : '?';

  // Profesores y administradores no tienen interfaz de reserva: su navegación
  // se limita al aforo (panel), la gestión y su perfil.
  const staff = user?.role === 'ENTRENADOR' || user?.role === 'ADMIN';

  return (
    <nav className="navbar">
      <div className="navbar__contenido">
        <div>
          <img className="navbar__logo" src="/logo-udem.png" alt="Universidad de Medellín" />
        </div>

        <div className="navbar__acciones">
          {!staff && (
            <>
              <NavBtn active={view === 'dashboard'} onClick={() => onNavigate('dashboard')}>
                Reservar
              </NavBtn>

              <div className="navbar__con-contador">
                <NavBtn active={view === 'my-reservations'} onClick={() => onNavigate('my-reservations')}>
                  Mis reservas
                </NavBtn>
                {reservationCount > 0 && (
                  <span className="navbar__contador">{reservationCount}</span>
                )}
              </div>

              <NavBtn active={view === 'history'} onClick={() => onNavigate('history')}>
                Historial
              </NavBtn>
            </>
          )}

          {/* Panel de aforo y gestión — solo profesor/admin */}
          {staff && (
            <NavBtn active={view === 'panel'} onClick={() => onNavigate('panel')}>
              Panel
            </NavBtn>
          )}

          {/* Gestión de usuarios — solo administrador */}
          {user?.role === 'ADMIN' && (
            <NavBtn active={view === 'admin'} onClick={() => onNavigate('admin')}>
              Usuarios
            </NavBtn>
          )}

          <NavBtn active={view === 'profile'} onClick={() => onNavigate('profile')}>
            Perfil
          </NavBtn>

          <div className="navbar__separador" />

          <div className="navbar__usuario">
            <div className="navbar__avatar">{initials}</div>
            <div className="navbar__datos">
              <p className="navbar__nombre">{user?.name}</p>
              <p className="navbar__rol">{ROLE_LABEL[user?.role] || user?.role}</p>
            </div>
            <button className="navbar__salir" onClick={onLogout}>Salir</button>
          </div>
        </div>
      </div>
    </nav>
  );
}

function NavBtn({ active, onClick, children }) {
  return (
    <button
      className={`navbar__boton${active ? ' navbar__boton--activo' : ''}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
