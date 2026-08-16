import hashlib
import os
from datetime import date, datetime, timedelta
from pymongo import MongoClient
from django.conf import settings
from django.utils import timezone

_client = None

# Roles y estados de usuario (RF02 / RN09 del documento de análisis).
ROLES = ('ESTUDIANTE', 'ENTRENADOR', 'ADMIN')
ESTADOS = ('ACTIVO', 'PENALIZADO', 'INACTIVO')

# ──────────────────────────────────────────────────────────────────────────
# RN01 — TRES TIPOS DE CORREO INSTITUCIONAL PARA DIFERENCIAR USUARIOS
# El dominio del correo determina el rol: no se elige en el formulario, se
# deduce del correo con el que la persona se registra. Así un estudiante no
# puede auto-asignarse un rol de entrenador o administrador.
# ──────────────────────────────────────────────────────────────────────────
DOMINIOS_ROL = {
    '@soyudemedellin.edu.co': 'ESTUDIANTE',
    '@udem.edu.co':           'ENTRENADOR',
    '@udemedellin.edu.co':    'ADMIN',
}

# Reglas de negocio configurables.
MAX_RESERVAS_POR_DIA = 1      # RN05: una única reserva activa por día
NO_SHOW_LIMITE = 3            # RN09: 3 inasistencias -> PENALIZADO
CANCELACION_LIMITE = 5        # RN10: 5 cancelaciones -> PENALIZADO
CANCELACION_ALERTA = 2        # RN10: avisar cuando falten 2 para la penalización
PENALIZACION_DIAS_HABILES = 5  # RN09/RN10: penalización de 5 días hábiles

# Nombres en español para las fechas: strftime depende del locale del sistema
# (que en los contenedores suele ser inglés), así que se formatea a mano.
_DIAS = ('lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo')
_MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
          'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre')


def role_for_email(email: str):
    """Rol que corresponde al dominio del correo, o None si no es institucional."""
    email = (email or '').strip().lower()
    for dominio, rol in DOMINIOS_ROL.items():
        if email.endswith(dominio):
            return rol
    return None


def hoy_local() -> date:
    """Fecha de hoy en la zona horaria del gimnasio (America/Bogota)."""
    return timezone.localtime().date()


def fecha_reserva() -> date:
    """RN03 — Las reservas siempre son para el DÍA SIGUIENTE."""
    return hoy_local() + timedelta(days=1)


def formato_fecha_es(d: date) -> str:
    """'martes 18 de agosto de 2026' — etiqueta legible para la interfaz."""
    return f'{_DIAS[d.weekday()]} {d.day} de {_MESES[d.month - 1]} de {d.year}'


def cancelaciones_restantes(user: dict) -> int:
    """Cuántas cancelaciones le faltan al usuario para ser penalizado."""
    usadas = (user or {}).get('cancel_count', 0)
    return max(CANCELACION_LIMITE - usadas, 0)


def alerta_cancelaciones(user: dict):
    """Mensaje de alerta in-app cuando quedan pocas cancelaciones (RN10).

    Devuelve None si todavía no hay motivo de alerta.
    """
    restantes = cancelaciones_restantes(user)
    if restantes == 0:
        return (f'Alcanzaste el límite de {CANCELACION_LIMITE} cancelaciones. '
                'Tu cuenta quedó penalizada y no puedes reservar por ahora.')
    if restantes <= CANCELACION_ALERTA:
        veces = 'cancelación' if restantes == 1 else 'cancelaciones'
        return (f'Atención: llevas {(user or {}).get("cancel_count", 0)} cancelaciones. '
                f'Estás a {restantes} {veces} de ser penalizado.')
    return None


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
    """Lee un valor de la colección de configuración."""
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
