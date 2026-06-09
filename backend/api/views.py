from datetime import datetime
from bson import ObjectId
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .db import (
    get_db, seed_slots, hash_password, verify_password, serialize,
    add_business_days, ROLES, ESTADOS,
    MAX_RESERVAS_ACTIVAS, NO_SHOW_LIMITE, PENALIZACION_DIAS_HABILES,
)
from .notifications import send_reservation_confirmation, send_cancellation_notice


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


# ──────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────

@swagger_auto_schema(
    method='post',
    operation_description="Registro de usuarios con correo institucional.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['name', 'email', 'password'],
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, example='Juan Pérez'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='juan.perez@udem.edu.co'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, example='secreto123'),
        }
    ),
    responses={
        201: openapi.Response('Registro exitoso.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'message': openapi.Schema(type=openapi.TYPE_STRING)})),
        400: openapi.Response('Datos inválidos.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
        409: openapi.Response('Correo ya existe.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
    }
)
@api_view(['POST'])
def register(request):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #1 — REGISTRO CON CORREO INSTITUCIONAL          ║
    # ║ Crítico porque es el control de acceso: solo miembros de la         ║
    # ║ universidad (@udem.edu.co / @soyudemedellin.edu.co) pueden crear    ║
    # ║ cuenta, la contraseña se almacena HASHEADA (PBKDF2, nunca en claro) ║
    # ║ y el correo es único — evita cuentas duplicadas y accesos externos. ║
    # ╚══════════════════════════════════════════════════════════════════╝
    db = get_db()
    name     = request.data.get('name', '').strip()
    email    = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    if not name or not email or not password:
        return Response({'error': 'Todos los campos son obligatorios.'}, status=400)

    if len(password) < 6:
        return Response({'error': 'La contraseña debe tener al menos 6 caracteres.'}, status=400)

    valid_domains = ('@soyudemedellin.edu.co', '@udem.edu.co')
    if not any(email.endswith(d) for d in valid_domains):
        return Response({'error': 'Debes usar tu correo institucional (@soyudemedellin.edu.co o @udem.edu.co).'}, status=400)

    if db.users.find_one({'email': email}):
        return Response({'error': 'Ya existe una cuenta con este correo.'}, status=409)

    # RF02 — Rol del usuario. Por defecto ESTUDIANTE; se admite crear
    # ENTRENADOR/ADMIN para la gestión (en un entorno real lo asignaría un admin).
    role = request.data.get('role', 'ESTUDIANTE').strip().upper()
    if role not in ROLES:
        return Response({'error': f'Rol inválido. Use uno de: {", ".join(ROLES)}.'}, status=400)

    db.users.insert_one({
        'name':       name,
        'email':      email,
        'password':   hash_password(password),
        'role':       role,
        'estado':     'ACTIVO',          # RN09: ACTIVO | PENALIZADO | INACTIVO
        'no_show_count': 0,
        'penalizado_hasta': None,
        'created_at': datetime.utcnow(),
    })

    return Response({'message': 'Registro exitoso.'}, status=201)


@swagger_auto_schema(
    method='post',
    operation_description="Inicio de sesión y validación de credenciales.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'password'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='juan.perez@udem.edu.co'),
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

    # Se devuelve el rol y el estado para que el frontend (HU11) muestre las
    # herramientas de cada perfil y advierta si el usuario está PENALIZADO.
    return Response({
        'name':   user['name'],
        'email':  user['email'],
        'role':   user.get('role', 'ESTUDIANTE'),
        'estado': user.get('estado', 'ACTIVO'),
    })


# ──────────────────────────────────────────
# SLOTS
# ──────────────────────────────────────────

@swagger_auto_schema(
    method='get',
    operation_description="Consulta de bloques horarios (pares) y cupos disponibles.",
    responses={
        200: openapi.Response('Lista de horarios.', openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'hour': openapi.Schema(type=openapi.TYPE_STRING),
                'available': openapi.Schema(type=openapi.TYPE_INTEGER),
                'total': openapi.Schema(type=openapi.TYPE_INTEGER),
            })
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
    # ╚══════════════════════════════════════════════════════════════════╝
    seed_slots()
    db = get_db()
    slots = [
        {'id': s['slotId'], 'hour': s['hour'], 'available': s['available'], 'total': s['total']}
        for s in db.slots.find({}, {'_id': 0}).sort('slotId', 1)
    ]
    return Response(slots)


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
    operation_description="Crea una reserva y descuenta cupo.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'slotId'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='juan.perez@udem.edu.co'),
            'slotId': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
        }
    ),
    responses={
        201: openapi.Response('Reserva creada.', openapi.Schema(type=openapi.TYPE_OBJECT)),
        400: openapi.Response('Datos inválidos.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
        404: openapi.Response('Horario no encontrado.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
        409: openapi.Response('Sin cupos o ya existe reserva.', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'error': openapi.Schema(type=openapi.TYPE_STRING)})),
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
    # ║ Aquí también se aplican RN05 (máx. 2 activas), RN07 (1 por bloque),  ║
    # ║ RN09 (bloqueo si PENALIZADO) y RF07 (el entrenador reserva a otros). ║
    # ╚══════════════════════════════════════════════════════════════════╝
    # 'email' = dueño de la reserva. Un ENTRENADOR/ADMIN puede crear la reserva
    # para un tercero enviando además 'actor_email' (quién la registra, RF07).
    email       = request.data.get('email', '').strip().lower()
    actor_email = request.data.get('actor_email', email).strip().lower()
    slot_id     = request.data.get('slotId')

    if not email or slot_id is None:
        return Response({'error': 'email y slotId son obligatorios.'}, status=400)

    # RF07 — Si reserva para un tercero distinto a sí mismo, el actor debe ser
    # ENTRENADOR o ADMIN.
    if actor_email != email:
        actor = db.users.find_one({'email': actor_email})
        if not actor or actor.get('role') not in ('ENTRENADOR', 'ADMIN'):
            return Response({'error': 'Solo un entrenador o administrador puede reservar para otro usuario.'}, status=403)

    owner = db.users.find_one({'email': email})
    if not owner:
        return Response({'error': 'El usuario de la reserva no existe.'}, status=404)

    # RN09 — Un usuario PENALIZADO no puede crear reservas (sí consultar).
    if owner.get('estado') == 'PENALIZADO':
        hasta = owner.get('penalizado_hasta')
        if hasta and hasta > datetime.utcnow():
            return Response({'error': 'Tu cuenta está penalizada por inasistencias. No puedes reservar por ahora.'}, status=403)
        # Penalización vencida: se reactiva la cuenta.
        db.users.update_one({'email': email}, {'$set': {'estado': 'ACTIVO', 'no_show_count': 0, 'penalizado_hasta': None}})

    slot = db.slots.find_one({'slotId': slot_id})
    if not slot:
        return Response({'error': 'Horario no encontrado.'}, status=404)

    # RN07 — Una reserva ACTIVA por usuario y bloque.
    if db.reservations.find_one({'email': email, 'slotId': slot_id, 'estado': 'ACTIVA'}):
        return Response({'error': 'Ya tienes una reserva en este horario.'}, status=409)

    # RN05 — Máximo de reservas activas simultáneas por usuario.
    activas = db.reservations.count_documents({'email': email, 'estado': 'ACTIVA'})
    if activas >= MAX_RESERVAS_ACTIVAS:
        return Response({'error': f'Has alcanzado el límite de {MAX_RESERVAS_ACTIVAS} reservas activas.'}, status=409)

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
        'email':      email,
        'slotId':     slot_id,
        'hour':       slot['hour'],
        'date':       now.strftime('%A %d de %B de %Y'),
        'estado':     'ACTIVA',          # ACTIVA | CANCELADA | NO_SHOW
        'created_by': actor_email,        # quién la registró (RF07)
        'created_at': now,
    })

    # Confirmación por correo (CASO DE USO de notificación que la UI anuncia).
    send_reservation_confirmation(email, (owner or {}).get('name', ''), slot['hour'],
                                  now.strftime('%A %d de %B de %Y'))

    new_res = db.reservations.find_one({'_id': result.inserted_id})
    return Response(serialize(new_res), status=201)


@swagger_auto_schema(
    method='delete',
    operation_description="Cancela reserva y libera cupo inmediatamente.",
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
    send_cancellation_notice(reservation['email'], reservation['hour'])

    # RF12 — al liberar el cupo, avisa al primero en la lista de espera.
    from .features import notify_next_in_waitlist
    notify_next_in_waitlist(reservation['slotId'])

    return Response({'message': 'Reserva cancelada. Cupo liberado.'})


@swagger_auto_schema(
    method='post',
    operation_description="El entrenador/admin marca una inasistencia (No-Show). Suma al contador y, al llegar al límite, penaliza al usuario (RN09).",
    manual_parameters=[
        openapi.Parameter('reservation_id', openapi.IN_PATH, description="ID de la reserva (ObjectId)", type=openapi.TYPE_STRING, required=True),
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['actor_email'],
        properties={'actor_email': openapi.Schema(type=openapi.TYPE_STRING, example='entrenador@udem.edu.co')},
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
        return Response({'error': 'Solo un entrenador o administrador puede registrar inasistencias.'}, status=403)

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
