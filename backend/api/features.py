"""
PERFIL, HISTORIAL Y AFORO

Como el resto del backend, este archivo no consulta MongoDB directamente ni
define límites propios: se apoya en `datos.py` y en `reglas.py`.

REQUISITOS FUNCIONALES CUBIERTOS EN ESTE ARCHIVO
    RF07  Cupos ocupados y disponibles de cada bloque  (occupancy_report)
    RF12  El personal visualiza los bloques y su disponibilidad (occupancy_report)
    RF17  Historial de reservas, cancelaciones y asistencias (reservation_history)

REQUISITOS FUNCIONALES IGNORADOS EN ESTE ARCHIVO
    Están implementados y funcionan, pero no se diseñaron escenarios ni casos
    de prueba para ellos porque son responsabilidad de otros integrantes.
    RF04  Perfil del estudiante: edad, peso, altura y objetivo
    RF05  Perfil de entrenadores y administradores
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import datos, reglas


# ── RF17 · [IGNORADO] Historial de reservas, cancelaciones y asistencias ─
@api_view(['GET'])
def reservation_history(request):
    """Historial completo del estudiante.

    Incluye TODOS sus movimientos: reservas vigentes, cancelaciones,
    asistencias (COMPLETADA) e inasistencias (NO_SHOW). Con ?solo=pasadas se
    excluyen las reservas todavía activas.
    """
    email = reglas.normalizar_correo(request.query_params.get('email'))
    if not email:
        return Response({'error': 'Parámetro email requerido.'}, status=400)

    filtro = {'email': email}
    if request.query_params.get('solo') == 'pasadas':
        filtro['estado'] = {'$ne': 'ACTIVA'}

    return Response([{
        'id': str(r['_id']), 'slotId': r['slotId'], 'hour': r['hour'],
        'date': r.get('date'), 'reserva_date': r.get('reserva_date'),
        'estado': r.get('estado'),
    } for r in datos.listar_reservas(filtro)])


# ── RF04 · [IGNORADO] Perfil del estudiante ──────────────────────────────
# ── RF05 · [IGNORADO] Perfil de entrenadores y administradores ───────────
@api_view(['GET', 'PUT'])
def user_profile(request):
    if request.method == 'GET':
        email = reglas.normalizar_correo(request.query_params.get('email'))
    else:
        email = reglas.normalizar_correo(request.data.get('email'))
    if not email:
        return Response({'error': 'email requerido.'}, status=400)
    user = datos.buscar_usuario(email)
    if not user:
        return Response({'error': 'Usuario no encontrado.'}, status=404)

    if request.method == 'PUT':
        # El estudiante gestiona edad, peso, altura y objetivo de entrenamiento.
        # El nombre, el correo, el documento y el rol NO se editan desde aquí:
        # identifican a la persona.
        cambios = {campo: request.data.get(campo)
                   for campo in ('edad', 'peso', 'altura', 'meta')
                   if campo in request.data}
        if cambios:
            datos.actualizar_usuario(email, cambios)
            user = datos.buscar_usuario(email)

    return Response({
        # Nombre, documento de identidad y rol asignado.
        'name': user['name'], 'email': user['email'],
        'documento': user.get('documento', ''),
        'role': user.get('role'),
        'estado': user.get('estado'),
        'es_principal': bool(user.get('es_principal')),
        # Inasistencias y cuántas faltan para la penalización.
        'no_show_count': user.get('no_show_count', 0),
        'inasistencias_restantes': reglas.inasistencias_restantes(user),
        'no_show_limite': reglas.NO_SHOW_LIMITE,
        'alerta_inasistencias': reglas.alerta_inasistencias(user),
        # Cuántas veces ha cancelado. Es solo informativo: cancelar no penaliza.
        'cancel_count': user.get('cancel_count', 0),
        # Información personal de entrenamiento.
        'edad': user.get('edad'), 'peso': user.get('peso'),
        'altura': user.get('altura'), 'meta': user.get('meta'),
    })


# ── RF07 · Cupos ocupados y disponibles de cada bloque ───────────────────
# ── RF12 · El personal consulta el aforo del gimnasio ────────────────────
@api_view(['GET'])
def occupancy_report(request):
    """Ocupación de cada bloque horario para entrenadores y administradores.

    Se informa de la jornada que se está reservando (el día siguiente), no del
    acumulado histórico: cada día arranca con el gimnasio entero disponible.
    """
    fecha = (request.query_params.get('fecha') or '').strip() or reglas.fecha_reserva().isoformat()
    ocupados = datos.ocupados_del_dia(fecha)
    data = []
    for s in datos.listar_bloques():
        reservados = ocupados.get(s['slotId'], 0)
        data.append({
            'slotId': s['slotId'], 'hour': s['hour'], 'total': s['total'],
            'fecha': fecha,
            'available': s['total'] - reservados,
            'reservados': reservados,
            'ocupacion_pct': round((reservados / s['total']) * 100) if s['total'] else 0,
        })
    return Response(data)
