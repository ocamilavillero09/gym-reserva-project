from datetime import datetime
from bson import ObjectId
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .db import (
    get_db, seed_slots, hash_password, verify_password, serialize,
    add_business_days, ROLES, DOMINIOS_ROL, role_for_email,
    fecha_reserva, formato_fecha_es, cancelaciones_restantes, alerta_cancelaciones,
    MAX_RESERVAS_POR_DIA, NO_SHOW_LIMITE, CANCELACION_LIMITE, PENALIZACION_DIAS_HABILES,
)


# ══════════════════════════════════════════════════════════════════════════
#  CASOS DE USO CRÍTICOS DEL SISTEMA
#  --------------------------------------------------------------------------
#  Este archivo concentra los 5 casos de uso críticos del sistema de reservas.
#  Cada uno está marcado con un encabezado «CASO DE USO CRÍTICO #N» que explica
#  la regla de negocio que protege y por qué es crítico. Son los flujos que,
#  si fallan, comprometen la integridad de los datos o la seguridad:
#
#    CU-1  Registro con correo institucional      (seguridad / control de acceso)
#    CU-2  Inicio de sesión y verificación de hash (seguridad / credenciales)
#    CU-3  Consulta de cupos en tiempo real        (consistencia de lectura)
#    CU-4  Crear reserva con descuento ATÓMICO     (concurrencia / no sobreventa)
#    CU-5  Cancelar reserva y liberar cupo         (consistencia / no perder cupos)
# ══════════════════════════════════════════════════════════════════════════


def _dominios_texto() -> str:
    """'@soyudemedellin.edu.co (estudiante), @udem.edu.co (profesor), ...'"""
    etiquetas = {'ESTUDIANTE': 'estudiante', 'ENTRENADOR': 'profesor', 'ADMIN': 'administrador'}
    return ', '.join(f'{d} ({etiquetas[r]})' for d, r in DOMINIOS_ROL.items())


def _perfil_sesion(user: dict) -> dict:
    """Datos de sesión que el frontend necesita para pintar la interfaz."""
    return {
        'name':   user['name'],
        'email':  user['email'],
        'role':   user.get('role', 'ESTUDIANTE'),
        'estado': user.get('estado', 'ACTIVO'),
        'cancel_count':  user.get('cancel_count', 0),
        'no_show_count': user.get('no_show_count', 0),
        'cancelaciones_restantes': cancelaciones_restantes(user),
        'cancelacion_limite': CANCELACION_LIMITE,
        'alerta': alerta_cancelaciones(user),
    }


# ──────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────

