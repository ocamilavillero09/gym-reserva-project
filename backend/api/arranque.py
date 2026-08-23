"""
CUENTA DE ADMINISTRADOR PRINCIPAL DEL SISTEMA

El gimnasio necesita SIEMPRE un administrador principal: es la única cuenta que
puede dar de alta a otros administradores. Si no existiera ninguno, nadie
podría crearlo —las cuentas de administrador ya no se pueden crear desde el
formulario de registro— y el sistema quedaría bloqueado.

Por eso esta cuenta se asegura en cada arranque del servidor: si no está, se
crea; y si alguien le retiró el rol o la desactivó, se restaura.

    Correo:     adan@udemedellin.edu.co
    Contraseña: admin12345   (el documento de identidad es la contraseña)

Esta capa se apoya en las otras tres: `reglas.py` para saber qué rol
corresponde, `datos.py` para consultar y guardar, y `seguridad.py` para la
contraseña.
"""
from datetime import datetime

from . import datos, reglas
from .seguridad import hash_password

CORREO = 'adan@udemedellin.edu.co'
CLAVE = 'admin12345'          # es a la vez el documento de identidad
NOMBRE = 'Adán Administrador'


def asegurar_administrador_principal() -> str:
    """Deja lista la cuenta de administrador principal. Devuelve qué hizo.

    Es idempotente: se puede llamar en cada arranque sin efectos secundarios.
    """
    cuenta = datos.buscar_usuario(CORREO)

    if cuenta is None:
        datos.crear_usuario({
            'name':      NOMBRE,
            'email':     CORREO,
            'documento': CLAVE,
            'password':  hash_password(CLAVE),
            'role':      reglas.role_for_email(CORREO),   # ADMIN por su dominio
            'estado':    'ACTIVO',
            'es_principal': True,
            'no_show_count': 0,
            'cancel_count':  0,
            'penalizado_hasta': None,
            'created_at': datetime.utcnow(),
        })
        return 'creada'

    # Si alguien le retiró el rol o la desactivó, se devuelve a su sitio: el
    # sistema no puede quedarse sin administrador principal.
    desviada = (cuenta.get('role') != 'ADMIN'
                or cuenta.get('estado') != 'ACTIVO'
                or not cuenta.get('es_principal'))
    if desviada:
        datos.actualizar_usuario(CORREO, {
            'role': 'ADMIN', 'estado': 'ACTIVO', 'es_principal': True,
        })
        return 'restaurada'

    return 'sin cambios'
