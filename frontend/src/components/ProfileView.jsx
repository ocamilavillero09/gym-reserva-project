/*
 * MI PERFIL
 *
 * Muestra los datos de la cuenta, el reporte personal de inasistencias y
 * penalizaciones, las cancelaciones acumuladas y —solo para estudiantes— la
 * información de entrenamiento.
 *
 * Solo estructura y comportamiento. La presentación vive en
 * src/styles/perfil.css.
 */
import { useCallback, useEffect, useState } from 'react';
import { profileApi, reportsApi } from '../services/api';
import '../styles/perfil.css';

const ROLE_LABEL = {
  ESTUDIANTE: 'Estudiante',
  ENTRENADOR: 'Entrenador',
  ADMIN: 'Administrador',
  SIN_ROL: 'Sin rol asignado',
};

export default function ProfileView({ user, showToast }) {
  const [edad, setEdad] = useState('');
  const [peso, setPeso] = useState('');
  const [altura, setAltura] = useState('');
  const [meta, setMeta] = useState('');
  const [datos, setDatos] = useState(null);
  const [reporte, setReporte] = useState(null);

  const cargar = useCallback(() => {
    profileApi.get(user.email).then((p) => {
      setDatos(p);
      setEdad(p.edad ?? '');
      setPeso(p.peso ?? '');
      setAltura(p.altura ?? '');
      setMeta(p.meta ?? '');
    }).catch(() => {});
  }, [user.email]);

  useEffect(cargar, [cargar]);

  const esEstudiante = (datos?.role ?? user.role) === 'ESTUDIANTE';

  // Reporte personal de inasistencias y penalizaciones.
  useEffect(() => {
    if (!esEstudiante) return;
    reportsApi.personal(user.email).then(setReporte).catch(() => {});
  }, [user.email, esEstudiante, datos]);

  // <input type="number"> acepta notación científica, así que deja teclear
  // «e», «E», «+» y «-». Se bloquean: en edad, peso y altura no significan nada.
  const soloNumeros = (e) => {
    if (['e', 'E', '+', '-'].includes(e.key)) e.preventDefault();
  };

  const save = async (e) => {
    e.preventDefault();
    try {
      const actualizado = await profileApi.update({
        email: user.email,
        edad: edad === '' ? null : Number(edad),
        peso: peso === '' ? null : Number(peso),
        altura: altura === '' ? null : Number(altura),
        meta,
      });
      setDatos(actualizado);
      showToast('Perfil actualizado.', 'success');
    } catch (err) { showToast(err.message, 'error'); }
  };

  const inasistenciasRestantes = reporte?.inasistencias_restantes ?? datos?.inasistencias_restantes ?? 0;
  const penalizado = (reporte?.estado ?? datos?.estado) === 'PENALIZADO';

  return (
    <div className="perfil">
      <h2 className="perfil__titulo">Mi perfil</h2>
      <p className="perfil__subtitulo">Datos de tu cuenta en el sistema de reservas</p>

      {/* Nombre, documento de identidad y rol asignado (todos los roles) */}
      <div className="perfil__tarjeta">
        <h3 className="perfil__seccion">🪪 Mis datos</h3>
        <Dato label="Nombre" valor={datos?.name ?? user.name} />
        <Dato label="Correo institucional" valor={datos?.email ?? user.email} />
        <Dato label="Documento de identidad" valor={datos?.documento || user.documento || '—'} />
        <Dato
          label="Rol asignado"
          valor={ROLE_LABEL[datos?.role ?? user.role] || (datos?.role ?? user.role)}
          extra={datos?.es_principal ? 'Administrador principal' : null}
        />
        <Dato label="Estado de la cuenta" valor={datos?.estado ?? user.estado} />
      </div>

      {/* Mis inasistencias y penalizaciones */}
      {esEstudiante && reporte && (
        <div className={`perfil__tarjeta${penalizado ? ' perfil__tarjeta--penalizado' : ''}`}>
          <h3 className="perfil__seccion">🚦 Mis inasistencias y penalizaciones</h3>
          <p className="perfil__nota">
            La cuenta se penaliza al llegar a {reporte.no_show_limite} inasistencias.
          </p>
          <div className="perfil__contadores">
            <Contador
              label="Inasistencias"
              value={reporte.no_show_count}
              sub={`de ${reporte.no_show_limite} permitidas`}
              alerta={reporte.no_show_count > 0}
            />
            <Contador
              label="Me faltan"
              value={inasistenciasRestantes}
              sub="para la penalización"
              alerta={inasistenciasRestantes <= 2}
            />
            <Contador
              label="Asistencias"
              value={reporte.total_asistencias}
              sub="entrenamientos cumplidos"
            />
          </div>

          {penalizado ? (
            <div className="perfil__aviso perfil__aviso--bloqueado">
              🚫 Tu cuenta está <strong>PENALIZADA</strong> y no puedes reservar
              {reporte.penalizado_hasta ? ` hasta el ${reporte.penalizado_hasta}` : ''}.
            </div>
          ) : reporte.alerta_inasistencias && (
            <div className="perfil__aviso perfil__aviso--atencion">
              ⚠️ {reporte.alerta_inasistencias}
            </div>
          )}

          {reporte.inasistencias.length > 0 && (
            <div className="perfil__detalle">
              <p className="perfil__detalle-titulo">Detalle de mis inasistencias</p>
              {reporte.inasistencias.map((i) => (
                <div key={i.id} className="perfil__detalle-fila">
                  <span className="perfil__detalle-hora">{i.hour}</span>
                  <span className="perfil__detalle-fecha">{i.date}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Cancelaciones acumuladas. Es solo informativo: cancelar no penaliza
          la cuenta ni cuenta como inasistencia. */}
      {esEstudiante && datos && (
        <div className="perfil__tarjeta">
          <h3 className="perfil__seccion">📊 Mis cancelaciones</h3>
          <p className="perfil__nota">
            Cancelar a tiempo devuelve el cupo a otro compañero y no penaliza tu cuenta.
            Este contador es solo informativo.
          </p>
          <div className="perfil__contadores">
            <Contador
              label="Veces que he cancelado"
              value={datos.cancel_count}
              sub="no afectan a tu cuenta"
            />
            <Contador
              label="Inasistencias"
              value={datos.no_show_count}
              sub={`de ${datos.no_show_limite} permitidas`}
              alerta={datos.no_show_count > 0}
            />
          </div>
        </div>
      )}

      {/* Información personal de entrenamiento (solo estudiantes) */}
      {esEstudiante ? (
        <form className="perfil__tarjeta perfil__formulario" onSubmit={save}>
          <div>
            <h3 className="perfil__seccion">🏋️ Mi información de entrenamiento</h3>
            <p className="perfil__nota">
              Mantén actualizados tu edad, peso, altura y objetivo.
            </p>
          </div>
          <div>
            <label className="perfil__etiqueta">Edad (años)</label>
            <input className="perfil__entrada" type="number" min="10" max="100" step="1"
                   value={edad} onKeyDown={soloNumeros}
                   onChange={(e) => setEdad(e.target.value)} />
            <p className="perfil__ayuda">Entre 10 y 100 años.</p>
          </div>
          <div>
            <label className="perfil__etiqueta">Peso (kg)</label>
            <input className="perfil__entrada" type="number" min="20" max="300" step="0.1"
                   value={peso} onKeyDown={soloNumeros}
                   onChange={(e) => setPeso(e.target.value)} />
            <p className="perfil__ayuda">Entre 20 y 300 kg.</p>
          </div>
          <div>
            <label className="perfil__etiqueta">Altura (cm)</label>
            <input className="perfil__entrada" type="number" min="100" max="250" step="1"
                   value={altura} onKeyDown={soloNumeros}
                   onChange={(e) => setAltura(e.target.value)} />
            <p className="perfil__ayuda">Entre 100 y 250 cm.</p>
          </div>
          <div>
            <label className="perfil__etiqueta">Objetivo de entrenamiento</label>
            <input className="perfil__entrada" type="text" value={meta} maxLength={120}
                   onChange={(e) => setMeta(e.target.value)} placeholder="Ej: Ganar resistencia" />
          </div>
          <button className="perfil__guardar" type="submit">Guardar perfil</button>
        </form>
      ) : (
        <div className="perfil__tarjeta">
          <p className="perfil__explicacion">
            Los entrenadores y administradores consultan aquí su nombre, documento de identidad
            y rol asignado. La información de entrenamiento (edad, peso, altura y objetivo) es
            exclusiva del perfil del estudiante.
          </p>
        </div>
      )}
    </div>
  );
}

function Dato({ label, valor, extra }) {
  return (
    <div className="dato">
      <span className="dato__etiqueta">{label}</span>
      <span className="dato__valor">
        {valor || '—'}
        {extra && <span className="dato__extra">{extra}</span>}
      </span>
    </div>
  );
}

function Contador({ label, value, sub, alerta }) {
  return (
    <div className={`contador${alerta ? ' contador--alerta' : ''}`}>
      <p className="contador__valor">{value}</p>
      <p className="contador__label">{label}</p>
      <p className="contador__sub">{sub}</p>
    </div>
  );
}
