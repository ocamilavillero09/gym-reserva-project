"""
Asistencia, inasistencias, penalizaciones y reportes del sistema.

  RF11 / P11 / HU11  Buscar la reserva de un estudiante por su DOCUMENTO
  RF13 / P13 / HU12  Registrar la asistencia del estudiante
  RF14 / P14 / HU13-HU15  Estudiantes con reserva y sin asistencia registrada
  RF15 / P15 / HU14-HU16  Procesar de forma GENERAL las inasistencias
  RF16 / P16         Penalización al alcanzar CINCO (5) inasistencias
  RF18 / P18 / HU08  Reporte personal de inasistencias y penalizaciones
  RF19 / P19 / HU17-HU18  Reporte GENERAL DIARIO del gimnasio
"""
from datetime import datetime

from bson import ObjectId
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .db import (
    get_db, add_business_days, hoy_local, formato_fecha_es, normalizar_documento,
    inasistencias_restantes, alerta_inasistencias, cancelaciones_restantes,
    NO_SHOW_LIMITE, CANCELACION_LIMITE, PENALIZACION_DIAS_HABILES,
)

ROLES_STAFF = ('ENTRENADOR', 'ADMIN')


def _actor_staff(email: str):
    """Devuelve el ENTRENADOR/ADMIN que ejecuta la acción, o None si no lo es."""
    user = get_db().users.find_one({'email': (email or '').strip().lower()})
    return user if user and user.get('role') in ROLES_STAFF else None


def _fecha_jornada(request) -> str:
    """Fecha ISO de la jornada consultada. Por defecto, HOY."""
    pedida = (request.query_params.get('fecha') if request.method == 'GET'
              else request.data.get('fecha'))
    return (pedida or '').strip() or hoy_local().isoformat()


def _fecha_label(fecha_iso: str) -> str:
    try:
        y, m, d = (int(x) for x in fecha_iso.split('-'))
        from datetime import date as _date
        return formato_fecha_es(_date(y, m, d))
    except Exception:
        return fecha_iso


def aplicar_inasistencia(email: str):
    """RF16 — Suma una inasistencia y penaliza al llegar al límite de CINCO (5).

    Devuelve (usuario_actualizado, penalizado_ahora).
    """
    db = get_db()
    owner = db.users.find_one_and_update(
        {'email': email}, {'$inc': {'no_show_count': 1}}, return_document=True,
    )
    if not owner:
        return None, False
    penalizado = False
    if owner.get('no_show_count', 0) >= NO_SHOW_LIMITE and owner.get('estado') != 'PENALIZADO':
        hasta = add_business_days(datetime.utcnow(), PENALIZACION_DIAS_HABILES)
        db.users.update_one(
            {'email': email},
            {'$set': {'estado': 'PENALIZADO', 'penalizado_hasta': hasta,
                      'penalizado_at': datetime.utcnow()}},
        )
        owner['estado'] = 'PENALIZADO'
        penalizado = True
    return owner, penalizado


def _fila_estudiante(user: dict) -> dict:
    return {
        'name': user.get('name'),
        'email': user.get('email'),
        'documento': user.get('documento', ''),
        'estado': user.get('estado', 'ACTIVO'),
        'no_show_count': user.get('no_show_count', 0),
        'inasistencias_restantes': inasistencias_restantes(user),
        'no_show_limite': NO_SHOW_LIMITE,
    }


