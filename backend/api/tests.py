"""
PRUEBAS UNITARIAS DEL BACKEND — GESTIÓN DE RESERVAS DEL GIMNASIO

Cada clase cubre un requisito funcional y su nombre lo dice. Se ejecutan con:

    cd backend && python manage.py test api

Las pruebas no tocan la base de datos real: `setUp` sustituye la conexión de
`datos.py` por una MongoDB en memoria (mongomock), así cada prueba arranca con
el sistema vacío y no deja rastro.

REQUISITOS CUBIERTOS
    RF01  Registro con nombre, correo institucional y documento
    RF02  Inicio de sesión con el documento como contraseña
    RF03  Asignación automática del rol según el dominio del correo
    RF04  Perfil del estudiante: edad, peso, altura y objetivo
    RF05  Perfil de entrenadores y administradores
    RF08  Reserva del estudiante para el día siguiente
    RF09  Una única reserva por estudiante y día
    RF10  Consulta de las reservas hechas
    RF11  Búsqueda de la reserva por documento de identidad
    RF12  El personal visualiza los bloques sin poder reservar
    RF13  Registro de la asistencia del estudiante
    RF16  Penalización al alcanzar cinco inasistencias
    RF17  Historial de reservas, cancelaciones y asistencias
    RF18  Reporte personal de inasistencias y penalizaciones
    RF21  Creación de cuentas de administrador por el administrador principal
    RF23  Notificación de reserva confirmada
    RF25  Notificación de cancelación de reserva
"""
from datetime import timedelta

import mongomock
from django.test import TestCase
from rest_framework.test import APIClient

from api import arranque, datos, reglas

# ── Cuentas de ejemplo (el dominio del correo decide el rol) ───────────────
ESTUDIANTE, DOC_ESTUDIANTE = 'ana.gomez@soyudemedellin.edu.co', '1001234567'
COMPANERA, DOC_COMPANERA   = 'sara.ruiz@soyudemedellin.edu.co', '1009876543'
ENTRENADOR, DOC_ENTRENADOR = 'coach@udem.edu.co',              '7001112223'
ADMIN, DOC_ADMIN           = 'jefa@udemedellin.edu.co',        '3004445556'


class BaseGimnasio(TestCase):
    """Cimientos comunes: base de datos en memoria y atajos de uso frecuente."""

    def setUp(self):
        datos._client = mongomock.MongoClient()
        self.client = APIClient()

    def tearDown(self):
        datos._client = None

    # ── Atajos ────────────────────────────────────────────────────────────
    def registrar(self, email, documento, nombre='Persona de prueba'):
        return self.client.post('/api/auth/register/',
                                {'name': nombre, 'email': email, 'documento': documento},
                                format='json')

    def registrar_admin(self, email=ADMIN, documento=DOC_ADMIN, nombre='Persona admin'):
        """Da de alta un administrador por la vía real.

        El formulario público ya no crea administradores: los da de alta el
        administrador principal, que es la cuenta de arranque del sistema.
        """
        arranque.asegurar_administrador_principal()
        return self.client.post('/api/admin/users/', {
            'actor_email': arranque.CORREO, 'name': nombre,
            'email': email, 'documento': documento,
        }, format='json')

    def entrar(self, email, documento):
        return self.client.post('/api/auth/login/',
                                {'email': email, 'documento': documento}, format='json')

    def reservar(self, email, slot_id=1):
        return self.client.post('/api/reservations/',
                                {'email': email, 'slotId': slot_id}, format='json')

    def cancelar(self, reserva_id):
        return self.client.delete(f'/api/reservations/{reserva_id}/')

    def usuario(self, email):
        return datos.buscar_usuario(email)

    def bloque(self, slot_id=1):
        return datos.buscar_bloque(slot_id)

    def cupos_libres(self, slot_id=1, fecha=None):
        """Cupos libres de un bloque PARA UNA FECHA (por defecto, mañana).

        La ocupación se lleva por día, así que preguntar «cuántos cupos hay»
        sin decir cuándo no tiene sentido.
        """
        fecha = fecha or reglas.fecha_reserva().isoformat()
        return (self.bloque(slot_id)['total']
                - datos.ocupados_del_dia(fecha).get(slot_id, 0))

    def llenar_bloque(self, slot_id=1, fecha=None):
        """Deja un bloque sin cupos para esa fecha.

        Se ocupa con reservas reales de otros estudiantes, porque el aforo se
        mide contando reservas: no hay ningún contador que falsear.
        """
        fecha = fecha or reglas.fecha_reserva().isoformat()
        bloque = self.bloque(slot_id)
        datos.get_db().reservations.insert_many([{
            'email': f'relleno{i}@soyudemedellin.edu.co',
            'slotId': slot_id, 'hour': bloque['hour'],
            'reserva_date': fecha, 'estado': 'ACTIVA',
        } for i in range(bloque['total'])])

    def sembrar_bloques(self):
        """Los bloques se crean la primera vez que alguien los consulta."""
        self.client.get('/api/slots/')

    def hacer_que_llegue_la_jornada(self, email):
        """Adelanta el reloj: mueve la reserva del estudiante al día de hoy.

        Las reservas se crean SIEMPRE para el día siguiente, y la asistencia
        solo puede registrarse el día de la reserva. Para probar la asistencia
        sin esperar 24 horas, se retrasa la fecha de la reserva hasta hoy.
        """
        datos.get_db().reservations.update_many(
            {'email': email, 'estado': 'ACTIVA'},
            {'$set': {'reserva_date': reglas.hoy_local().isoformat()}},
        )


# ══════════════════════════════════════════════════════════════════════════
#  RF01 — REGISTRO CON NOMBRE, CORREO INSTITUCIONAL Y DOCUMENTO
# ══════════════════════════════════════════════════════════════════════════
class RF01Registro(BaseGimnasio):

    def test_registro_valido_crea_la_cuenta(self):
        resp = self.registrar(ESTUDIANTE, DOC_ESTUDIANTE, 'Ana Gómez')
        self.assertEqual(resp.status_code, 201)
        cuenta = self.usuario(ESTUDIANTE)
        self.assertEqual(cuenta['name'], 'Ana Gómez')
        self.assertEqual(cuenta['documento'], DOC_ESTUDIANTE)

    def test_la_contrasena_no_se_guarda_en_claro(self):
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        guardada = self.usuario(ESTUDIANTE)['password']
        self.assertNotEqual(guardada, DOC_ESTUDIANTE)
        self.assertIn(':', guardada)  # formato 'sal:clave' derivado

    def test_rechaza_correo_no_institucional(self):
        resp = self.registrar('alguien@gmail.com', '1234567890')
        self.assertEqual(resp.status_code, 400)

    def test_rechaza_correo_repetido(self):
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        resp = self.registrar(ESTUDIANTE, '9999999999')
        self.assertEqual(resp.status_code, 409)

    def test_rechaza_documento_repetido(self):
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        resp = self.registrar(COMPANERA, DOC_ESTUDIANTE)
        self.assertEqual(resp.status_code, 409)

    def test_rechaza_documento_demasiado_corto(self):
        resp = self.registrar(ESTUDIANTE, '123')
        self.assertEqual(resp.status_code, 400)

    def test_el_registro_publico_no_crea_administradores(self):
        """Si el formulario abierto creara administradores, cualquiera con un
        correo del dominio de administración se daría el mando del sistema."""
        resp = self.registrar(ADMIN, DOC_ADMIN)
        self.assertEqual(resp.status_code, 403)
        self.assertIsNone(self.usuario(ADMIN))

    def test_el_registro_publico_si_crea_estudiantes_y_entrenadores(self):
        self.assertEqual(self.registrar(ESTUDIANTE, DOC_ESTUDIANTE).status_code, 201)
        self.assertEqual(self.registrar(ENTRENADOR, DOC_ENTRENADOR).status_code, 201)

    def test_nadie_se_registra_como_administrador_principal(self):
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.assertFalse(self.usuario(ESTUDIANTE)['es_principal'])

    def test_rechaza_campos_vacios(self):
        resp = self.client.post('/api/auth/register/',
                                {'name': '', 'email': ESTUDIANTE, 'documento': DOC_ESTUDIANTE},
                                format='json')
        self.assertEqual(resp.status_code, 400)


