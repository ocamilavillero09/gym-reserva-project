from datetime import datetime
from bson import ObjectId
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .db import get_db, seed_slots, hash_password, verify_password, serialize


# ──────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────

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
