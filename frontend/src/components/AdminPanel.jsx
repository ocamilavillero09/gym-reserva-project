/*
 * GESTIÓN DE USUARIOS (ADMINISTRADOR)
 *
 * El administrador principal crea cuentas —el rol se deduce del dominio del
 * correo— y puede retirar o restaurar el rol de administrador de otras
 * cuentas.
 *
 * Solo estructura y comportamiento. La presentación vive en
 * src/styles/admin.css.
 */
import { useCallback, useEffect, useState } from 'react';
import { adminApi } from '../services/api';
import '../styles/admin.css';

// Los tres dominios institucionales y el rol que otorga cada uno.
const DOMINIOS = [
  { dominio: '@soyudemedellin.edu.co', rol: 'ESTUDIANTE' },
  { dominio: '@udem.edu.co',           rol: 'ENTRENADOR' },
  { dominio: '@udemedellin.edu.co',    rol: 'ADMIN' },
];

const ROL = {
  ESTUDIANTE: { clase: 'estudiante', label: 'Estudiante' },
  ENTRENADOR: { clase: 'entrenador', label: 'Entrenador' },
  ADMIN:      { clase: 'admin',      label: 'Administrador' },
  SIN_ROL:    { clase: 'sin-rol',    label: 'Rol retirado' },
};

const rolDeCorreo = (email) =>
  DOMINIOS.find((d) => email.trim().toLowerCase().endsWith(d.dominio))?.rol ?? null;

