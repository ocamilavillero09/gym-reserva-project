import hashlib
import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from django.conf import settings

_client = None

# Roles y estados de usuario (RF02 / RN09 del documento de análisis).
ROLES = ('ESTUDIANTE', 'ENTRENADOR', 'ADMIN')
ESTADOS = ('ACTIVO', 'PENALIZADO', 'INACTIVO')

# Reglas de negocio configurables.
MAX_RESERVAS_ACTIVAS = 2     # RN05: hasta 2 reservas activas por usuario
NO_SHOW_LIMITE = 3           # RN09: 3 inasistencias -> PENALIZADO
PENALIZACION_DIAS_HABILES = 5  # RN09: penalización de 5 días hábiles


def add_business_days(start: datetime, days: int) -> datetime:
    """Suma N días hábiles (lunes-viernes) a una fecha."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # 0-4 = lunes a viernes
            added += 1
    return current

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

def seed_machines():
    """Inicializa el catálogo de máquinas si está vacío (RF18)."""
    db = get_db()
    if db.machines.count_documents({}) == 0:
        db.machines.insert_many([
            {'machineId': 1, 'name': 'Caminadora 1',    'estado': 'DISPONIBLE', 'note': ''},
            {'machineId': 2, 'name': 'Caminadora 2',    'estado': 'DISPONIBLE', 'note': ''},
            {'machineId': 3, 'name': 'Banco de pesas',  'estado': 'DISPONIBLE', 'note': ''},
            {'machineId': 4, 'name': 'Bicicleta estática', 'estado': 'DISPONIBLE', 'note': ''},
            {'machineId': 5, 'name': 'Multifuerza',     'estado': 'DISPONIBLE', 'note': ''},
        ])


def get_config(key: str, default=None):
    """Lee un valor de la colección de configuración (p. ej. claves VAPID)."""
    doc = get_db().config.find_one({'_id': key})
    return doc['value'] if doc else default


def set_config(key: str, value):
    get_db().config.update_one({'_id': key}, {'$set': {'value': value}}, upsert=True)


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