@swagger_auto_schema(
    method='post',
    operation_description="Registro de usuarios. El rol se deduce del dominio del correo institucional.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['name', 'email', 'password'],
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, example='Juan Pérez'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='juan.perez@soyudemedellin.edu.co'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, example='secreto123'),
        }
    ),
    responses={
        201: openapi.Response('Registro exitoso.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'message': openapi.Schema(type=openapi.TYPE_STRING), 'role': openapi.Schema(type=openapi.TYPE_STRING)})),
        400: openapi.Response('Datos inválidos.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
        409: openapi.Response('Correo ya existe.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
    }
)
@api_view(['POST'])
def register(request):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #1 — REGISTRO CON CORREO INSTITUCIONAL          ║
    # ║ Crítico porque es el control de acceso: solo miembros de la         ║
    # ║ universidad pueden crear cuenta, la contraseña se almacena HASHEADA ║
    # ║ (PBKDF2, nunca en claro) y el correo es único.                      ║
    # ║ RN01 — El ROL SE DEDUCE DEL DOMINIO (tres tipos de correo):         ║
    # ║   @soyudemedellin.edu.co -> ESTUDIANTE                              ║
    # ║   @udem.edu.co           -> ENTRENADOR (profesor)                   ║
    # ║   @udemedellin.edu.co    -> ADMIN                                   ║
    # ║ El cliente NO puede elegir el rol: así nadie se auto-asigna         ║
    # ║ privilegios de profesor o administrador al registrarse.             ║
    # ╚══════════════════════════════════════════════════════════════════╝
    db = get_db()
    name     = request.data.get('name', '').strip()
    email    = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    if not name or not email or not password:
        return Response({'error': 'Todos los campos son obligatorios.'}, status=400)

    if len(password) < 6:
        return Response({'error': 'La contraseña debe tener al menos 6 caracteres.'}, status=400)

    role = role_for_email(email)
    if role is None:
        return Response(
            {'error': f'Debes usar un correo institucional válido: {_dominios_texto()}.'},
            status=400,
        )

    if db.users.find_one({'email': email}):
        return Response({'error': 'Ya existe una cuenta con este correo.'}, status=409)

    db.users.insert_one({
        'name':       name,
        'email':      email,
        'password':   hash_password(password),
        'role':       role,
        'estado':     'ACTIVO',          # RN09: ACTIVO | PENALIZADO | INACTIVO
        'no_show_count': 0,
        'cancel_count':  0,              # RN10: cancelaciones acumuladas
        'penalizado_hasta': None,
        'created_at': datetime.utcnow(),
    })

    return Response({'message': 'Registro exitoso.', 'role': role}, status=201)


@swagger_auto_schema(
    method='post',
    operation_description="Inicio de sesión y validación de credenciales.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'password'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='juan.perez@soyudemedellin.edu.co'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, example='secreto123'),
        }
    ),
    responses={
        200: openapi.Response('Login exitoso.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'name': openapi.Schema(type=openapi.TYPE_STRING), 'email': openapi.Schema(type=openapi.TYPE_STRING)})),
        401: openapi.Response('Credenciales incorrectas.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
    }
)
@api_view(['POST'])
def login(request):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #2 — INICIO DE SESIÓN                          ║
    # ║ Crítico por seguridad: la verificación compara el hash PBKDF2       ║
    # ║ almacenado (verify_password) sin exponer la contraseña, y devuelve  ║
    # ║ un mensaje genérico ante correo o clave incorrectos para no revelar ║
    # ║ si el correo existe (mitiga enumeración de usuarios).               ║
    # ╚══════════════════════════════════════════════════════════════════╝
    db = get_db()
    email    = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    user = db.users.find_one({'email': email})
    if not user or not verify_password(user['password'], password):
        return Response({'error': 'Correo o contraseña incorrectos.'}, status=401)

    # Se devuelve rol, estado y contadores para que el frontend muestre las
    # herramientas de cada perfil y la alerta de cancelaciones (RN10).
    return Response(_perfil_sesion(user))


@swagger_auto_schema(
    method='get',
    operation_description="Devuelve la sesión actualizada de un usuario (se usa al recargar la página).",
    manual_parameters=[
        openapi.Parameter('email', openapi.IN_QUERY, description="Correo del usuario", type=openapi.TYPE_STRING, required=True),
    ],
    responses={
        200: openapi.Response('Sesión vigente.', openapi.Schema(type=openapi.TYPE_OBJECT)),
        404: openapi.Response('Usuario no encontrado.', openapi.Schema(type=openapi.TYPE_OBJECT)),
    }
)
@api_view(['GET'])
def session(request):
    """Rehidrata la sesión tras recargar la página.

    El frontend guarda la sesión en localStorage; al recargar consulta este
    endpoint para traer datos frescos (rol, estado, cancelaciones) en vez de
    confiar ciegamente en lo guardado en el navegador.
    """
    email = request.query_params.get('email', '').strip().lower()
    if not email:
        return Response({'error': 'Parámetro email requerido.'}, status=400)
    user = get_db().users.find_one({'email': email})
    if not user:
        return Response({'error': 'Usuario no encontrado.'}, status=404)
    return Response(_perfil_sesion(user))


# ──────────────────────────────────────────
# ADMINISTRACIÓN DE USUARIOS
# ──────────────────────────────────────────

@swagger_auto_schema(
    method='get',
    operation_description="Lista los usuarios del sistema (solo ADMIN).",
    manual_parameters=[
        openapi.Parameter('actor_email', openapi.IN_QUERY, description="Correo del administrador", type=openapi.TYPE_STRING, required=True),
    ],
    responses={200: openapi.Response('Listado de usuarios.'), 403: openapi.Response('Solo administradores.')}
)
@swagger_auto_schema(
    method='post',
    operation_description="Un ADMIN crea nuevos usuarios, incluidos otros administradores.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['actor_email', 'name', 'email', 'password'],
        properties={
            'actor_email': openapi.Schema(type=openapi.TYPE_STRING, example='soporte@udemedellin.edu.co'),
            'name': openapi.Schema(type=openapi.TYPE_STRING, example='Nueva Administradora'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='nueva.admin@udemedellin.edu.co'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, example='secreto123'),
            'role': openapi.Schema(type=openapi.TYPE_STRING, example='ADMIN', description='Debe coincidir con el dominio del correo.'),
        }
    ),
    responses={
        201: openapi.Response('Usuario creado.'),
        400: openapi.Response('Datos inválidos.'),
        403: openapi.Response('Solo administradores.'),
        409: openapi.Response('El correo ya existe.'),
    }
)
@api_view(['GET', 'POST'])
def admin_users(request):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO — GESTIÓN DE USUARIOS POR EL ADMINISTRADOR              ║
    # ║ Solo un ADMIN autenticado puede dar de alta cuentas, y es la única   ║
    # ║ vía para crear NUEVOS ADMINISTRADORES. El rol sigue amarrado al      ║
    # ║ dominio del correo (RN01): un admin no puede crear un administrador  ║
    # ║ con un correo de estudiante.                                        ║
    # ╚══════════════════════════════════════════════════════════════════╝
    db = get_db()
    actor_email = (request.query_params.get('actor_email') if request.method == 'GET'
                   else request.data.get('actor_email', ''))
    actor = db.users.find_one({'email': (actor_email or '').strip().lower()})
    if not actor or actor.get('role') != 'ADMIN':
        return Response({'error': 'Solo un administrador puede gestionar usuarios.'}, status=403)

    if request.method == 'GET':
        rows = [{
            'name': u.get('name'), 'email': u['email'], 'role': u.get('role'),
            'estado': u.get('estado'), 'cancel_count': u.get('cancel_count', 0),
            'no_show_count': u.get('no_show_count', 0),
        } for u in db.users.find().sort('role', 1)]
        return Response(rows)

    name     = request.data.get('name', '').strip()
    email    = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')
    if not name or not email or not password:
        return Response({'error': 'Nombre, correo y contraseña son obligatorios.'}, status=400)
    if len(password) < 6:
        return Response({'error': 'La contraseña debe tener al menos 6 caracteres.'}, status=400)

    role = role_for_email(email)
    if role is None:
        return Response(
            {'error': f'Debes usar un correo institucional válido: {_dominios_texto()}.'},
            status=400,
        )

    # Si el admin indica un rol explícito, debe coincidir con el dominio.
    pedido = request.data.get('role')
    if pedido:
        pedido = pedido.strip().upper()
        if pedido not in ROLES:
            return Response({'error': f'Rol inválido. Use uno de: {", ".join(ROLES)}.'}, status=400)
        if pedido != role:
            return Response(
                {'error': f'El correo {email} corresponde al rol {role}, no a {pedido}. '
                          f'Para crear un {pedido} usa un correo del dominio correspondiente.'},
                status=400,
            )

    if db.users.find_one({'email': email}):
        return Response({'error': 'Ya existe una cuenta con este correo.'}, status=409)

    db.users.insert_one({
        'name':       name,
        'email':      email,
        'password':   hash_password(password),
        'role':       role,
        'estado':     'ACTIVO',
        'no_show_count': 0,
        'cancel_count':  0,
        'penalizado_hasta': None,
        'created_at': datetime.utcnow(),
        'created_by': actor['email'],
    })
    return Response({'message': f'Usuario creado con rol {role}.', 'role': role}, status=201)


# ──────────────────────────────────────────
# SLOTS
# ──────────────────────────────────────────

@swagger_auto_schema(
    method='get',
    operation_description="Bloques horarios y cupos disponibles para la fecha de reserva (el día siguiente).",
    responses={
        200: openapi.Response('Disponibilidad del día siguiente.', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'fecha': openapi.Schema(type=openapi.TYPE_STRING, example='2026-08-17'),
                'fecha_label': openapi.Schema(type=openapi.TYPE_STRING, example='lunes 17 de agosto de 2026'),
                'slots': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
            }
        )),
    }
)
@api_view(['GET'])
def get_slots(request):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #3 — CONSULTA DE CUPOS EN TIEMPO REAL           ║
    # ║ Crítico para la consistencia: el frontend muestra disponibilidad    ║
    # ║ "en vivo" y decide qué bloques se pueden reservar a partir de este  ║
    # ║ valor. Debe reflejar siempre el estado real de la colección slots.  ║
    # ║ RN03 — La respuesta incluye la FECHA DE LA RESERVA (el día          ║
    # ║ siguiente) para que la interfaz la muestre de forma explícita.      ║
    # ╚══════════════════════════════════════════════════════════════════╝
    seed_slots()
    db = get_db()
    slots = [
        {'id': s['slotId'], 'hour': s['hour'], 'available': s['available'], 'total': s['total']}
        for s in db.slots.find({}, {'_id': 0}).sort('slotId', 1)
    ]
    fecha = fecha_reserva()
    return Response({
        'fecha': fecha.isoformat(),
        'fecha_label': formato_fecha_es(fecha),
        'slots': slots,
    })


