"""
PERFIL, HISTORIAL Y AFORO

Como el resto del backend, este archivo no consulta MongoDB directamente ni
define límites propios: se apoya en `datos.py` y en `reglas.py`.

REQUISITOS EN USO EN ESTE ARCHIVO (con pruebas en tests.py)
    RF04  Perfil del estudiante: edad, peso, altura y objetivo   (user_profile)
    RF05  Perfil de entrenadores y administradores               (user_profile)
    RF12  El personal visualiza los bloques y su disponibilidad (occupancy_report)
    RF17  Historial de reservas, cancelaciones y asistencias (reservation_history)

REQUISITOS IGNORADOS EN ESTE ARCHIVO
    Están implementados y funcionan, pero quedaron fuera del alcance acordado
    con el equipo: no se diseñaron escenarios ni casos de prueba para ellos.
    RF07  Cupos ocupados y disponibles de cada bloque      (occupancy_report)

Hay dos funciones que atienden a dos requisitos cada una. No es que estén
mezclados: comparten el mismo dato y se diferencian en un solo punto, que queda
señalado sobre cada función y en las líneas que le corresponden.
    user_profile      RF04 y RF05 -> el mismo perfil; cambia el ROL de la cuenta
    occupancy_report  RF07 y RF12 -> el mismo aforo; cambia QUIÉN lo consulta
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import datos, reglas


# ── RF17 · Historial de reservas, cancelaciones y asistencias ─
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


# ── RF04 · Perfil del estudiante ──────────────────────────────
# ── RF05 · Perfil de entrenadores y administradores ───────────
#
# QUÉ LE TOCA A CADA REQUISITO
# Los dos comparten esta función porque consultar el perfil es idéntico para
# cualquier cuenta: se busca por correo y se devuelven sus datos. Lo que los
# separa es el ROL de quien consulta y, con él, qué información tiene sentido.
#
#   RF04 · ESTUDIANTE.  Además de sus datos de cuenta ve, y puede EDITAR con
#          PUT, su información de entrenamiento: edad, peso, altura y objetivo.
#          También ve sus inasistencias y sus cancelaciones, porque él sí
#          reserva cupos. Es el único rol que usa el método PUT.
#   RF05 · ENTRENADOR y ADMINISTRADOR.  Solo consultan con GET: nombre, correo,
#          documento y el rol que les asignó su dominio (RF03). No tienen datos
#          de entrenamiento ni inasistencias, porque no reservan cupos; esos
#          campos les llegan vacíos o en cero.
#
# Abajo, cada bloque de la respuesta lleva marcado a qué requisito responde.
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

    # RF04 · Solo el estudiante llega aquí: es el único que tiene datos de
    # entrenamiento que actualizar.
    if request.method == 'PUT':
        # El estudiante gestiona edad, peso, altura y objetivo de entrenamiento.
        # El nombre, el correo, el documento y el rol NO se editan desde aquí:
        # identifican a la persona.
        enviados = {campo: request.data.get(campo)
                    for campo in ('edad', 'peso', 'altura', 'meta')
                    if campo in request.data}
        cambios, error = reglas.validar_datos_entrenamiento(enviados)
        if error:
            return Response({'error': error}, status=400)
        if cambios:
            datos.actualizar_usuario(email, cambios)
            user = datos.buscar_usuario(email)

    return Response({
        # RF04 y RF05 · Datos de la cuenta. Los ven todos los roles: nombre,
        # correo, documento de identidad y el rol que les asignó su dominio.
        'name': user['name'], 'email': user['email'],
        'documento': user.get('documento', ''),
        'role': user.get('role'),
        'estado': user.get('estado'),
        # RF05 · Distingue al administrador principal del resto de administradores.
        'es_principal': bool(user.get('es_principal')),
        # RF04 · Inasistencias y cuántas faltan para la penalización. Solo el
        # estudiante reserva, así que para el personal esto siempre va en cero.
        'no_show_count': user.get('no_show_count', 0),
        'inasistencias_restantes': reglas.inasistencias_restantes(user),
        'no_show_limite': reglas.NO_SHOW_LIMITE,
        'alerta_inasistencias': reglas.alerta_inasistencias(user),
        # RF04 · Cuántas veces ha cancelado. Es solo informativo: cancelar no penaliza.
        'cancel_count': user.get('cancel_count', 0),
        # RF04 · Información de entrenamiento: es lo propio del estudiante y lo
        # único editable de todo el perfil.
        'edad': user.get('edad'), 'peso': user.get('peso'),
        'altura': user.get('altura'), 'meta': user.get('meta'),
    })


# ── RF07 · [IGNORADO] Cupos ocupados y disponibles de cada bloque ───────────────────
# ── RF12 · El personal consulta el aforo del gimnasio ───────────────────
#
# QUÉ LE TOCA A CADA REQUISITO
#   RF07 · QUÉ se calcula: de cada bloque, cuántos cupos están reservados,
#          cuántos quedan libres y el porcentaje de ocupación. Son los campos
#          `reservados`, `available` y `ocupacion_pct` de la respuesta.
#   RF12 · QUIÉN lo consulta: entrenadores y administradores, que revisan la
#          disponibilidad para supervisar el aforo pero no reservan. El bloqueo
#          que se lo impide está en `reservations`, no aquí.
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
            # RF07 · El cálculo del aforo: libres, ocupados y su proporción.
            'available': s['total'] - reservados,
            'reservados': reservados,
            'ocupacion_pct': round((reservados / s['total']) * 100) if s['total'] else 0,
        })
    return Response(data)