# ── RF11 / HU11 — BUSCAR AL ESTUDIANTE POR SU DOCUMENTO DE IDENTIDAD ────────
@api_view(['GET'])
def student_lookup(request):
    """El entrenador busca a un estudiante por su documento y ve su reserva.

    Parámetros: ?documento=1001234567&actor_email=coach@udem.edu.co
    Devuelve los datos del estudiante y sus reservas ACTIVAS (con la del día
    de la jornada marcada), para poder registrarle la asistencia (RF13).
    """
    if not _actor_staff(request.query_params.get('actor_email')):
        return Response(
            {'error': 'Solo un entrenador o administrador puede consultar reservas de estudiantes.'},
            status=403,
        )

    documento = normalizar_documento(request.query_params.get('documento'))
    if not documento:
        return Response({'error': 'Debes indicar el documento de identidad.'}, status=400)

    db = get_db()
    student = db.users.find_one({'documento': documento, 'role': 'ESTUDIANTE'})
    if not student:
        return Response(
            {'error': f'No hay ningún estudiante registrado con el documento {documento}.'},
            status=404,
        )

    hoy = hoy_local().isoformat()
    reservas = [{
        'id': str(r['_id']), 'slotId': r['slotId'], 'hour': r['hour'],
        'date': r.get('date'), 'reserva_date': r.get('reserva_date'),
        'estado': r.get('estado'),
        'es_de_hoy': r.get('reserva_date') == hoy,
    } for r in db.reservations.find({'email': student['email'], 'estado': 'ACTIVA'}).sort('reserva_date', 1)]

    return Response({
        'estudiante': _fila_estudiante(student),
        'reservas': reservas,
        'tiene_reserva': len(reservas) > 0,
        'fecha_jornada': hoy,
    })


# ── RF13 / HU12 — REGISTRAR LA ASISTENCIA DEL ESTUDIANTE ───────────────────
@api_view(['POST'])
def register_attendance(request):
    """Registra la asistencia de un estudiante que TIENE una reserva.

    Cuerpo: {actor_email, documento} o {actor_email, reservation_id}.
    Con documento se toma su reserva activa de la jornada de hoy.
    """
    actor = _actor_staff(request.data.get('actor_email'))
    if not actor:
        return Response(
            {'error': 'Solo un entrenador o administrador puede registrar asistencias.'},
            status=403,
        )

    db = get_db()
    filtro = {'estado': 'ACTIVA'}
    reservation_id = request.data.get('reservation_id')

    if reservation_id:
        try:
            filtro['_id'] = ObjectId(reservation_id)
        except Exception:
            return Response({'error': 'ID de reserva inválido.'}, status=400)
    else:
        documento = normalizar_documento(request.data.get('documento'))
        if not documento:
            return Response(
                {'error': 'Debes indicar el documento de identidad o el id de la reserva.'},
                status=400,
            )
        student = db.users.find_one({'documento': documento, 'role': 'ESTUDIANTE'})
        if not student:
            return Response(
                {'error': f'No hay ningún estudiante registrado con el documento {documento}.'},
                status=404,
            )
        filtro['email'] = student['email']
        filtro['reserva_date'] = _fecha_jornada(request)

    reserva = db.reservations.find_one_and_update(
        filtro,
        {'$set': {'estado': 'COMPLETADA', 'completed_at': datetime.utcnow(),
                  'asistencia_registrada_por': actor['email']}},
    )
    if reserva is None:
        return Response(
            {'error': 'El estudiante no tiene una reserva activa para registrar asistencia.'},
            status=404,
        )

    return Response({
        'message': 'Asistencia registrada.',
        'notificacion': f"Asistencia registrada para las {reserva['hour']} del {reserva.get('date', '')}.",
        'reservation_id': str(reserva['_id']),
        'email': reserva['email'],
        'hour': reserva['hour'],
    })


# ── RF14 / HU13 / HU15 — ESTUDIANTES SIN ASISTENCIA REGISTRADA ─────────────
@api_view(['GET'])
def pending_attendance(request):
    """Reservas de la jornada que siguen ACTIVAS: nadie les registró asistencia.

    Se incluyen las de la fecha consultada y las de días anteriores que
    quedaron sin procesar. Las reservas de días futuros NO aparecen: todavía
    no ha llegado su jornada.
    """
    if not _actor_staff(request.query_params.get('actor_email')):
        return Response(
            {'error': 'Solo un entrenador o administrador puede consultar las inasistencias.'},
            status=403,
        )

    fecha = _fecha_jornada(request)
    db = get_db()
    pendientes = []
    for r in db.reservations.find(
        {'estado': 'ACTIVA', 'reserva_date': {'$lte': fecha}}
    ).sort('reserva_date', 1):
        student = db.users.find_one({'email': r['email']}) or {}
        pendientes.append({
            'id': str(r['_id']),
            'name': student.get('name', r['email']),
            'email': r['email'],
            'documento': student.get('documento', ''),
            'hour': r['hour'],
            'slotId': r['slotId'],
            'date': r.get('date'),
            'reserva_date': r.get('reserva_date'),
            'no_show_count': student.get('no_show_count', 0),
            'inasistencias_restantes': inasistencias_restantes(student),
        })

    return Response({
        'fecha': fecha,
        'fecha_label': _fecha_label(fecha),
        'no_show_limite': NO_SHOW_LIMITE,
        'total': len(pendientes),
        'pendientes': pendientes,
    })