# ──────────────────────────────────────────
# RESERVATIONS
# ──────────────────────────────────────────

@swagger_auto_schema(
    method='get',
    operation_description="Lista las reservas activas de un estudiante.",
    manual_parameters=[
        openapi.Parameter('email', openapi.IN_QUERY, description="Correo del usuario", type=openapi.TYPE_STRING, required=True),
    ],
    responses={
        200: openapi.Response('Lista de reservas.', openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))),
        400: openapi.Response('Parámetro email requerido.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
    }
)
@swagger_auto_schema(
    method='post',
    operation_description="Crea la reserva del día siguiente y descuenta cupo. Una sola reserva por día.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'slotId'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='juan.perez@soyudemedellin.edu.co'),
            'slotId': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
        }
    ),
    responses={
        201: openapi.Response('Reserva creada.', openapi.Schema(type=openapi.TYPE_OBJECT)),
        400: openapi.Response('Datos inválidos.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
        403: openapi.Response('Perfil sin permiso de reserva.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
        404: openapi.Response('Horario no encontrado.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
        409: openapi.Response('Sin cupos o ya reservó hoy.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
    }
)
@api_view(['GET', 'POST'])
def reservations(request):
    db = get_db()

    if request.method == 'GET':
        email = request.query_params.get('email', '').lower()
        if not email:
            return Response({'error': 'Parámetro email requerido.'}, status=400)
        # Solo las ACTIVA: las canceladas o marcadas No-Show no se listan.
        docs = [serialize(r) for r in db.reservations.find({'email': email, 'estado': 'ACTIVA'})]
        return Response(docs)

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #4 — CREAR RESERVA (DESCUENTO ATÓMICO DE CUPO)  ║
    # ║ El más crítico del sistema. Bajo concurrencia (varios estudiantes   ║
    # ║ reservando el último cupo a la vez), un patrón "leer-luego-escribir" ║
    # ║ permite SOBREVENTA: dos peticiones leen available=1, ambas crean la  ║
    # ║ reserva y el cupo queda en -1.                                      ║
    # ║ Solución: se descuenta con find_one_and_update CONDICIONAL          ║
    # ║ (available > 0) en una sola operación atómica de MongoDB. Si el     ║
    # ║ documento devuelto es None, no había cupo y se rechaza SIN crear     ║
    # ║ reserva. La reserva solo se inserta DESPUÉS de ganar el cupo.       ║
    # ║ Reglas aplicadas aquí:                                              ║
    # ║   RN02 — Solo los ESTUDIANTES reservan (profesores y admins solo     ║
    # ║          consultan el aforo).                                       ║
    # ║   RN03 — La reserva es SIEMPRE para el día siguiente.                ║
    # ║   RN05 — Una única reserva por día.                                  ║
    # ║   RN09/RN10 — Bloqueo si el usuario está PENALIZADO.                 ║
    # ╚══════════════════════════════════════════════════════════════════╝
    email   = request.data.get('email', '').strip().lower()
    slot_id = request.data.get('slotId')

    if not email or slot_id is None:
        return Response({'error': 'email y slotId son obligatorios.'}, status=400)

    owner = db.users.find_one({'email': email})
    if not owner:
        return Response({'error': 'El usuario de la reserva no existe.'}, status=404)

    # RN02 — El gimnasio reserva cupos para estudiantes. Profesores y
    # administradores usan el sistema únicamente para consultar el aforo.
    if owner.get('role') != 'ESTUDIANTE':
        return Response(
            {'error': 'Los profesores y administradores no reservan cupos: solo consultan el aforo.'},
            status=403,
        )

    # RN09/RN10 — Un usuario PENALIZADO no puede crear reservas (sí consultar).
    if owner.get('estado') == 'PENALIZADO':
        hasta = owner.get('penalizado_hasta')
        if hasta and hasta > datetime.utcnow():
            return Response({'error': 'Tu cuenta está penalizada. No puedes reservar por ahora.'}, status=403)
        # Penalización vencida: se reactiva la cuenta y se reinician contadores.
        db.users.update_one(
            {'email': email},
            {'$set': {'estado': 'ACTIVO', 'no_show_count': 0, 'cancel_count': 0, 'penalizado_hasta': None}},
        )

    slot = db.slots.find_one({'slotId': slot_id})
    if not slot:
        return Response({'error': 'Horario no encontrado.'}, status=404)

    fecha = fecha_reserva()
    fecha_iso = fecha.isoformat()
    fecha_label = formato_fecha_es(fecha)

    # RN05 — UNA SOLA RESERVA POR DÍA. Se cuenta sobre la fecha de la reserva
    # (el día siguiente), no sobre el total histórico de reservas activas.
    del_dia = db.reservations.count_documents(
        {'email': email, 'estado': 'ACTIVA', 'reserva_date': fecha_iso}
    )
    if del_dia >= MAX_RESERVAS_POR_DIA:
        return Response(
            {'error': f'Ya tienes una reserva para el {fecha_label}. '
                      'Solo se permite una reserva por día: cancela la actual si quieres cambiar de horario.'},
            status=409,
        )

    # Descuento ATÓMICO: solo descuenta si todavía queda cupo (available > 0).
    claimed = db.slots.find_one_and_update(
        {'slotId': slot_id, 'available': {'$gt': 0}},
        {'$inc': {'available': -1}},
    )
    if claimed is None:
        # Otro estudiante tomó el último cupo entre la lectura y este punto.
        return Response({'error': 'No hay cupos disponibles en este horario.'}, status=409)

    now = datetime.utcnow()
    result = db.reservations.insert_one({
        'email':        email,
        'slotId':       slot_id,
        'hour':         slot['hour'],
        'reserva_date': fecha_iso,        # RN03 — fecha efectiva: el día siguiente
        'date':         fecha_label,      # etiqueta legible para la interfaz
        'estado':       'ACTIVA',         # ACTIVA | CANCELADA | NO_SHOW | COMPLETADA
        'created_by':   email,
        'created_at':   now,
    })

    new_res = db.reservations.find_one({'_id': result.inserted_id})
    return Response(serialize(new_res), status=201)


@swagger_auto_schema(
    method='delete',
    operation_description="Cancela reserva y libera cupo inmediatamente. Suma al contador de cancelaciones (RN10).",
    manual_parameters=[
        openapi.Parameter('reservation_id', openapi.IN_PATH, description="ID de la reserva (ObjectId)", type=openapi.TYPE_STRING, required=True),
    ],
    responses={
        200: openapi.Response('Reserva cancelada.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'message': openapi.Schema(type=openapi.TYPE_STRING)})),
        400: openapi.Response('ID inválido.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
        404: openapi.Response('Reserva no encontrada.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
    }
)
@api_view(['DELETE'])
def cancel_reservation(request, reservation_id):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #5 — CANCELAR RESERVA Y LIBERAR CUPO            ║
    # ║ Crítico para no "perder" cupos: el cupo solo se devuelve (+1) si la  ║
    # ║ reserva estaba ACTIVA y esta operación la pasó a CANCELADA. Se usa    ║
    # ║ find_one_and_update CONDICIONAL (estado='ACTIVA') como guardia: una   ║
    # ║ doble cancelación no vuelve a sumar el cupo (no dejaría available>total).║
    # ║ RN10 — Cada cancelación suma al contador del estudiante. Al llegar a  ║
    # ║ CANCELACION_LIMITE la cuenta queda PENALIZADA; antes de eso la        ║
    # ║ respuesta devuelve la alerta que la app muestra en pantalla.          ║
    # ╚══════════════════════════════════════════════════════════════════╝
    db = get_db()
    try:
        oid = ObjectId(reservation_id)
    except Exception:
        return Response({'error': 'ID de reserva inválido.'}, status=400)

    # Transición atómica ACTIVA -> CANCELADA. Devuelve el doc previo o None.
    reservation = db.reservations.find_one_and_update(
        {'_id': oid, 'estado': 'ACTIVA'},
        {'$set': {'estado': 'CANCELADA', 'cancelled_at': datetime.utcnow()}},
    )
    if reservation is None:
        # O no existe, o ya no estaba activa (cancelada / no-show).
        if db.reservations.find_one({'_id': oid}):
            return Response({'error': 'La reserva ya no está activa.'}, status=409)
        return Response({'error': 'Reserva no encontrada.'}, status=404)

    db.slots.update_one({'slotId': reservation['slotId']}, {'$inc': {'available': 1}})

    # RN10 — Contador de cancelaciones del estudiante.
    owner = db.users.find_one_and_update(
        {'email': reservation['email']},
        {'$inc': {'cancel_count': 1}},
        return_document=True,
    )
    penalizado = False
    if owner and owner.get('cancel_count', 0) >= CANCELACION_LIMITE:
        hasta = add_business_days(datetime.utcnow(), PENALIZACION_DIAS_HABILES)
        db.users.update_one(
            {'email': reservation['email']},
            {'$set': {'estado': 'PENALIZADO', 'penalizado_hasta': hasta}},
        )
        penalizado = True

    # RF12 — al liberar el cupo, mueve al primero de la lista de espera.
    from .features import pop_next_in_waitlist
    pop_next_in_waitlist(reservation['slotId'])

    return Response({
        'message': 'Reserva cancelada. Cupo liberado.',
        'cancel_count': (owner or {}).get('cancel_count', 0),
        'cancelaciones_restantes': cancelaciones_restantes(owner),
        'cancelacion_limite': CANCELACION_LIMITE,
        'penalizado': penalizado,
        'alerta': alerta_cancelaciones(owner),
    })


@swagger_auto_schema(
    method='post',
    operation_description="El entrenador/admin marca una inasistencia (No-Show). Suma al contador y, al llegar al límite, penaliza al usuario (RN09).",
    manual_parameters=[
        openapi.Parameter('reservation_id', openapi.IN_PATH, description="ID de la reserva (ObjectId)", type=openapi.TYPE_STRING, required=True),
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['actor_email'],
        properties={'actor_email': openapi.Schema(type=openapi.TYPE_STRING, example='profesor@udem.edu.co')},
    ),
    responses={
        200: openapi.Response('No-Show registrado.', openapi.Schema(type=openapi.TYPE_OBJECT)),
        403: openapi.Response('Sin permisos.', openapi.Schema(type=openapi.TYPE_OBJECT)),
        404: openapi.Response('Reserva no encontrada.', openapi.Schema(type=openapi.TYPE_OBJECT)),
    }
)
@api_view(['POST'])
def mark_no_show(request, reservation_id):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO — RN09: POLÍTICA DE INASISTENCIA Y PENALIZACIÓN         ║
    # ║ Solo ENTRENADOR/ADMIN. Marca la reserva como NO_SHOW, incrementa el  ║
    # ║ contador del usuario y, al alcanzar NO_SHOW_LIMITE inasistencias,    ║
    # ║ cambia su estado a PENALIZADO por N días hábiles.                    ║
    # ╚══════════════════════════════════════════════════════════════════╝
    db = get_db()
    actor_email = request.data.get('actor_email', '').strip().lower()
    actor = db.users.find_one({'email': actor_email})
    if not actor or actor.get('role') not in ('ENTRENADOR', 'ADMIN'):
        return Response({'error': 'Solo un profesor o administrador puede registrar inasistencias.'}, status=403)

    try:
        oid = ObjectId(reservation_id)
    except Exception:
        return Response({'error': 'ID de reserva inválido.'}, status=400)

    # ACTIVA -> NO_SHOW de forma atómica (no se devuelve el cupo: se desperdició).
    reservation = db.reservations.find_one_and_update(
        {'_id': oid, 'estado': 'ACTIVA'},
        {'$set': {'estado': 'NO_SHOW', 'no_show_at': datetime.utcnow()}},
    )
    if reservation is None:
        return Response({'error': 'Reserva no encontrada o ya no está activa.'}, status=404)

    # Incrementa el contador de inasistencias del usuario dueño.
    owner = db.users.find_one_and_update(
        {'email': reservation['email']},
        {'$inc': {'no_show_count': 1}},
        return_document=True,
    )
    penalizado = False
    if owner and owner.get('no_show_count', 0) >= NO_SHOW_LIMITE:
        hasta = add_business_days(datetime.utcnow(), PENALIZACION_DIAS_HABILES)
        db.users.update_one(
            {'email': reservation['email']},
            {'$set': {'estado': 'PENALIZADO', 'penalizado_hasta': hasta}},
        )
        penalizado = True

    return Response({
        'message': 'Inasistencia registrada.',
        'no_show_count': (owner or {}).get('no_show_count', 0),
        'penalizado': penalizado,
    })
