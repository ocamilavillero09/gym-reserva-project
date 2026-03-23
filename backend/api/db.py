import hashlib
import os
from pymongo import MongoClient
from django.conf import settings

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI)
    return _client[settings.MONGO_DB]

def seed_slots():
    """Inicializa los bloques horarios si la colección está vacía."""
    db = get_db()
    if db.slots.count_documents({}) == 0:
        db.slots.insert_many([
            {'slotId': 1, 'hour': '06:00', 'available': 20, 'total': 20},
            {'slotId': 2, 'hour': '08:00', 'available': 20, 'total': 20},
            {'slotId': 3, 'hour': '10:00', 'available': 20, 'total': 20},
            {'slotId': 4, 'hour': '12:00', 'available': 20, 'total': 20},
            {'slotId': 5, 'hour': '14:00', 'available': 20, 'total': 20},
            {'slotId': 6, 'hour': '16:00', 'available': 20, 'total': 20},
        ])

def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100_000)
    return salt.hex() + ':' + key.hex()

def verify_password(stored: str, provided: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(':')
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac('sha256', provided.encode(), salt, 100_000)
        return key.hex() == key_hex
    except Exception:
        return False

def serialize(doc: dict) -> dict:
    """Convierte ObjectId a string para que sea JSON serializable."""
    doc['id'] = str(doc.pop('_id'))
    return doc