# ── RF15 / HU14 / HU16 — PROCESAR DE FORMA GENERAL LAS INASISTENCIAS ───────
@api_view(['POST'])
def process_no_shows(request):
    """Cierra la jornada: toda reserva sin asistencia queda como inasistencia.

    Cuerpo: {actor_email, fecha?}. Marca NO_SHOW cada reserva ACTIVA de la
    jornada, suma la inasistencia a cada estudiante y aplica la penalización
    a quienes lleguen a CINCO (5) inasistencias (RF16).
    """
    actor = _actor_staff(request.data.get('actor_email'))
    if not actor:
        return Response(
            {'error': 'Solo un entrenador o administrador puede procesar las inasistencias.'},
            status=403,
        )

    fecha = _fecha_jornada(request)
    db = get_db()
    procesados, penalizados = [], []

    while True:
        # Se toma una reserva a la vez con find_one_and_update: la transición
        # ACTIVA -> NO_SHOW es atómica, así dos entrenadores que cierren la
        # jornada al mismo tiempo no cuentan dos veces la misma inasistencia.
        reserva = db.reservations.find_one_and_update(
            {'estado': 'ACTIVA', 'reserva_date': {'$lte': fecha}},
            {'$set': {'estado': 'NO_SHOW', 'no_show_at': datetime.utcnow(),
                      'procesado_por': actor['email']}},
        )
        if reserva is None:
            break

        owner, penalizado = aplicar_inasistencia(reserva['email'])
        procesados.append({
            'email': reserva['email'],
            'name': (owner or {}).get('name', reserva['email']),
            'documento': (owner or {}).get('documento', ''),
            'hour': reserva['hour'],
            'date': reserva.get('date'),
            'no_show_count': (owner or {}).get('no_show_count', 0),
            'inasistencias_restantes': inasistencias_restantes(owner),
            'penalizado': penalizado,
        })
        if penalizado:
            penalizados.append((owner or {}).get('name', reserva['email']))

    mensaje = (f'No había inasistencias pendientes para el {_fecha_label(fecha)}.'
               if not procesados else
               f'Se procesaron {len(procesados)} inasistencias del {_fecha_label(fecha)}.')
    if penalizados:
        mensaje += f" Estudiantes penalizados: {', '.join(penalizados)}."

    return Response({
        'message': mensaje,
        'fecha': fecha,
        'fecha_label': _fecha_label(fecha),
        'total_procesadas': len(procesados),
        'total_penalizados': len(penalizados),
        'no_show_limite': NO_SHOW_LIMITE,
        'procesados': procesados,
    })


# ── RF18 / HU08 — REPORTE PERSONAL DE INASISTENCIAS Y PENALIZACIONES ───────
@api_view(['GET'])
def personal_report(request):
    """Lo que el estudiante ve de sí mismo: inasistencias y penalizaciones."""
    email = request.query_params.get('email', '').strip().lower()
    if not email:
        return Response({'error': 'Parámetro email requerido.'}, status=400)

    db = get_db()
    user = db.users.find_one({'email': email})
    if not user:
        return Response({'error': 'Usuario no encontrado.'}, status=404)

    inasistencias = [{
        'id': str(r['_id']), 'hour': r['hour'], 'date': r.get('date'),
        'reserva_date': r.get('reserva_date'),
    } for r in db.reservations.find({'email': email, 'estado': 'NO_SHOW'}).sort('reserva_date', -1)]

    penalizado_hasta = user.get('penalizado_hasta')
    return Response({
        'name': user.get('name'),
        'email': email,
        'documento': user.get('documento', ''),
        'estado': user.get('estado', 'ACTIVO'),
        # RF16/RF18 — inasistencias y cuántas faltan para la penalización.
        'no_show_count': user.get('no_show_count', 0),
        'no_show_limite': NO_SHOW_LIMITE,
        'inasistencias_restantes': inasistencias_restantes(user),
        'alerta_inasistencias': alerta_inasistencias(user),
        'penalizado': user.get('estado') == 'PENALIZADO',
        'penalizado_hasta': penalizado_hasta.isoformat() if penalizado_hasta else None,
        # Contexto de cancelaciones (RN10).
        'cancel_count': user.get('cancel_count', 0),
        'cancelacion_limite': CANCELACION_LIMITE,
        'cancelaciones_restantes': cancelaciones_restantes(user),
        'inasistencias': inasistencias,
        'total_asistencias': db.reservations.count_documents({'email': email, 'estado': 'COMPLETADA'}),
        'total_cancelaciones': db.reservations.count_documents({'email': email, 'estado': 'CANCELADA'}),
    })


