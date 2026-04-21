from datetime import datetime
from bson import ObjectId
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .db import get_db, seed_slots, hash_password, verify_password, serialize


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

    db.users.insert_one({
        'name':     name,
        'email':    email,
        'password': hash_password(password),
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
    db = get_db()
    email    = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    user = db.users.find_one({'email': email})
    if not user or not verify_password(user['password'], password):
        return Response({'error': 'Correo o contraseña incorrectos.'}, status=401)

    return Response({'name': user['name'], 'email': user['email']})


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
        docs = [serialize(r) for r in db.reservations.find({'email': email})]
        return Response(docs)

    # POST — crear reserva
    email   = request.data.get('email', '').strip().lower()
    slot_id = request.data.get('slotId')

    if not email or slot_id is None:
        return Response({'error': 'email y slotId son obligatorios.'}, status=400)

    slot = db.slots.find_one({'slotId': slot_id})
    if not slot:
        return Response({'error': 'Horario no encontrado.'}, status=404)
    if slot['available'] <= 0:
        return Response({'error': 'No hay cupos disponibles en este horario.'}, status=409)
    if db.reservations.find_one({'email': email, 'slotId': slot_id}):
        return Response({'error': 'Ya tienes una reserva en este horario.'}, status=409)

    now = datetime.utcnow()
    result = db.reservations.insert_one({
        'email':   email,
        'slotId':  slot_id,
        'hour':    slot['hour'],
        'date':    now.strftime('%A %d de %B de %Y'),
        'created_at': now,
    })
    db.slots.update_one({'slotId': slot_id}, {'$inc': {'available': -1}})

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
    db = get_db()
    try:
        oid = ObjectId(reservation_id)
    except Exception:
        return Response({'error': 'ID de reserva inválido.'}, status=400)

    reservation = db.reservations.find_one({'_id': oid})
    if not reservation:
        return Response({'error': 'Reserva no encontrada.'}, status=404)

    db.reservations.delete_one({'_id': oid})
    db.slots.update_one({'slotId': reservation['slotId']}, {'$inc': {'available': 1}})

    return Response({'message': 'Reserva cancelada. Cupo liberado.'})
