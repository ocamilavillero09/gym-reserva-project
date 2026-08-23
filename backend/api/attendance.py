"""
FUNCIONALIDADES DE ASISTENCIA, INASISTENCIAS Y REPORTES

Este archivo expone la API de la jornada del gimnasio. No consulta MongoDB
directamente ni define límites propios: llama a `datos.py` para leer y escribir
y a `reglas.py` para saber cuándo corresponde penalizar una cuenta.

REQUISITOS EN USO EN ESTE ARCHIVO (con pruebas en tests.py)
    RF11  Búsqueda del estudiante por su documento de identidad
    RF13  Registro de la asistencia del estudiante
    RF16  Penalización al alcanzar cinco inasistencias
    RF18  Reporte personal de inasistencias y penalizaciones

REQUISITOS IGNORADOS EN ESTE ARCHIVO
    Están implementados y funcionan, pero quedaron fuera del alcance acordado
    con el equipo: no se diseñaron escenarios ni casos de prueba para ellos.
    RF14  Estudiantes con reserva y sin asistencia registrada
    RF15  Procesamiento general de las inasistencias de la jornada
    RF19  Reporte general diario del gimnasio

`process_no_shows` atiende a dos requisitos a la vez: RF15 recorre la jornada y
RF16 decide qué pasa con cada inasistencia. Sobre la función se detalla qué le
toca a cada uno.
"""
from datetime import date as _date, datetime

from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import datos, reglas


def _actor_staff(email: str):
    """Devuelve el ENTRENADOR o ADMIN que ejecuta la acción, o None si no lo es."""
    user = datos.buscar_usuario(reglas.normalizar_correo(email))
    return user if reglas.es_staff(user) else None


def _fecha_jornada(request) -> str:
    """Fecha de la jornada consultada. Por defecto, HOY."""
    pedida = (request.query_params.get('fecha') if request.method == 'GET'
              else request.data.get('fecha'))
    return (pedida or '').strip() or reglas.hoy_local().isoformat()


def _fecha_label(fecha_iso: str) -> str:
    """Convierte '2026-08-20' en 'jueves 20 de agosto de 2026'."""
    try:
        y, m, d = (int(x) for x in fecha_iso.split('-'))
        return reglas.formato_fecha_es(_date(y, m, d))
    except Exception:
        return fecha_iso


def aplicar_inasistencia(email: str):
    """Suma una inasistencia y penaliza la cuenta al llegar al límite.

    Es la única puerta por la que se registra una inasistencia, para que el
    registro individual y el procesamiento general de la jornada apliquen
    exactamente la misma regla. Devuelve (usuario_actualizado, penalizado_ahora).
    """
    owner = datos.sumar_a_contador(email, 'no_show_count')
    if not owner:
        return None, False
    penalizado = False
    if reglas.alcanza_limite_inasistencias(owner) and owner.get('estado') != 'PENALIZADO':
        datos.actualizar_usuario(email, {
            'estado': 'PENALIZADO',
            'penalizado_hasta': reglas.fin_de_penalizacion(),
            'penalizado_at': datetime.utcnow(),
        })
        owner['estado'] = 'PENALIZADO'
        penalizado = True
    return owner, penalizado


def _reserva_futura(filtro: dict):
    """Busca la reserva que el filtro descartó por ser de una jornada futura."""
    sin_fecha = {k: v for k, v in filtro.items() if k != 'reserva_date'}
    hoy = reglas.hoy_local().isoformat()
    futuras = datos.listar_reservas({**sin_fecha, 'reserva_date': {'$gt': hoy}}, 'reserva_date', 1)
    return futuras[0] if futuras else None


def _fila_estudiante(user: dict) -> dict:
    """Los datos del estudiante que ve el personal del gimnasio."""
    return {
        'name': user.get('name'),
        'email': user.get('email'),
        'documento': user.get('documento', ''),
        'estado': user.get('estado', 'ACTIVO'),
        'no_show_count': user.get('no_show_count', 0),
        'inasistencias_restantes': reglas.inasistencias_restantes(user),
        'no_show_limite': reglas.NO_SHOW_LIMITE,
    }


