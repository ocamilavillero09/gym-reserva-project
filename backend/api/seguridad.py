"""
SEGURIDAD DE LAS CREDENCIALES

El documento de identidad es la contraseña con la que la persona inicia
sesión, así que nunca se guarda en claro en el campo `password`: se almacena
derivado con PBKDF2-SHA256 y una sal distinta para cada cuenta.

Esta capa no toca la base de datos ni responde peticiones: solo transforma y
compara credenciales.
"""
import hashlib
import os

ITERACIONES = 100_000
TAM_SAL = 32


def hash_password(password: str) -> str:
    """Deriva la contraseña con una sal nueva y devuelve 'sal:clave' en hexadecimal."""
    salt = os.urandom(TAM_SAL)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERACIONES)
    return salt.hex() + ':' + key.hex()


def verify_password(stored: str, provided: str) -> bool:
    """Compara la contraseña recibida con la almacenada, sin descifrar nada."""
    try:
        salt_hex, key_hex = stored.split(':')
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac('sha256', provided.encode(), salt, ITERACIONES)
        return key.hex() == key_hex
    except Exception:
        return False