export default function AdminPanel({ user, showToast }) {
  const [users, setUsers] = useState([]);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [documento, setDocumento] = useState('');
  const [enviando, setEnviando] = useState(false);

  const cargar = useCallback(() => {
    adminApi.listUsers(user.email).then(setUsers).catch(() => setUsers([]));
  }, [user.email]);

  useEffect(cargar, [cargar]);

  const crear = async (e) => {
    e.preventDefault();
    setEnviando(true);
    try {
      const r = await adminApi.createUser({
        actor_email: user.email,
        name: name.trim(),
        email: email.trim().toLowerCase(),
        documento: documento.trim(),
      });
      showToast(r.message, 'success');
      setName(''); setEmail(''); setDocumento('');
      cargar();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setEnviando(false);
    }
  };

  // Retirar o restaurar el rol de administrador de otra cuenta.
  const cambiarRol = async (objetivo, accion) => {
    const verbo = accion === 'retirar'
      ? 'retirar el rol de administrador a'
      : 'restaurar el rol de administrador a';
    if (!window.confirm(`¿Seguro que deseas ${verbo} ${objetivo.name}?`)) return;
    try {
      const r = await adminApi.setAdminRole(objetivo.email, accion, user.email);
      showToast(r.message, accion === 'retirar' ? 'warning' : 'success');
      cargar();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Solo el administrador principal gestiona las cuentas de administrador.
  const esPrincipal = user.es_principal ?? false;
  const rolDetectado = rolDeCorreo(email);
  // A un administrador que no es el principal ni se le ofrece el dominio de
  // administración ni se le deja enviar el formulario con él.
  const DISPONIBLES = esPrincipal ? DOMINIOS : DOMINIOS.filter((d) => d.rol !== 'ADMIN');
  const rolNoPermitido = rolDetectado === 'ADMIN' && !esPrincipal;
  const porRol = (rol) => users.filter((u) => u.role === rol).length;

  return (
    <div className="admin">
      <h2 className="admin__titulo">Gestión de usuarios</h2>
      <p className="admin__subtitulo">
        {esPrincipal ? 'Administrador principal' : 'Administrador'} · {user.email}
      </p>

      {!esPrincipal && (
        <div className="admin__aviso">
          ⚠️ Solo el <strong>administrador principal</strong> puede crear cuentas de administrador
          y retirarles el rol. Desde aquí puedes consultar los usuarios y crear estudiantes o entrenadores.
        </div>
      )}

      {/* Crear usuario. Los administradores solo los crea el principal. */}
      <div className="admin__tarjeta">
        <h3 className="admin__seccion">➕ Crear usuario</h3>
        <p className="admin__explicacion">
          El rol se asigna automáticamente según el dominio del correo, y el documento de
          identidad será su contraseña de ingreso.
          {esPrincipal
            ? ' Para crear otro administrador, usa un correo @udemedellin.edu.co.'
            : ' Puedes crear estudiantes y entrenadores; las cuentas de administrador solo las crea el administrador principal.'}
        </p>

        <div className="admin__dominios">
          {DISPONIBLES.map((d) => (
            <div key={d.dominio} className="admin__dominio">
              <span className={`rol rol--${ROL[d.rol].clase}`}>{ROL[d.rol].label}</span>
              <p className="admin__dominio-correo">{d.dominio}</p>
            </div>
          ))}
        </div>

        <form className="admin__formulario" onSubmit={crear}>
          <input className="admin__entrada" value={name} onChange={(e) => setName(e.target.value)}
                 placeholder="Nombre completo" required />
          <input
            className="admin__entrada"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="correo@udemedellin.edu.co"
            autoCapitalize="none"
            required
          />
          <input
            className="admin__entrada"
            type="text"
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            placeholder="Documento de identidad (mínimo 6 caracteres)"
            inputMode="numeric"
            required
          />

          {email && (
            <p className={`admin__pista admin__pista--${rolDetectado && !rolNoPermitido ? 'ok' : 'error'}`}>
              {rolNoPermitido
                ? '⚠ Solo el administrador principal puede crear cuentas de administrador.'
                : rolDetectado
                  ? `✓ Este correo creará un usuario con rol ${ROL[rolDetectado].label.toUpperCase()}.`
                  : '⚠ El correo no pertenece a ninguno de los tres dominios institucionales.'}
            </p>
          )}

          <button className="admin__crear" type="submit" disabled={enviando || rolNoPermitido}>
            {enviando ? 'Creando...' : 'Crear usuario'}
          </button>
        </form>
      </div>

      {/* Listado de usuarios */}
      <div className="admin__tarjeta">
        <div className="admin__encabezado">
          <h3 className="admin__seccion">👥 Usuarios registrados ({users.length})</h3>
          <span className="admin__resumen">
            {porRol('ESTUDIANTE')} estudiantes · {porRol('ENTRENADOR')} profesores · {porRol('ADMIN')} administradores
          </span>
        </div>

        {users.length === 0 ? (
          <p className="admin__vacio">Sin usuarios para mostrar.</p>
        ) : users.map((u) => {
          const rol = ROL[u.role] || { clase: 'otro', label: u.role };
          return (
            <div key={u.email} className="usuario">
              <div className="usuario__datos">
                <p className="usuario__nombre">
                  {u.name}
                  {u.es_principal && <span className="usuario__principal">★ PRINCIPAL</span>}
                </p>
                <p className="usuario__correo">
                  {u.email} · doc. {u.documento || '—'}
                </p>
              </div>
              <div className="usuario__acciones">
                {u.estado === 'PENALIZADO' && (
                  <span className="usuario__penalizado">PENALIZADO</span>
                )}
                <span className={`rol rol--${rol.clase}`}>{rol.label}</span>

                {/* Retirar o restaurar el rol de administrador */}
                {esPrincipal && !u.es_principal && u.role === 'ADMIN' && (
                  <button
                    className="usuario__boton usuario__boton--retirar"
                    onClick={() => cambiarRol(u, 'retirar')}
                  >
                    Retirar rol
                  </button>
                )}
                {esPrincipal && u.role === 'SIN_ROL' && (
                  <button
                    className="usuario__boton usuario__boton--restaurar"
                    onClick={() => cambiarRol(u, 'restaurar')}
                  >
                    Restaurar
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