# ── RF11 · Búsqueda del estudiante por su documento ───────────
@api_view(['GET'])
def student_lookup(request):
    """El entrenador busca a un estudiante por su documento y ve su reserva.

    Parámetros: ?documento=1001234567&actor_email=coach@udem.edu.co
    Devuelve los datos del estudiante y sus reservas ACTIVAS (con la del día
    de la jornada marcada), para poder registrarle la asistencia.
    """
    if not _actor_staff(request.query_params.get('actor_email')):
        return Response(
            {'error': 'Solo un entrenador o administrador puede consultar reservas de estudiantes.'},
            status=403,
        )

    documento = reglas.normalizar_documento(request.query_params.get('documento'))
    if not documento:
        return Response({'error': 'Debes indicar el documento de identidad.'}, status=400)

    student = datos.buscar_estudiante_por_documento(documento)
    if not student:
        return Response(
            {'error': f'No hay ningún estudiante registrado con el documento {documento}.'},
            status=404,
        )

    hoy = reglas.hoy_local().isoformat()
    reservas = [{
        'id': str(r['_id']), 'slotId': r['slotId'], 'hour': r['hour'],
        'date': r.get('date'), 'reserva_date': r.get('reserva_date'),
        'estado': r.get('estado'),
        'es_de_hoy': r.get('reserva_date') == hoy,
        # La recepción necesita saber si ya puede marcar la asistencia.
        'se_puede_registrar': reglas.jornada_ya_llegada(r.get('reserva_date')),
    } for r in datos.reservas_activas_ordenadas(student['email'])]

    return Response({
        'estudiante': _fila_estudiante(student),
        'reservas': reservas,
        'tiene_reserva': len(reservas) > 0,
        'fecha_jornada': hoy,
    })


# ── RF13 · Registro de la asistencia del estudiante ───────────
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

    # La jornada de la reserva tiene que haber llegado: si la reserva es para
    # mañana, el estudiante todavía no ha podido presentarse.
    hoy = reglas.hoy_local().isoformat()
    filtro = {'estado': 'ACTIVA', 'reserva_date': {'$lte': hoy}}
    reservation_id = request.data.get('reservation_id')

    if reservation_id:
        oid = datos.a_object_id(reservation_id)
        if oid is None:
            return Response({'error': 'ID de reserva inválido.'}, status=400)
        filtro['_id'] = oid
    else:
        documento = reglas.normalizar_documento(request.data.get('documento'))
        if not documento:
            return Response(
                {'error': 'Debes indicar el documento de identidad o el id de la reserva.'},
                status=400,
            )
        student = datos.buscar_estudiante_por_documento(documento)
        if not student:
            return Response(
                {'error': f'No hay ningún estudiante registrado con el documento {documento}.'},
                status=404,
            )
        filtro['email'] = student['email']

    reserva = datos.marcar_asistencia(filtro, actor['email'])
    if reserva is None:
        # Se distingue entre «no hay reserva» y «la reserva todavía no toca»,
        # que son dos situaciones muy distintas para quien está en recepción.
        futura = _reserva_futura(filtro)
        if futura:
            return Response(
                {'error': f"La reserva de este estudiante es para el {futura.get('date')}. "
                          'La asistencia solo puede registrarse el día de la reserva.'},
                status=409,
            )
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


# ── RF14 · [IGNORADO] Estudiantes sin asistencia registrada ─────────────
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
    pendientes = []
    for r in datos.listar_reservas(
            {'estado': 'ACTIVA', 'reserva_date': {'$lte': fecha}}, 'reserva_date', 1):
        student = datos.buscar_usuario(r['email']) or {}
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
            'inasistencias_restantes': reglas.inasistencias_restantes(student),
        })

    return Response({
        'fecha': fecha,
        'fecha_label': _fecha_label(fecha),
        'no_show_limite': reglas.NO_SHOW_LIMITE,
        'total': len(pendientes),
        'pendientes': pendientes,
    })


# ── RF15 · [IGNORADO] Procesamiento general de las inasistencias ────────
# ── RF16 · Penalización al alcanzar cinco inasistencias ──────
#
# QUÉ LE TOCA A CADA REQUISITO
#   RF15 · EL RECORRIDO. Cerrar la jornada: tomar una a una las reservas que
#          quedaron ACTIVAS ese día —nadie registró su asistencia— y marcarlas
#          como NO_SHOW. Es el bucle de abajo.
#   RF16 · LA CONSECUENCIA. Qué ocurre con cada inasistencia: se suma al
#          contador del estudiante y, al llegar al límite de cinco, la cuenta
#          queda penalizada. Esa parte vive en `aplicar_inasistencia`, que se
#          llama desde aquí y también desde el marcado individual (views.mark_no_show).
@api_view(['POST'])
def process_no_shows(request):
    """Cierra la jornada: toda reserva sin asistencia queda como inasistencia.

    Cuerpo: {actor_email, fecha?}. Marca NO_SHOW cada reserva ACTIVA de la
    jornada, suma la inasistencia a cada estudiante y aplica la penalización
    a quienes lleguen al límite establecido.
    """
    actor = _actor_staff(request.data.get('actor_email'))
    if not actor:
        return Response(
            {'error': 'Solo un entrenador o administrador puede procesar las inasistencias.'},
            status=403,
        )

    # Nunca se cierra una jornada futura: esas reservas todavía se pueden
    # cumplir, así que marcarlas como inasistencia sería injusto.
    fecha = reglas.limitar_a_hoy(_fecha_jornada(request))
    procesados, penalizados = [], []

    while True:
        # RF15 · Se toma una reserva a la vez de forma atómica: dos entrenadores
        # que cierren la jornada al mismo tiempo no cuentan dos veces la misma
        # inasistencia.
        reserva = datos.tomar_reserva_pendiente(fecha, actor['email'])
        if reserva is None:
            break

        # RF16 · Suma la inasistencia y penaliza la cuenta si llegó al límite.
        owner, penalizado = aplicar_inasistencia(reserva['email'])
        procesados.append({
            'email': reserva['email'],
            'name': (owner or {}).get('name', reserva['email']),
            'documento': (owner or {}).get('documento', ''),
            'hour': reserva['hour'],
            'date': reserva.get('date'),
            'no_show_count': (owner or {}).get('no_show_count', 0),
            'inasistencias_restantes': reglas.inasistencias_restantes(owner),
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
        'no_show_limite': reglas.NO_SHOW_LIMITE,
        'procesados': procesados,
    })


