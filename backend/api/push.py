"""
RF14 — Notificaciones push web (Web Push API + VAPID).

Flujo:
  1) El navegador pide la clave pública VAPID (GET /push/public-key/).
  2) El usuario se suscribe y manda su subscription (POST /push/subscribe/).
  3) Un recordatorio se envía con POST /push/remind/ (entrenador, por bloque).
     La automatización "30 min antes" se haría con un CronJob de Kubernetes que
     llame a este endpoint; aquí el disparo es manual desde el panel del entrenador.

Las claves VAPID se generan una sola vez y se guardan en la colección config.
Si las librerías de push no están instaladas, los endpoints responden 501.
"""
import base64
import json
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .db import get_db, get_config, set_config

logger = logging.getLogger('gym.push')


def _ensure_vapid():
    """Devuelve (public_b64, private_pem) generándolas la primera vez."""
    pub = get_config('vapid_public')
    priv = get_config('vapid_private')
    if pub and priv:
        return pub, priv

    from py_vapid import Vapid01
    from cryptography.hazmat.primitives import serialization

    vapid = Vapid01()
    vapid.generate_keys()
    priv_pem = vapid.private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    raw_pub = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    pub_b64 = base64.urlsafe_b64encode(raw_pub).rstrip(b'=').decode()
    set_config('vapid_public', pub_b64)
    set_config('vapid_private', priv_pem)
    return pub_b64, priv_pem


@api_view(['GET'])
def public_key(request):
    try:
        pub, _ = _ensure_vapid()
    except ImportError:
        return Response({'error': 'Push no disponible (faltan dependencias).'}, status=501)
    return Response({'publicKey': pub})


@api_view(['POST'])
def subscribe(request):
    email = request.data.get('email', '').strip().lower()
    sub = request.data.get('subscription')
    if not email or not sub:
        return Response({'error': 'email y subscription requeridos.'}, status=400)
    # Guarda la subscription en el usuario (evita duplicados por endpoint).
    get_db().users.update_one(
        {'email': email},
        {'$pull': {'push_subscriptions': {'endpoint': sub.get('endpoint')}}},
    )
    get_db().users.update_one(
        {'email': email},
        {'$push': {'push_subscriptions': sub}},
    )
    return Response({'message': 'Suscripción registrada.'}, status=201)


@api_view(['POST'])
def remind(request):
    """Envía un recordatorio push a los inscritos ACTIVA de un bloque (RF14)."""
    db = get_db()
    actor = db.users.find_one({'email': request.data.get('actor_email', '').strip().lower()})
    if not actor or actor.get('role') not in ('ENTRENADOR', 'ADMIN'):
        return Response({'error': 'Solo entrenador/admin.'}, status=403)

    slot_id = request.data.get('slotId')
    try:
        from pywebpush import webpush, WebPushException
        _, priv = _ensure_vapid()
    except ImportError:
        return Response({'error': 'Push no disponible (faltan dependencias).'}, status=501)

    slot = db.slots.find_one({'slotId': slot_id})
    if not slot:
        return Response({'error': 'Horario no encontrado.'}, status=404)

    emails = db.reservations.distinct('email', {'slotId': slot_id, 'estado': 'ACTIVA'})
    sent, failed = 0, 0
    payload = json.dumps({'title': 'Recordatorio de gimnasio',
                          'body': f"Tu bloque de las {slot['hour']} está por comenzar."})
    for user in db.users.find({'email': {'$in': emails}, 'push_subscriptions': {'$exists': True}}):
        for sub in user.get('push_subscriptions', []):
            try:
                webpush(subscription_info=sub, data=payload,
                        vapid_private_key=priv, vapid_claims={'sub': 'mailto:gimnasio@udem.edu.co'})
                sent += 1
            except WebPushException as exc:
                failed += 1
                logger.warning('push falló: %s', exc)
    return Response({'message': 'Recordatorios enviados.', 'enviados': sent, 'fallidos': failed})