# ══════════════════════════════════════════════════════════════════════════
#  RF02 — INICIO DE SESIÓN CON EL DOCUMENTO COMO CONTRASEÑA
# ══════════════════════════════════════════════════════════════════════════
class RF02InicioDeSesion(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE, 'Ana Gómez')

    def test_entra_con_credenciales_correctas(self):
        resp = self.entrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['email'], ESTUDIANTE)
        self.assertEqual(resp.data['role'], 'ESTUDIANTE')

    def test_no_entra_con_documento_incorrecto(self):
        resp = self.entrar(ESTUDIANTE, '0000000000')
        self.assertEqual(resp.status_code, 401)

    def test_no_entra_un_correo_que_no_existe(self):
        resp = self.entrar('fantasma@soyudemedellin.edu.co', DOC_ESTUDIANTE)
        self.assertEqual(resp.status_code, 401)

    def test_el_error_no_revela_si_el_correo_existe(self):
        """Ambos rechazos deben decir exactamente lo mismo: si el mensaje
        cambiara, cualquiera podría averiguar qué correos están registrados."""
        con_documento_malo = self.entrar(ESTUDIANTE, '0000000000').data['error']
        con_correo_inexistente = self.entrar('nadie@soyudemedellin.edu.co',
                                             DOC_ESTUDIANTE).data['error']
        self.assertEqual(con_documento_malo, con_correo_inexistente)

    def test_acepta_el_documento_escrito_con_puntos(self):
        resp = self.entrar(ESTUDIANTE, '1.001 234-567')
        self.assertEqual(resp.status_code, 200)

    def test_acepta_el_correo_en_mayusculas(self):
        resp = self.entrar(ESTUDIANTE.upper(), DOC_ESTUDIANTE)
        self.assertEqual(resp.status_code, 200)

    def test_la_respuesta_no_devuelve_la_contrasena_guardada(self):
        resp = self.entrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.assertNotIn('password', resp.data)

    def test_la_sesion_se_recupera_al_recargar_la_pagina(self):
        resp = self.client.get(f'/api/auth/session/?email={ESTUDIANTE}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['email'], ESTUDIANTE)


# ══════════════════════════════════════════════════════════════════════════
#  RF03 — ASIGNACIÓN AUTOMÁTICA DEL ROL SEGÚN EL DOMINIO
# ══════════════════════════════════════════════════════════════════════════
class RF03RolSegunDominio(BaseGimnasio):

    def test_dominio_de_estudiante_da_rol_estudiante(self):
        resp = self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.assertEqual(resp.data['role'], 'ESTUDIANTE')

    def test_dominio_de_profesor_da_rol_entrenador(self):
        resp = self.registrar(ENTRENADOR, DOC_ENTRENADOR)
        self.assertEqual(resp.data['role'], 'ENTRENADOR')

    def test_dominio_de_administracion_da_rol_admin(self):
        """El dominio sigue determinando el rol, pero esa cuenta ya no se crea
        desde el formulario público: la da de alta el administrador principal."""
        self.assertEqual(reglas.role_for_email(ADMIN), 'ADMIN')
        resp = self.registrar_admin()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['role'], 'ADMIN')

    def test_el_cliente_no_puede_elegir_su_rol(self):
        """Aunque pida ser ADMIN, el dominio del correo manda."""
        resp = self.client.post('/api/auth/register/', {
            'name': 'Aprovechada', 'email': ESTUDIANTE,
            'documento': DOC_ESTUDIANTE, 'role': 'ADMIN',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['role'], 'ESTUDIANTE')
        self.assertEqual(self.usuario(ESTUDIANTE)['role'], 'ESTUDIANTE')

    def test_un_dominio_parecido_no_cuela(self):
        resp = self.registrar('falsa@udemedellin.edu.co.otrositio.com', '1112223334')
        self.assertEqual(resp.status_code, 400)

    def test_la_funcion_de_rol_reconoce_los_tres_dominios(self):
        self.assertEqual(reglas.role_for_email(ESTUDIANTE), 'ESTUDIANTE')
        self.assertEqual(reglas.role_for_email(ENTRENADOR), 'ENTRENADOR')
        self.assertEqual(reglas.role_for_email(ADMIN), 'ADMIN')
        self.assertIsNone(reglas.role_for_email('alguien@gmail.com'))


# ══════════════════════════════════════════════════════════════════════════
#  RF04 — PERFIL DEL ESTUDIANTE: EDAD, PESO, ALTURA Y OBJETIVO
# ══════════════════════════════════════════════════════════════════════════
class RF04PerfilDelEstudiante(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE, 'Ana Gómez')

    def test_guarda_los_cuatro_datos_de_entrenamiento(self):
        resp = self.client.put('/api/users/profile/', {
            'email': ESTUDIANTE, 'edad': 21, 'peso': 68,
            'altura': 170, 'meta': 'Ganar resistencia',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['edad'], 21)
        self.assertEqual(resp.data['peso'], 68)
        self.assertEqual(resp.data['altura'], 170)
        self.assertEqual(resp.data['meta'], 'Ganar resistencia')

    def test_los_datos_guardados_se_recuperan_despues(self):
        self.client.put('/api/users/profile/',
                        {'email': ESTUDIANTE, 'meta': 'Ganar fuerza'}, format='json')
        resp = self.client.get(f'/api/users/profile/?email={ESTUDIANTE}')
        self.assertEqual(resp.data['meta'], 'Ganar fuerza')

    def test_el_perfil_no_deja_cambiar_el_rol_ni_el_documento(self):
        """Nombre, correo, documento y rol identifican a la persona: el
        formulario de entrenamiento no debe poder tocarlos."""
        self.client.put('/api/users/profile/', {
            'email': ESTUDIANTE, 'role': 'ADMIN', 'documento': '0000000000',
        }, format='json')
        cuenta = self.usuario(ESTUDIANTE)
        self.assertEqual(cuenta['role'], 'ESTUDIANTE')
        self.assertEqual(cuenta['documento'], DOC_ESTUDIANTE)

    # ── Validación de los datos de entrenamiento ──────────────────────────
    def test_rechaza_una_edad_negativa(self):
        resp = self.client.put('/api/users/profile/',
                               {'email': ESTUDIANTE, 'edad': -5}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIsNone(self.usuario(ESTUDIANTE).get('edad'))

    def test_rechaza_un_peso_negativo(self):
        resp = self.client.put('/api/users/profile/',
                               {'email': ESTUDIANTE, 'peso': -70}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_rechaza_una_altura_negativa(self):
        resp = self.client.put('/api/users/profile/',
                               {'email': ESTUDIANTE, 'altura': -170}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_la_edad_admitida_va_de_16_a_50_anos(self):
        for edad in (16, 33, 50):                       # los extremos entran
            resp = self.client.put('/api/users/profile/',
                                   {'email': ESTUDIANTE, 'edad': edad}, format='json')
            self.assertEqual(resp.status_code, 200, edad)
            self.assertEqual(resp.data['edad'], edad)
        for edad in (15, 51):                           # justo fuera, no
            resp = self.client.put('/api/users/profile/',
                                   {'email': ESTUDIANTE, 'edad': edad}, format='json')
            self.assertEqual(resp.status_code, 400, edad)
            self.assertIn('16', resp.data['error'])
            self.assertIn('50', resp.data['error'])

    def test_rechaza_valores_fuera_de_rango(self):
        for campo, valor in (('edad', 999), ('peso', 9999), ('altura', 5)):
            resp = self.client.put('/api/users/profile/',
                                   {'email': ESTUDIANTE, campo: valor}, format='json')
            self.assertEqual(resp.status_code, 400, campo)

    def test_rechaza_texto_donde_va_un_numero(self):
        for valor in ('muy alto', 'e', 'abc'):
            resp = self.client.put('/api/users/profile/',
                                   {'email': ESTUDIANTE, 'altura': valor}, format='json')
            self.assertEqual(resp.status_code, 400, valor)

    def test_un_dato_invalido_no_guarda_los_demas(self):
        """La actualización es todo o nada: si un campo falla, no se guarda
        ninguno y el perfil queda como estaba."""
        self.client.put('/api/users/profile/',
                        {'email': ESTUDIANTE, 'edad': 21, 'peso': -70}, format='json')
        self.assertIsNone(self.usuario(ESTUDIANTE).get('edad'))

    def test_se_puede_borrar_un_dato_dejandolo_vacio(self):
        self.client.put('/api/users/profile/',
                        {'email': ESTUDIANTE, 'peso': 68}, format='json')
        resp = self.client.put('/api/users/profile/',
                               {'email': ESTUDIANTE, 'peso': ''}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data['peso'])

    def test_rechaza_un_objetivo_demasiado_largo(self):
        resp = self.client.put('/api/users/profile/',
                               {'email': ESTUDIANTE, 'meta': 'x' * 200}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_perfil_de_un_correo_que_no_existe(self):
        resp = self.client.get('/api/users/profile/?email=nadie@soyudemedellin.edu.co')
        self.assertEqual(resp.status_code, 404)

    def test_exige_indicar_de_quien_es_el_perfil(self):
        resp = self.client.get('/api/users/profile/')
        self.assertEqual(resp.status_code, 400)


# ══════════════════════════════════════════════════════════════════════════
#  RF05 — PERFIL DE ENTRENADORES Y ADMINISTRADORES
# ══════════════════════════════════════════════════════════════════════════
class RF05PerfilDelPersonal(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ENTRENADOR, DOC_ENTRENADOR, 'Sebastián Coach')
        self.registrar_admin(nombre='Violeta Admin')

    def test_el_entrenador_ve_su_nombre_documento_y_rol(self):
        resp = self.client.get(f'/api/users/profile/?email={ENTRENADOR}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['name'], 'Sebastián Coach')
        self.assertEqual(resp.data['documento'], DOC_ENTRENADOR)
        self.assertEqual(resp.data['role'], 'ENTRENADOR')

    def test_el_administrador_ve_su_nombre_documento_y_rol(self):
        resp = self.client.get(f'/api/users/profile/?email={ADMIN}')
        self.assertEqual(resp.data['name'], 'Violeta Admin')
        self.assertEqual(resp.data['documento'], DOC_ADMIN)
        self.assertEqual(resp.data['role'], 'ADMIN')

    def test_solo_la_cuenta_de_arranque_es_la_principal(self):
        """Un administrador dado de alta por el principal no hereda el mando."""
        resp = self.client.get(f'/api/users/profile/?email={ADMIN}')
        self.assertFalse(resp.data['es_principal'])
        principal = self.client.get(f'/api/users/profile/?email={arranque.CORREO}')
        self.assertTrue(principal.data['es_principal'])

    def test_el_perfil_no_expone_la_contrasena(self):
        resp = self.client.get(f'/api/users/profile/?email={ENTRENADOR}')
        self.assertNotIn('password', resp.data)


# ══════════════════════════════════════════════════════════════════════════
#  RF08 — RESERVA DEL ESTUDIANTE PARA EL DÍA SIGUIENTE
# ══════════════════════════════════════════════════════════════════════════
class RF08Reserva(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.sembrar_bloques()

    def test_la_reserva_se_crea_y_queda_activa(self):
        resp = self.reservar(ESTUDIANTE, 1)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['estado'], 'ACTIVA')

    def test_la_reserva_queda_fechada_para_el_dia_siguiente(self):
        resp = self.reservar(ESTUDIANTE, 1)
        manana = reglas.hoy_local() + timedelta(days=1)
        self.assertEqual(resp.data['reserva_date'], manana.isoformat())

    def test_la_reserva_nunca_queda_fechada_para_hoy(self):
        resp = self.reservar(ESTUDIANTE, 1)
        self.assertNotEqual(resp.data['reserva_date'], reglas.hoy_local().isoformat())

    def test_el_estudiante_no_puede_imponer_otra_fecha(self):
        resp = self.client.post('/api/reservations/', {
            'email': ESTUDIANTE, 'slotId': 1, 'reserva_date': '2030-12-25',
        }, format='json')
        manana = reglas.hoy_local() + timedelta(days=1)
        self.assertEqual(resp.data['reserva_date'], manana.isoformat())

    def test_la_reserva_guarda_la_hora_del_bloque(self):
        resp = self.reservar(ESTUDIANTE, 1)
        self.assertEqual(resp.data['hour'], self.bloque(1)['hour'])

    def test_reservar_descuenta_exactamente_un_cupo(self):
        antes = self.cupos_libres(1)
        self.reservar(ESTUDIANTE, 1)
        self.assertEqual(self.cupos_libres(1), antes - 1)

    def test_reservar_no_cambia_la_capacidad_total(self):
        total_antes = self.bloque(1)['total']
        self.reservar(ESTUDIANTE, 1)
        self.assertEqual(self.bloque(1)['total'], total_antes)

    def test_rechaza_un_bloque_que_no_existe(self):
        resp = self.reservar(ESTUDIANTE, 99)
        self.assertEqual(resp.status_code, 404)

    def test_rechaza_a_un_usuario_no_registrado(self):
        resp = self.reservar('nadie@soyudemedellin.edu.co', 1)
        self.assertEqual(resp.status_code, 404)

    def test_rechaza_la_peticion_sin_bloque(self):
        resp = self.client.post('/api/reservations/', {'email': ESTUDIANTE}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_un_bloque_sin_cupos_rechaza_la_reserva(self):
        self.llenar_bloque(1)
        resp = self.reservar(ESTUDIANTE, 1)
        self.assertEqual(resp.status_code, 409)

    def test_los_cupos_de_un_bloque_se_cuentan_por_dia(self):
        """El arreglo del reinicio diario: lo reservado un día no descuenta
        cupos de otro. Antes había un único contador por bloque, sin fecha, y
        la disponibilidad iba bajando día tras día hasta agotar el gimnasio."""
        manana = reglas.fecha_reserva().isoformat()
        otro_dia = (reglas.fecha_reserva() + timedelta(days=1)).isoformat()
        self.reservar(ESTUDIANTE, 1)
        self.assertEqual(self.cupos_libres(1, manana), 19)
        self.assertEqual(self.cupos_libres(1, otro_dia), 20)

    def test_una_reserva_cumplida_no_descuenta_cupos_de_los_dias_siguientes(self):
        """El estudiante reservó, asistió y el día pasó: ese cupo pertenecía a
        aquella jornada y no puede seguir descontándose."""
        self.reservar(ESTUDIANTE, 1)
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        datos.get_db().reservations.update_many(
            {'email': ESTUDIANTE}, {'$set': {'estado': 'COMPLETADA'}})
        self.assertEqual(self.cupos_libres(1), 20)

    def test_el_rechazo_por_falta_de_cupo_no_crea_la_reserva(self):
        self.llenar_bloque(1)
        self.reservar(ESTUDIANTE, 1)
        self.assertEqual(datos.contar_reservas({'email': ESTUDIANTE}), 0)
        self.assertEqual(self.cupos_libres(1), 0)  # nunca queda negativo


# ══════════════════════════════════════════════════════════════════════════
#  RF09 — UNA ÚNICA RESERVA POR ESTUDIANTE Y DÍA
# ══════════════════════════════════════════════════════════════════════════
class RF09UnaReservaPorDia(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.sembrar_bloques()
        self.reservar(ESTUDIANTE, 1)

    def test_no_deja_reservar_un_segundo_bloque_el_mismo_dia(self):
        resp = self.reservar(ESTUDIANTE, 2)
        self.assertEqual(resp.status_code, 409)

    def test_tampoco_deja_repetir_el_mismo_bloque(self):
        resp = self.reservar(ESTUDIANTE, 1)
        self.assertEqual(resp.status_code, 409)

    def test_el_rechazo_no_descuenta_cupo_del_otro_bloque(self):
        antes = self.cupos_libres(2)
        self.reservar(ESTUDIANTE, 2)
        self.assertEqual(self.cupos_libres(2), antes)

    def test_el_estudiante_sigue_con_una_sola_reserva(self):
        self.reservar(ESTUDIANTE, 2)
        self.assertEqual(datos.contar_reservas({'email': ESTUDIANTE, 'estado': 'ACTIVA'}), 1)

    def test_tras_cancelar_puede_reservar_otro_bloque_del_dia(self):
        activa = datos.reservas_activas(ESTUDIANTE)[0]
        self.cancelar(str(activa['_id']))
        resp = self.reservar(ESTUDIANTE, 2)
        self.assertEqual(resp.status_code, 201)

    def test_el_limite_configurado_es_una_reserva(self):
        self.assertEqual(reglas.MAX_RESERVAS_POR_DIA, 1)


# ══════════════════════════════════════════════════════════════════════════
#  RF10 — CONSULTA DE LAS RESERVAS HECHAS
# ══════════════════════════════════════════════════════════════════════════
class RF10ConsultarReservas(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.registrar(COMPANERA, DOC_COMPANERA)
        self.sembrar_bloques()

    def test_devuelve_la_reserva_recien_creada(self):
        self.reservar(ESTUDIANTE, 1)
        resp = self.client.get(f'/api/reservations/?email={ESTUDIANTE}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_sin_reservas_devuelve_una_lista_vacia(self):
        resp = self.client.get(f'/api/reservations/?email={ESTUDIANTE}')
        self.assertEqual(resp.data, [])

    def test_no_muestra_las_reservas_canceladas(self):
        self.reservar(ESTUDIANTE, 1)
        activa = datos.reservas_activas(ESTUDIANTE)[0]
        self.cancelar(str(activa['_id']))
        resp = self.client.get(f'/api/reservations/?email={ESTUDIANTE}')
        self.assertEqual(resp.data, [])

    def test_cada_estudiante_ve_solo_lo_suyo(self):
        self.reservar(ESTUDIANTE, 1)
        self.reservar(COMPANERA, 2)
        resp = self.client.get(f'/api/reservations/?email={ESTUDIANTE}')
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['email'], ESTUDIANTE)

    def test_exige_indicar_de_quien_son_las_reservas(self):
        resp = self.client.get('/api/reservations/')
        self.assertEqual(resp.status_code, 400)


# ══════════════════════════════════════════════════════════════════════════
#  RF11 — BÚSQUEDA DE LA RESERVA POR DOCUMENTO DE IDENTIDAD
# ══════════════════════════════════════════════════════════════════════════
class RF11BuscarPorDocumento(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE, 'Ana Gómez')
        self.registrar(ENTRENADOR, DOC_ENTRENADOR)
        self.registrar_admin()
        self.sembrar_bloques()
        self.reservar(ESTUDIANTE, 1)

    def buscar(self, documento, actor):
        return self.client.get(
            f'/api/students/lookup/?documento={documento}&actor_email={actor}')

    def test_el_entrenador_encuentra_al_estudiante(self):
        resp = self.buscar(DOC_ESTUDIANTE, ENTRENADOR)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['estudiante']['name'], 'Ana Gómez')

    def test_devuelve_la_reserva_del_estudiante(self):
        resp = self.buscar(DOC_ESTUDIANTE, ENTRENADOR)
        self.assertTrue(resp.data['tiene_reserva'])
        self.assertEqual(len(resp.data['reservas']), 1)

    def test_el_administrador_tambien_puede_buscar(self):
        resp = self.buscar(DOC_ESTUDIANTE, ADMIN)
        self.assertEqual(resp.status_code, 200)

    def test_un_estudiante_no_puede_buscar_a_otro(self):
        resp = self.buscar(DOC_ESTUDIANTE, ESTUDIANTE)
        self.assertEqual(resp.status_code, 403)

    def test_documento_que_no_existe(self):
        resp = self.buscar('0000000000', ENTRENADOR)
        self.assertEqual(resp.status_code, 404)

    def test_exige_indicar_el_documento(self):
        resp = self.client.get(f'/api/students/lookup/?actor_email={ENTRENADOR}')
        self.assertEqual(resp.status_code, 400)

    def test_acepta_el_documento_escrito_con_puntos(self):
        resp = self.buscar('1.001.234.567', ENTRENADOR)
        self.assertEqual(resp.status_code, 200)


# ══════════════════════════════════════════════════════════════════════════
#  RF12 — EL PERSONAL VISUALIZA LOS BLOQUES SIN PODER RESERVAR
# ══════════════════════════════════════════════════════════════════════════
class RF12PersonalNoReserva(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.registrar(ENTRENADOR, DOC_ENTRENADOR)
        self.registrar_admin()
        self.sembrar_bloques()

    def test_el_entrenador_consulta_los_bloques_establecidos(self):
        resp = self.client.get('/api/slots/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['slots']), 6)

    def test_la_disponibilidad_de_cada_bloque_es_coherente(self):
        resp = self.client.get('/api/slots/')
        for bloque in resp.data['slots']:
            self.assertGreaterEqual(bloque['available'], 0)
            self.assertLessEqual(bloque['available'], bloque['total'])

    def test_el_entrenador_consulta_el_reporte_de_ocupacion(self):
        resp = self.client.get(f'/api/reports/occupancy/?actor_email={ENTRENADOR}')
        self.assertEqual(resp.status_code, 200)

    def test_el_administrador_ve_el_mismo_aforo_que_el_entrenador(self):
        del_entrenador = self.client.get(
            f'/api/reports/occupancy/?actor_email={ENTRENADOR}').data
        del_administrador = self.client.get(
            f'/api/reports/occupancy/?actor_email={ADMIN}').data
        self.assertEqual(del_entrenador, del_administrador)

    def test_el_entrenador_no_puede_reservar(self):
        resp = self.reservar(ENTRENADOR, 1)
        self.assertEqual(resp.status_code, 403)

    def test_el_administrador_no_puede_reservar(self):
        resp = self.reservar(ADMIN, 1)
        self.assertEqual(resp.status_code, 403)

    def test_el_intento_del_personal_no_consume_cupos(self):
        antes = self.cupos_libres(1)
        self.reservar(ENTRENADOR, 1)
        self.reservar(ADMIN, 1)
        self.assertEqual(self.cupos_libres(1), antes)

    def test_el_estudiante_si_puede_reservar_ese_bloque(self):
        self.reservar(ENTRENADOR, 1)
        resp = self.reservar(ESTUDIANTE, 1)
        self.assertEqual(resp.status_code, 201)

    def test_el_aforo_refleja_la_reserva_al_instante(self):
        antes = self.client.get(
            f'/api/reports/occupancy/?actor_email={ENTRENADOR}').data[0]['available']
        self.reservar(ESTUDIANTE, 1)
        despues = self.client.get(
            f'/api/reports/occupancy/?actor_email={ENTRENADOR}').data[0]['available']
        self.assertEqual(despues, antes - 1)


# ══════════════════════════════════════════════════════════════════════════
#  RF13 — REGISTRO DE LA ASISTENCIA DEL ESTUDIANTE
# ══════════════════════════════════════════════════════════════════════════
class RF13RegistrarAsistencia(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.registrar(ENTRENADOR, DOC_ENTRENADOR)
        self.registrar_admin()
        self.sembrar_bloques()
        self.reservar(ESTUDIANTE, 1)

    def registrar_asistencia(self, actor, documento=DOC_ESTUDIANTE):
        return self.client.post('/api/attendance/register/',
                                {'actor_email': actor, 'documento': documento},
                                format='json')

    def test_el_entrenador_registra_la_asistencia_el_dia_de_la_reserva(self):
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        resp = self.registrar_asistencia(ENTRENADOR)
        self.assertEqual(resp.status_code, 200)

    def test_la_reserva_queda_marcada_como_completada(self):
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        self.registrar_asistencia(ENTRENADOR)
        self.assertEqual(
            datos.contar_reservas({'email': ESTUDIANTE, 'estado': 'COMPLETADA'}), 1)

    def test_no_se_puede_registrar_antes_del_dia_de_la_reserva(self):
        """La reserva es para mañana: hoy el estudiante todavía no ha podido
        presentarse, así que ni asistió ni faltó."""
        resp = self.registrar_asistencia(ENTRENADOR)
        self.assertEqual(resp.status_code, 409)

    def test_el_administrador_tambien_registra_asistencia(self):
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        resp = self.registrar_asistencia(ADMIN)
        self.assertEqual(resp.status_code, 200)

    def test_un_estudiante_no_puede_registrar_asistencias(self):
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        resp = self.registrar_asistencia(ESTUDIANTE)
        self.assertEqual(resp.status_code, 403)

    def test_no_se_registra_dos_veces_la_misma_asistencia(self):
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        self.registrar_asistencia(ENTRENADOR)
        resp = self.registrar_asistencia(ENTRENADOR)
        self.assertEqual(resp.status_code, 404)

    def test_no_se_registra_asistencia_de_quien_no_reservo(self):
        self.registrar(COMPANERA, DOC_COMPANERA)
        resp = self.registrar_asistencia(ENTRENADOR, DOC_COMPANERA)
        self.assertEqual(resp.status_code, 404)

    def test_la_asistencia_no_suma_inasistencias(self):
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        self.registrar_asistencia(ENTRENADOR)
        self.assertEqual(self.usuario(ESTUDIANTE).get('no_show_count', 0), 0)


# ══════════════════════════════════════════════════════════════════════════
#  RF16 — PENALIZACIÓN AL ALCANZAR CINCO INASISTENCIAS
# ══════════════════════════════════════════════════════════════════════════
class RF16Penalizacion(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.registrar(ENTRENADOR, DOC_ENTRENADOR)
        self.sembrar_bloques()

    def faltar_una_vez(self, slot_id=1):
        """Reserva, deja pasar la jornada y marca la inasistencia."""
        self.reservar(ESTUDIANTE, slot_id)
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        reserva = datos.reservas_activas(ESTUDIANTE)[0]
        return self.client.post(f"/api/reservations/{reserva['_id']}/no-show/",
                                {'actor_email': ENTRENADOR}, format='json')

    def test_el_limite_establecido_es_de_cinco(self):
        self.assertEqual(reglas.NO_SHOW_LIMITE, 5)

    def test_cada_inasistencia_suma_al_contador(self):
        self.faltar_una_vez()
        self.assertEqual(self.usuario(ESTUDIANTE)['no_show_count'], 1)

    def test_con_cuatro_inasistencias_la_cuenta_sigue_activa(self):
        for i in range(4):
            self.faltar_una_vez(slot_id=(i % 6) + 1)
        cuenta = self.usuario(ESTUDIANTE)
        self.assertEqual(cuenta['no_show_count'], 4)
        self.assertEqual(cuenta['estado'], 'ACTIVO')

    def test_la_quinta_inasistencia_penaliza_la_cuenta(self):
        for i in range(4):
            self.faltar_una_vez(slot_id=(i % 6) + 1)
        resp = self.faltar_una_vez(slot_id=5)
        self.assertTrue(resp.data['penalizado'])
        self.assertEqual(self.usuario(ESTUDIANTE)['estado'], 'PENALIZADO')

    def test_la_cuenta_penalizada_no_puede_reservar(self):
        for i in range(5):
            self.faltar_una_vez(slot_id=(i % 6) + 1)
        resp = self.reservar(ESTUDIANTE, 6)
        self.assertEqual(resp.status_code, 403)

    def test_la_cuenta_penalizada_si_puede_iniciar_sesion(self):
        """La penalización impide reservar, no entrar a consultar."""
        for i in range(5):
            self.faltar_una_vez(slot_id=(i % 6) + 1)
        resp = self.entrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['estado'], 'PENALIZADO')

    def test_solo_el_personal_marca_inasistencias(self):
        self.reservar(ESTUDIANTE, 1)
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        reserva = datos.reservas_activas(ESTUDIANTE)[0]
        resp = self.client.post(f"/api/reservations/{reserva['_id']}/no-show/",
                                {'actor_email': ESTUDIANTE}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_no_se_marca_inasistencia_antes_del_dia_de_la_reserva(self):
        self.reservar(ESTUDIANTE, 1)
        reserva = datos.reservas_activas(ESTUDIANTE)[0]
        resp = self.client.post(f"/api/reservations/{reserva['_id']}/no-show/",
                                {'actor_email': ENTRENADOR}, format='json')
        self.assertEqual(resp.status_code, 409)

    def test_el_proceso_general_no_cierra_una_jornada_futura(self):
        self.reservar(ESTUDIANTE, 1)
        manana = (reglas.hoy_local() + timedelta(days=1)).isoformat()
        resp = self.client.post('/api/attendance/process/',
                                {'actor_email': ENTRENADOR, 'fecha': manana}, format='json')
        self.assertEqual(resp.data['total_procesadas'], 0)
        self.assertEqual(self.usuario(ESTUDIANTE).get('no_show_count', 0), 0)

    def test_el_proceso_general_marca_las_inasistencias_de_la_jornada(self):
        self.reservar(ESTUDIANTE, 1)
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        resp = self.client.post('/api/attendance/process/',
                                {'actor_email': ENTRENADOR}, format='json')
        self.assertEqual(resp.data['total_procesadas'], 1)
        self.assertEqual(self.usuario(ESTUDIANTE)['no_show_count'], 1)

    def test_procesar_dos_veces_no_cuenta_doble(self):
        self.reservar(ESTUDIANTE, 1)
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        self.client.post('/api/attendance/process/',
                         {'actor_email': ENTRENADOR}, format='json')
        resp = self.client.post('/api/attendance/process/',
                                {'actor_email': ENTRENADOR}, format='json')
        self.assertEqual(resp.data['total_procesadas'], 0)
        self.assertEqual(self.usuario(ESTUDIANTE)['no_show_count'], 1)


# ══════════════════════════════════════════════════════════════════════════
#  RF17 — HISTORIAL DE RESERVAS, CANCELACIONES Y ASISTENCIAS
# ══════════════════════════════════════════════════════════════════════════
class RF17Historial(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.registrar(ENTRENADOR, DOC_ENTRENADOR)
        self.sembrar_bloques()

    def historial(self, email=ESTUDIANTE, extra=''):
        return self.client.get(f'/api/reservations/history/?email={email}{extra}')

    def test_sin_actividad_el_historial_esta_vacio(self):
        self.assertEqual(self.historial().data, [])

    def test_incluye_la_reserva_vigente(self):
        self.reservar(ESTUDIANTE, 1)
        resp = self.historial()
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['estado'], 'ACTIVA')

    def test_incluye_las_reservas_canceladas(self):
        self.reservar(ESTUDIANTE, 1)
        reserva = datos.reservas_activas(ESTUDIANTE)[0]
        self.cancelar(str(reserva['_id']))
        estados = [h['estado'] for h in self.historial().data]
        self.assertIn('CANCELADA', estados)

    def test_incluye_las_asistencias(self):
        self.reservar(ESTUDIANTE, 1)
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        self.client.post('/api/attendance/register/',
                         {'actor_email': ENTRENADOR, 'documento': DOC_ESTUDIANTE},
                         format='json')
        estados = [h['estado'] for h in self.historial().data]
        self.assertIn('COMPLETADA', estados)

    def test_incluye_las_inasistencias(self):
        self.reservar(ESTUDIANTE, 1)
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        self.client.post('/api/attendance/process/',
                         {'actor_email': ENTRENADOR}, format='json')
        estados = [h['estado'] for h in self.historial().data]
        self.assertIn('NO_SHOW', estados)

    def test_el_filtro_de_pasadas_excluye_las_vigentes(self):
        self.reservar(ESTUDIANTE, 1)
        resp = self.historial(extra='&solo=pasadas')
        self.assertEqual(resp.data, [])

    def test_exige_indicar_de_quien_es_el_historial(self):
        resp = self.client.get('/api/reservations/history/')
        self.assertEqual(resp.status_code, 400)


# ══════════════════════════════════════════════════════════════════════════
#  RF18 — REPORTE PERSONAL DE INASISTENCIAS Y PENALIZACIONES
# ══════════════════════════════════════════════════════════════════════════
class RF18ReportePersonal(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE, 'Ana Gómez')
        self.registrar(ENTRENADOR, DOC_ENTRENADOR)
        self.sembrar_bloques()

    def reporte(self, email=ESTUDIANTE):
        return self.client.get(f'/api/reports/personal/?email={email}')

    def faltar_una_vez(self, slot_id=1):
        self.reservar(ESTUDIANTE, slot_id)
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        reserva = datos.reservas_activas(ESTUDIANTE)[0]
        self.client.post(f"/api/reservations/{reserva['_id']}/no-show/",
                         {'actor_email': ENTRENADOR}, format='json')

    def test_el_estudiante_consulta_su_reporte(self):
        resp = self.reporte()
        self.assertEqual(resp.status_code, 200)

    def test_el_reporte_trae_los_contadores_de_inasistencias(self):
        resp = self.reporte()
        for campo in ('no_show_count', 'no_show_limite', 'inasistencias_restantes'):
            self.assertIn(campo, resp.data)

    def test_sin_inasistencias_conserva_las_cinco_oportunidades(self):
        resp = self.reporte()
        self.assertEqual(resp.data['no_show_count'], 0)
        self.assertEqual(resp.data['inasistencias_restantes'], 5)

    def test_el_reporte_identifica_a_su_titular(self):
        resp = self.reporte()
        self.assertEqual(resp.data['name'], 'Ana Gómez')
        self.assertEqual(resp.data['documento'], DOC_ESTUDIANTE)

    def test_refleja_la_primera_inasistencia(self):
        self.faltar_una_vez()
        resp = self.reporte()
        self.assertEqual(resp.data['no_show_count'], 1)
        self.assertEqual(resp.data['inasistencias_restantes'], 4)

    def test_muestra_la_penalizacion_a_las_cinco_inasistencias(self):
        for i in range(5):
            self.faltar_una_vez(slot_id=(i % 6) + 1)
        resp = self.reporte()
        self.assertEqual(resp.data['estado'], 'PENALIZADO')
        self.assertTrue(resp.data['penalizado'])
        self.assertEqual(resp.data['inasistencias_restantes'], 0)

    def test_el_detalle_lista_cada_inasistencia(self):
        self.faltar_una_vez()
        resp = self.reporte()
        self.assertEqual(len(resp.data['inasistencias']), 1)

    def test_cuenta_las_asistencias_cumplidas(self):
        self.reservar(ESTUDIANTE, 1)
        self.hacer_que_llegue_la_jornada(ESTUDIANTE)
        self.client.post('/api/attendance/register/',
                         {'actor_email': ENTRENADOR, 'documento': DOC_ESTUDIANTE},
                         format='json')
        self.assertEqual(self.reporte().data['total_asistencias'], 1)

    def test_reporte_de_un_usuario_que_no_existe(self):
        resp = self.reporte('nadie@soyudemedellin.edu.co')
        self.assertEqual(resp.status_code, 404)

    def test_exige_indicar_de_quien_es_el_reporte(self):
        resp = self.client.get('/api/reports/personal/')
        self.assertEqual(resp.status_code, 400)


# ══════════════════════════════════════════════════════════════════════════
#  RF23 — NOTIFICACIÓN DE RESERVA CONFIRMADA
# ══════════════════════════════════════════════════════════════════════════
class RF23NotificacionDeReserva(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.registrar(COMPANERA, DOC_COMPANERA)
        self.registrar(ENTRENADOR, DOC_ENTRENADOR)
        self.sembrar_bloques()

    def test_la_reserva_confirmada_devuelve_un_aviso(self):
        resp = self.reservar(ESTUDIANTE, 1)
        self.assertTrue(resp.data['notificacion'])

    def test_el_aviso_se_identifica_como_confirmacion(self):
        resp = self.reservar(ESTUDIANTE, 1)
        self.assertEqual(resp.data['tipo'], 'RESERVA_CONFIRMADA')

    def test_el_aviso_menciona_la_hora_del_bloque(self):
        resp = self.reservar(ESTUDIANTE, 1)
        self.assertIn(resp.data['hour'], resp.data['notificacion'])

    def test_el_aviso_menciona_la_fecha_de_la_reserva(self):
        resp = self.reservar(ESTUDIANTE, 1)
        self.assertIn(resp.data['date'], resp.data['notificacion'])

    def test_al_reservar_otro_bloque_el_aviso_cambia_de_hora(self):
        primera = self.reservar(ESTUDIANTE, 1)
        segunda = self.reservar(COMPANERA, 6)
        self.assertIn(segunda.data['hour'], segunda.data['notificacion'])
        self.assertNotIn(primera.data['hour'], segunda.data['notificacion'])

    def test_cada_estudiante_recibe_su_propio_aviso(self):
        de_ana = self.reservar(ESTUDIANTE, 1).data['notificacion']
        de_sara = self.reservar(COMPANERA, 2).data['notificacion']
        self.assertNotEqual(de_ana, de_sara)

    def test_una_reserva_rechazada_no_confirma_nada(self):
        resp = self.reservar(ESTUDIANTE, 99)
        self.assertNotEqual(resp.data.get('tipo'), 'RESERVA_CONFIRMADA')

    def test_el_intento_del_personal_no_confirma_nada(self):
        resp = self.reservar(ENTRENADOR, 1)
        self.assertIsNone(resp.data.get('notificacion'))

    def test_consultar_las_reservas_no_repite_el_aviso(self):
        self.reservar(ESTUDIANTE, 1)
        resp = self.client.get(f'/api/reservations/?email={ESTUDIANTE}')
        self.assertNotIn('notificacion', resp.data[0])


# ══════════════════════════════════════════════════════════════════════════
#  RF25 — NOTIFICACIÓN DE CANCELACIÓN DE RESERVA
# ══════════════════════════════════════════════════════════════════════════
class RF25NotificacionDeCancelacion(BaseGimnasio):

    def setUp(self):
        super().setUp()
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        self.sembrar_bloques()
        self.reserva = self.reservar(ESTUDIANTE, 1).data

    def test_la_cancelacion_devuelve_un_aviso(self):
        resp = self.cancelar(self.reserva['id'])
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['notificacion'])

    def test_el_aviso_se_identifica_como_cancelacion(self):
        resp = self.cancelar(self.reserva['id'])
        self.assertEqual(resp.data['tipo'], 'RESERVA_CANCELADA')

    def test_el_aviso_menciona_la_hora_de_la_reserva_cancelada(self):
        resp = self.cancelar(self.reserva['id'])
        self.assertIn(self.reserva['hour'], resp.data['notificacion'])

    def test_el_aviso_informa_que_el_cupo_quedo_liberado(self):
        resp = self.cancelar(self.reserva['id'])
        self.assertIn('liberado', resp.data['notificacion'].lower())

    def test_la_cancelacion_devuelve_el_cupo_al_bloque(self):
        antes = self.cupos_libres(1)
        self.cancelar(self.reserva['id'])
        self.assertEqual(self.cupos_libres(1), antes + 1)

    def test_cancelar_dos_veces_no_duplica_el_cupo(self):
        self.cancelar(self.reserva['id'])
        despues_de_la_primera = self.cupos_libres(1)
        resp = self.cancelar(self.reserva['id'])
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self.cupos_libres(1), despues_de_la_primera)

    def test_un_identificador_mal_formado_se_rechaza(self):
        resp = self.cancelar('esto-no-es-un-identificador')
        self.assertEqual(resp.status_code, 400)

    # ── Cancelar NO es faltar ─────────────────────────────────────────────
    def test_cancelar_no_suma_ninguna_inasistencia(self):
        self.cancelar(self.reserva['id'])
        self.assertEqual(self.usuario(ESTUDIANTE).get('no_show_count', 0), 0)

    def test_las_cancelaciones_se_cuentan_aparte_de_las_inasistencias(self):
        resp = self.cancelar(self.reserva['id'])
        self.assertEqual(resp.data['cancel_count'], 1)
        self.assertEqual(resp.data['no_show_count'], 0)

    def test_cancelar_cinco_veces_no_penaliza_la_cuenta(self):
        """Cancelar a tiempo devuelve el cupo a otra persona: es el
        comportamiento que el gimnasio quiere, no una falta."""
        self.cancelar(self.reserva['id'])
        for slot in (2, 3, 4, 5):
            reserva = self.reservar(ESTUDIANTE, slot).data
            self.cancelar(reserva['id'])
        cuenta = self.usuario(ESTUDIANTE)
        self.assertEqual(cuenta['cancel_count'], 5)
        self.assertEqual(cuenta['estado'], 'ACTIVO')

    def test_cancelar_no_tiene_limite(self):
        """Cancelar es ilimitado: se cancela doce veces seguidas y la cuenta
        sigue intacta, sin inasistencias y sin sanción."""
        self.cancelar(self.reserva['id'])
        for i in range(11):
            reserva = self.reservar(ESTUDIANTE, (i % 6) + 1).data
            self.assertEqual(reserva.get('estado'), 'ACTIVA', f'no pudo reservar la vez {i + 2}')
            self.cancelar(reserva['id'])
        cuenta = self.usuario(ESTUDIANTE)
        self.assertEqual(cuenta['cancel_count'], 12)
        self.assertEqual(cuenta.get('no_show_count', 0), 0)
        self.assertEqual(cuenta['estado'], 'ACTIVO')

    def test_ninguna_regla_mira_el_contador_de_cancelaciones(self):
        """No existe límite de cancelaciones en las reglas del gimnasio."""
        self.assertFalse(hasattr(reglas, 'CANCELACION_LIMITE'))
        self.assertFalse(hasattr(reglas, 'alcanza_limite_cancelaciones'))

    def test_tras_cancelar_cinco_veces_todavia_puede_reservar(self):
        self.cancelar(self.reserva['id'])
        for slot in (2, 3, 4, 5):
            reserva = self.reservar(ESTUDIANTE, slot).data
            self.cancelar(reserva['id'])
        resp = self.reservar(ESTUDIANTE, 6)
        self.assertEqual(resp.status_code, 201)


# ══════════════════════════════════════════════════════════════════════════
#  RF21 — CREACIÓN DE CUENTAS DE ADMINISTRADOR
# ══════════════════════════════════════════════════════════════════════════
class RF21CuentasDeAdministrador(BaseGimnasio):
    """Solo el administrador principal crea administradores.

    El principal es la cuenta de arranque del sistema (`arranque.py`), que se
    asegura en cada encendido del servidor. Aquí se crea a mano porque las
    pruebas usan una base en memoria vacía.
    """

    OTRO_ADMIN, DOC_OTRO = 'suplente@udemedellin.edu.co', '3009998887'

    def setUp(self):
        super().setUp()
        arranque.asegurar_administrador_principal()
        self.principal = arranque.CORREO
        # El principal da de alta a un segundo administrador, que NO es principal.
        self.client.post('/api/admin/users/', {
            'actor_email': self.principal, 'name': 'Admin Suplente',
            'email': self.OTRO_ADMIN, 'documento': self.DOC_OTRO,
        }, format='json')

    def crear(self, actor, email, documento, nombre='Cuenta nueva'):
        return self.client.post('/api/admin/users/', {
            'actor_email': actor, 'name': nombre, 'email': email, 'documento': documento,
        }, format='json')

    # ── La cuenta de arranque ─────────────────────────────────────────────
    def test_la_cuenta_de_arranque_existe_y_es_la_principal(self):
        cuenta = self.usuario(arranque.CORREO)
        self.assertIsNotNone(cuenta)
        self.assertEqual(cuenta['role'], 'ADMIN')
        self.assertEqual(cuenta['estado'], 'ACTIVO')
        self.assertTrue(cuenta['es_principal'])

    def test_la_cuenta_de_arranque_entra_con_su_contrasena(self):
        resp = self.entrar(arranque.CORREO, arranque.CLAVE)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['role'], 'ADMIN')
        self.assertTrue(resp.data['es_principal'])

    def test_asegurarla_dos_veces_no_la_duplica(self):
        arranque.asegurar_administrador_principal()
        self.assertEqual(datos.contar_reservas({}), 0)
        self.assertEqual(
            len([u for u in datos.listar_usuarios() if u['email'] == arranque.CORREO]), 1)

    def test_si_la_desactivan_se_restaura_sola(self):
        """El sistema no puede quedarse sin administrador principal."""
        datos.actualizar_usuario(arranque.CORREO,
                                 {'role': 'SIN_ROL', 'estado': 'INACTIVO', 'es_principal': False})
        self.assertEqual(arranque.asegurar_administrador_principal(), 'restaurada')
        cuenta = self.usuario(arranque.CORREO)
        self.assertEqual(cuenta['role'], 'ADMIN')
        self.assertTrue(cuenta['es_principal'])

    # ── Quién puede crear qué ─────────────────────────────────────────────
    def test_el_principal_crea_administradores(self):
        resp = self.crear(self.principal, 'nueva.admin@udemedellin.edu.co', '3001112220')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['role'], 'ADMIN')

    def test_un_administrador_no_principal_no_crea_administradores(self):
        resp = self.crear(self.OTRO_ADMIN, 'colada@udemedellin.edu.co', '3001112221')
        self.assertEqual(resp.status_code, 403)
        self.assertIsNone(self.usuario('colada@udemedellin.edu.co'))

    def test_un_administrador_no_principal_si_crea_estudiantes(self):
        resp = self.crear(self.OTRO_ADMIN, 'nuevo.est@soyudemedellin.edu.co', '3001112222')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['role'], 'ESTUDIANTE')

    def test_un_administrador_no_principal_si_crea_entrenadores(self):
        resp = self.crear(self.OTRO_ADMIN, 'nuevo.coach@udem.edu.co', '3001112223')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['role'], 'ENTRENADOR')

    def test_un_estudiante_no_gestiona_usuarios(self):
        self.registrar(ESTUDIANTE, DOC_ESTUDIANTE)
        resp = self.crear(ESTUDIANTE, 'otra@soyudemedellin.edu.co', '3001112224')
        self.assertEqual(resp.status_code, 403)

    def test_la_cuenta_creada_por_el_principal_no_hereda_el_mando(self):
        self.crear(self.principal, 'tercera.admin@udemedellin.edu.co', '3001112225')
        self.assertFalse(self.usuario('tercera.admin@udemedellin.edu.co')['es_principal'])

    def test_el_rol_debe_coincidir_con_el_dominio(self):
        resp = self.client.post('/api/admin/users/', {
            'actor_email': self.principal, 'name': 'Incoherente',
            'email': 'quiere.mando@soyudemedellin.edu.co', 'documento': '3001112226',
            'role': 'ADMIN',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