# ── RF18 · Reporte personal de inasistencias y penalizaciones ───────────
@api_view(['GET'])
def personal_report(request):
    """Lo que el estudiante ve de sí mismo: inasistencias y penalizaciones."""
    email = reglas.normalizar_correo(request.query_params.get('email'))
    if not email:
        return Response({'error': 'Parámetro email requerido.'}, status=400)

    user = datos.buscar_usuario(email)
    if not user:
        return Response({'error': 'Usuario no encontrado.'}, status=404)

    inasistencias = [{
        'id': str(r['_id']), 'hour': r['hour'], 'date': r.get('date'),
        'reserva_date': r.get('reserva_date'),
    } for r in datos.listar_reservas({'email': email, 'estado': 'NO_SHOW'}, 'reserva_date', -1)]

    penalizado_hasta = user.get('penalizado_hasta')
    return Response({
        'name': user.get('name'),
        'email': email,
        'documento': user.get('documento', ''),
        'estado': user.get('estado', 'ACTIVO'),
        # Inasistencias acumuladas y cuántas faltan para la penalización.
        'no_show_count': user.get('no_show_count', 0),
        'no_show_limite': reglas.NO_SHOW_LIMITE,
        'inasistencias_restantes': reglas.inasistencias_restantes(user),
        'alerta_inasistencias': reglas.alerta_inasistencias(user),
        'penalizado': user.get('estado') == 'PENALIZADO',
        'penalizado_hasta': penalizado_hasta.isoformat() if penalizado_hasta else None,
        # Cancelaciones: se informan aparte porque NO son inasistencias ni
        # penalizan la cuenta.
        'cancel_count': user.get('cancel_count', 0),
        'inasistencias': inasistencias,
        'total_asistencias': datos.contar_reservas({'email': email, 'estado': 'COMPLETADA'}),
        'total_cancelaciones': datos.contar_reservas({'email': email, 'estado': 'CANCELADA'}),
    })


# ── RF19 · [IGNORADO] Reporte general diario del gimnasio ───────────────
def build_daily_report(fecha_iso: str) -> dict:
    """Totales del día: asistencias, cancelaciones e inasistencias.

    Lo usan tanto la consulta en pantalla como la exportación a PDF.
    """
    del_dia = {'reserva_date': fecha_iso}

    def _detalle(estado):
        filas = []
        for r in datos.listar_reservas({**del_dia, 'estado': estado}, 'hour', 1):
            u = datos.buscar_usuario(r['email']) or {}
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
    } for u in datos.listar_estudiantes_penalizados()]

    # Ocupación por bloque horario del día.
    bloques = []
    for s in datos.listar_bloques():
        reservados = datos.contar_reservas(
            {**del_dia, 'slotId': s['slotId'], 'estado': {'$in': ['ACTIVA', 'COMPLETADA', 'NO_SHOW']}})
        bloques.append({
            'slotId': s['slotId'], 'hour': s['hour'], 'total': s['total'],
            'reservados': reservados,
            'asistencias': datos.contar_reservas({**del_dia, 'slotId': s['slotId'], 'estado': 'COMPLETADA'}),
            'inasistencias': datos.contar_reservas({**del_dia, 'slotId': s['slotId'], 'estado': 'NO_SHOW'}),
        })

    return {
        'fecha': fecha_iso,
        'fecha_label': _fecha_label(fecha_iso),
        'totales': {
            'reservas': datos.contar_reservas(del_dia),
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
        'no_show_limite': reglas.NO_SHOW_LIMITE,
    }


@api_view(['GET'])
def daily_report(request):
    """Reporte general diario para entrenadores y administradores."""
    if not _actor_staff(request.query_params.get('actor_email')):
        return Response(
            {'error': 'Solo un entrenador o administrador puede consultar el reporte general.'},
            status=403,
        )
    return Response(build_daily_report(_fecha_jornada(request)))
