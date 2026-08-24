"""
CAPA DE DATOS — CONSULTAS A LA BASE DE DATOS

Este archivo es lo único del backend que sabe que la base de datos es MongoDB.
Aquí solo hay consultas y escrituras: buscar, listar, contar, insertar y
actualizar. No decide nada.

Ninguna regla del gimnasio vive aquí: los límites de inasistencias, las fechas
de reserva o el rol que corresponde a un correo están en `reglas.py`. Y ninguna
función de este archivo construye respuestas HTTP: de eso se encargan las
vistas.

Si algún día el proyecto cambia de motor de base de datos, este es el único
archivo que habría que reescribir.
"""
from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient
from django.conf import settings

_client = None


# ──────────────────────────────────────────────────────────────────────────
# CONEXIÓN
# ──────────────────────────────────────────────────────────────────────────
def get_db():
    """Conexión (reutilizada) a la base de datos del gimnasio."""
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI)
    return _client[settings.MONGO_DB]


def serialize(doc: dict) -> dict:
    """Convierte el _id de Mongo en un texto para poder devolverlo como JSON."""
    doc['id'] = str(doc.pop('_id'))
    return doc


def a_object_id(valor):
    """Convierte un texto en ObjectId, o None si no tiene ese formato."""
    try:
        return ObjectId(valor)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────
# DATOS INICIALES
# ──────────────────────────────────────────────────────────────────────────
def sembrar_bloques():
    """Crea los bloques horarios del gimnasio si la colección está vacía.

    Un bloque guarda solo su CONFIGURACIÓN —identificador, hora y capacidad—.
    Cuántos cupos hay tomados NO se guarda: se cuenta a partir de las reservas
    de esa fecha. Así no hay dos versiones de la verdad que puedan discrepar,
    y cada jornada empieza con el gimnasio entero libre sin reiniciar nada.
    """
    db = get_db()
    if db.slots.count_documents({}) == 0:
        db.slots.insert_many([
            {'slotId': 1, 'hour': '06:00', 'total': 20},
            {'slotId': 2, 'hour': '08:00', 'total': 20},
            {'slotId': 3, 'hour': '10:00', 'total': 20},
            {'slotId': 4, 'hour': '12:00', 'total': 20},
            {'slotId': 5, 'hour': '14:00', 'total': 20},
            {'slotId': 6, 'hour': '16:00', 'total': 20},
        ])
    # Buscar las reservas de un bloque en una fecha es la consulta más
    # frecuente del sistema: se indexa.
    db.reservations.create_index([('slotId', 1), ('reserva_date', 1)])


# ──────────────────────────────────────────────────────────────────────────
# USUARIOS
# ──────────────────────────────────────────────────────────────────────────
def buscar_usuario(email: str):
    """Devuelve la cuenta con ese correo, o None."""
    return get_db().users.find_one({'email': email})


def buscar_usuario_por_documento(documento: str):
    """Devuelve la cuenta con ese documento de identidad, o None."""
    return get_db().users.find_one({'documento': documento})


def buscar_estudiante_por_documento(documento: str):
    """Devuelve el ESTUDIANTE con ese documento de identidad, o None."""
    return get_db().users.find_one({'documento': documento, 'role': 'ESTUDIANTE'})


def crear_usuario(datos: dict):
    """Da de alta una cuenta."""
    return get_db().users.insert_one(datos)


def listar_usuarios(orden='role'):
    """Todas las cuentas del sistema."""
    return list(get_db().users.find().sort(orden, 1))


def listar_estudiantes():
    """Las cuentas con rol de estudiante, por nombre."""
    return list(get_db().users.find({'role': 'ESTUDIANTE'}).sort('name', 1))


def listar_estudiantes_penalizados():
    """Los estudiantes cuya cuenta está penalizada, por nombre."""
    return list(get_db().users.find(
        {'role': 'ESTUDIANTE', 'estado': 'PENALIZADO'}).sort('name', 1))


def actualizar_usuario(email: str, cambios: dict, quitar: dict = None):
    """Modifica campos de una cuenta; `quitar` elimina campos."""
    operacion = {'$set': cambios}
    if quitar:
        operacion['$unset'] = quitar
    return get_db().users.update_one({'email': email}, operacion)


def sumar_a_contador(email: str, campo: str):
    """Incrementa en uno un contador de la cuenta y devuelve el documento ya actualizado."""
    return get_db().users.find_one_and_update(
        {'email': email}, {'$inc': {campo: 1}}, return_document=True)


def contar_administradores() -> int:
    """Cuántas cuentas con rol de administrador existen."""
    return get_db().users.count_documents({'role': 'ADMIN'})


def hay_administrador_principal() -> bool:
    """True si alguna cuenta lleva la marca de administrador principal."""
    return get_db().users.count_documents({'role': 'ADMIN', 'es_principal': True}) > 0


def administrador_mas_antiguo():
    """La cuenta de administrador creada primero, o None."""
    return get_db().users.find_one({'role': 'ADMIN'}, sort=[('created_at', 1)])


# ──────────────────────────────────────────────────────────────────────────
# BLOQUES HORARIOS Y CUPOS
# ──────────────────────────────────────────────────────────────────────────
def listar_bloques(sin_id=False):
    """Los bloques horarios del gimnasio, ordenados por identificador."""
    proyeccion = {'_id': 0} if sin_id else None
    return list(get_db().slots.find({}, proyeccion).sort('slotId', 1))