# ── RF19 / HU17 / HU18 — REPORTE GENERAL DIARIO DEL GIMNASIO ───────────────
def build_daily_report(fecha_iso: str) -> dict:
    """Totales del día: asistencias, cancelaciones e inasistencias.

    Lo usan tanto la consulta en pantalla (RF19) como el PDF (RF20).
    """
    db = get_db()
    del_dia = {'reserva_date': fecha_iso}

    def _detalle(estado):
        filas = []
        for r in db.reservations.find({**del_dia, 'estado': estado}).sort('hour', 1):
            u = db.users.find_one({'email': r['email']}) or {}
            filas.append({
                'name': u.get('name', r['email']), 'email': r['email'],
                'documento': u.get('documento', ''), 'hour': r['hour'],
            })
        return filas

    asistencias   = _detalle('COMPLETADA')
    cancelaciones = _detalle('CANCELADA')
    inasistencias = _detalle('NO_SHOW')
    pendientes    = _detalle('ACTIVA')

    penalizados = [{
        'name': u.get('name'), 'email': u['email'],
        'documento': u.get('documento', ''),
        'no_show_count': u.get('no_show_count', 0),
        'cancel_count': u.get('cancel_count', 0),
        'penalizado_hasta': (u['penalizado_hasta'].date().isoformat()
                             if u.get('penalizado_hasta') else None),
    } for u in db.users.find({'role': 'ESTUDIANTE', 'estado': 'PENALIZADO'}).sort('name', 1)]

    # Ocupación por bloque horario del día (RF07 aplicado al reporte).
    bloques = []
    for s in db.slots.find().sort('slotId', 1):
        reservados = db.reservations.count_documents(
            {**del_dia, 'slotId': s['slotId'], 'estado': {'$in': ['ACTIVA', 'COMPLETADA', 'NO_SHOW']}}
        )
        bloques.append({
            'slotId': s['slotId'], 'hour': s['hour'], 'total': s['total'],
            'reservados': reservados,
            'asistencias': db.reservations.count_documents({**del_dia, 'slotId': s['slotId'], 'estado': 'COMPLETADA'}),
            'inasistencias': db.reservations.count_documents({**del_dia, 'slotId': s['slotId'], 'estado': 'NO_SHOW'}),
        })

    return {
        'fecha': fecha_iso,
        'fecha_label': _fecha_label(fecha_iso),
        'totales': {
            'reservas': db.reservations.count_documents(del_dia),
            'asistencias': len(asistencias),
            'cancelaciones': len(cancelaciones),
            'inasistencias': len(inasistencias),
            'pendientes': len(pendientes),
            'estudiantes_penalizados': len(penalizados),
        },
        'asistencias': asistencias,
        'cancelaciones': cancelaciones,
        'inasistencias': inasistencias,
        'pendientes': pendientes,
        'penalizados': penalizados,
        'bloques': bloques,
        'no_show_limite': NO_SHOW_LIMITE,
    }


@api_view(['GET'])
def daily_report(request):
    """Reporte general diario para entrenadores y administradores (RF19)."""
    if not _actor_staff(request.query_params.get('actor_email')):
        return Response(
            {'error': 'Solo un entrenador o administrador puede consultar el reporte general.'},
            status=403,
        )
    return Response(build_daily_report(_fecha_jornada(request)))
