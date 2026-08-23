"""
CONFIGURACIÓN DE LA APLICACIÓN

Al arrancar el servidor se asegura que exista la cuenta de administrador
principal. Sin ella nadie podría crear administradores, porque el formulario de
registro ya no los admite.
"""
import sys

from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        # Durante las pruebas no se siembra: cada prueba levanta su propia base
        # en memoria y crea las cuentas que necesita.
        if 'test' in sys.argv:
            return

        from .arranque import asegurar_administrador_principal
        try:
            asegurar_administrador_principal()
        except Exception as error:  # noqa: BLE001
            # Si la base de datos todavía no responde, el servidor arranca
            # igual y se vuelve a intentar en el siguiente arranque.
            print(f'[arranque] no se pudo asegurar el administrador principal: {error}')