def buscar_bloque(slot_id):
    """Devuelve el bloque con ese identificador, o None."""
    return get_db().slots.find_one({'slotId': slot_id})


def ocupados_del_dia(fecha_iso: str) -> dict:
    """Cuántos cupos hay tomados en cada bloque para esa fecha.

    Se cuenta directamente sobre las reservas: una reserva cancelada libera su
    cupo, y una cumplida o marcada como inasistencia lo mantiene ocupado, pero
    SOLO en su día. Devuelve {slotId: ocupados}; un bloque que no aparece está
    entero.
    """
    agrupado = get_db().reservations.aggregate([
        {'$match': {'reserva_date': fecha_iso, 'estado': {'$ne': 'CANCELADA'}}},
        {'$group': {'_id': '$slotId', 'n': {'$sum': 1}}},
    ])
    return {d['_id']: d['n'] for d in agrupado}


def ocupacion_de_bloque(slot_id: int, fecha_iso: str) -> int:
    """Cuántas reservas vivas tiene ese bloque en esa fecha."""
    return contar_reservas({
        'slotId': slot_id, 'reserva_date': fecha_iso, 'estado': {'$ne': 'CANCELADA'},
    })


def reserva_dentro_del_aforo(oid, slot_id: int, fecha_iso: str, total: int) -> bool:
    """¿Esta reserva cabe en el bloque, o llegó tarde?

    Se ordenan las reservas vivas de ese bloque y día por orden de creación y
    se toman las primeras `total`. Todas las peticiones aplican exactamente el
    mismo criterio, así que si varias entran a la vez sobreviven justo las que
    caben y las demás se descartan: no hay sobreventa ni empates.
    """
    primeras = get_db().reservations.find(
        {'slotId': slot_id, 'reserva_date': fecha_iso, 'estado': {'$ne': 'CANCELADA'}},
        {'_id': 1},
    ).sort('_id', 1).limit(total)
    return oid in [d['_id'] for d in primeras]


# ──────────────────────────────────────────────────────────────────────────
# RESERVAS
# ──────────────────────────────────────────────────────────────────────────
def crear_reserva(datos: dict):
    """Registra una reserva y devuelve el documento guardado."""
    db = get_db()
    resultado = db.reservations.insert_one(datos)
    return db.reservations.find_one({'_id': resultado.inserted_id})


def eliminar_reserva(oid):
    """Borra una reserva. Solo se usa para deshacer una que no cabía."""
    return get_db().reservations.delete_one({'_id': oid})


def buscar_reserva(oid):
    """Devuelve la reserva con ese identificador, o None."""
    return get_db().reservations.find_one({'_id': oid})


def reservas_activas(email: str):
    """Las reservas vigentes de una persona."""
    return list(get_db().reservations.find({'email': email, 'estado': 'ACTIVA'}))


def reservas_activas_ordenadas(email: str):
    """Las reservas vigentes de una persona, de la más próxima a la más lejana."""
    return list(get_db().reservations.find(
        {'email': email, 'estado': 'ACTIVA'}).sort('reserva_date', 1))


def listar_reservas(filtro: dict, orden: str = 'created_at', sentido: int = -1):
    """Reservas que cumplen el filtro indicado."""
    return list(get_db().reservations.find(filtro).sort(orden, sentido))


def contar_reservas(filtro: dict) -> int:
    """Cuántas reservas cumplen el filtro indicado."""
    return get_db().reservations.count_documents(filtro)


def cambiar_estado_reserva(oid, estado_actual: str, cambios: dict, condiciones: dict = None):
    """Cambia el estado de una reserva SOLO si cumple lo que se le pide.

    Es una guardia atómica: una segunda cancelación de la misma reserva no
    vuelve a liberar el cupo. Con `condiciones` se añaden requisitos extra
    —por ejemplo, que la jornada de la reserva ya haya llegado—. Devuelve la
    reserva anterior al cambio, o None si no cumplía.
    """
    filtro = {'_id': oid, 'estado': estado_actual, **(condiciones or {})}
    return get_db().reservations.find_one_and_update(filtro, {'$set': cambios})


def marcar_asistencia(filtro: dict, registrada_por: str):
    """Pasa a COMPLETADA la primera reserva ACTIVA que cumpla el filtro.

    Devuelve la reserva anterior al cambio, o None si no había ninguna activa.
    """
    return get_db().reservations.find_one_and_update(
        filtro,
        {'$set': {'estado': 'COMPLETADA', 'completed_at': datetime.utcnow(),
                  'asistencia_registrada_por': registrada_por}},
    )


def tomar_reserva_pendiente(fecha_iso: str, procesado_por: str):
    """Pasa a NO_SHOW una reserva de la jornada que quedó sin asistencia.

    Toma una sola reserva por llamada y de forma atómica, para que dos
    entrenadores que cierren la jornada a la vez no cuenten dos veces la misma
    inasistencia. Devuelve None cuando ya no queda ninguna pendiente.
    """
    return get_db().reservations.find_one_and_update(
        {'estado': 'ACTIVA', 'reserva_date': {'$lte': fecha_iso}},
        {'$set': {'estado': 'NO_SHOW', 'no_show_at': datetime.utcnow(),
                  'procesado_por': procesado_por}},
    )
