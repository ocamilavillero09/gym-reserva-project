const RED = '#CC0000';

export default function Navbar({ user, view, reservationCount, onNavigate, onLogout }) {
  const initials = user?.name
    ? user.name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
    : '?';

  return (
    <nav style={{
      background: `linear-gradient(90deg, ${RED} 0%, #AA0000 100%)`,
      boxShadow: '0 2px 16px rgba(0,0,0,0.25)',
      position: 'sticky', top: 0, zIndex: 100,
    }}>
      <div style={{
        maxWidth: 1100, margin: '0 auto', padding: '0 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 66,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <img src="/logo-udem.png" alt="Universidad de Medellín" style={{ height: 38, filter: 'brightness(0) invert(1)' }} />
        </div>

        {/* Nav links + user */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <NavBtn active={view === 'dashboard'} onClick={() => onNavigate('dashboard')}>
            Reservar
          </NavBtn>

          <div style={{ position: 'relative' }}>
            <NavBtn active={view === 'my-reservations'} onClick={() => onNavigate('my-reservations')}>
              Mis reservas
            </NavBtn>
            {reservationCount > 0 && (
              <span style={{
                position: 'absolute', top: 2, right: 2,
                backgroundColor: 'white', color: RED,
                width: 18, height: 18, borderRadius: '50%',
                fontSize: 11, fontWeight: 800,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                pointerEvents: 'none',
              }}>
                {reservationCount}
              </span>
            )}
          </div>

          <div style={{ width: 1, height: 28, backgroundColor: 'rgba(255,255,255,0.3)', margin: '0 6px' }} />

          {/* Avatar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 38, height: 38, borderRadius: '50%',
              backgroundColor: 'rgba(255,255,255,0.25)',
              border: '2px solid rgba(255,255,255,0.5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'white', fontWeight: 800, fontSize: 13, flexShrink: 0,
            }}>
              {initials}
            </div>
            <span style={{ color: 'rgba(255,255,255,0.9)', fontSize: 13, maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.name}
            </span>
            <button onClick={onLogout} style={{
              padding: '7px 14px',
              border: '1.5px solid rgba(255,255,255,0.45)',
              borderRadius: 9, cursor: 'pointer',
              backgroundColor: 'transparent', color: 'white',
              fontSize: 13, fontWeight: 600,
            }}>
              Salir
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

function NavBtn({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{
      padding: '8px 18px', border: 'none', borderRadius: 10, cursor: 'pointer',
      backgroundColor: active ? 'rgba(255,255,255,0.22)' : 'transparent',
      color: 'white',
      fontWeight: active ? 700 : 500,
      fontSize: 14,
      transition: 'background 0.2s',
    }}>
      {children}
    </button>
  );
}
