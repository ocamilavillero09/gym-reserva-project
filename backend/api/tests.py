"""
Pruebas unitarias del sistema de reservas.

Cubren los casos de uso críticos (views.py) y las reglas de negocio vigentes:

  RN01  Tres tipos de correo institucional -> rol (estudiante/profesor/admin)
  RN02  Profesores y administradores no reservan: solo consultan el aforo
  RN03  La reserva es siempre para el DÍA SIGUIENTE (y la fecha se expone)
  RN05  Una única reserva por día
  RN09  Penalización por inasistencias (No-Show)
  RN10  Penalización por cancelaciones + alerta previa

Se usa `mongomock` para simular MongoDB en memoria.
"""
from datetime import date, timedelta

import mongomock
from django.test import TestCase
from rest_framework.test import APIClient

from api import db as db_module

ESTUDIANTE = 'juan.perez@soyudemedellin.edu.co'
PROFESOR   = 'coach@udem.edu.co'
ADMIN      = 'jefe@udemedellin.edu.co'


class GymApiTestCase(TestCase):
    def setUp(self):
        db_module._client = mongomock.MongoClient()
        self.client = APIClient()

    def tearDown(self):
        db_module._client = None

    # Helpers ----------------------------------------------------------------
    def _register(self, email=ESTUDIANTE, name='Juan Perez', password='secreto123'):
        return self.client.post(
            '/api/auth/register/',
            {'name': name, 'email': email, 'password': password},
            format='json',
        )

    def _reserve(self, email, slot_id):
        return self.client.post('/api/reservations/', {'email': email, 'slotId': slot_id}, format='json')

    def _slot(self, slot_id):
        return db_module.get_db().slots.find_one({'slotId': slot_id})

    def _user(self, email):
        return db_module.get_db().users.find_one({'email': email})

    def _cancelar_n_veces(self, email, veces):
        """Reserva y cancela N veces para acumular cancelaciones."""
        for _ in range(veces):
            rid = self._reserve(email, 1).data['id']
            self.client.delete(f'/api/reservations/{rid}/')


# ── CU-1 / RN01: REGISTRO Y TRES TIPOS DE CORREO ────────────────────────────
class RegisterTests(GymApiTestCase):

    def test_registro_guarda_password_hasheada(self):
        resp = self._register()
        self.assertEqual(resp.status_code, 201)
        user = self._user(ESTUDIANTE)
        self.assertNotEqual(user['password'], 'secreto123')
        self.assertIn(':', user['password'])
        self.assertEqual(user['estado'], 'ACTIVO')
        self.assertEqual(user['cancel_count'], 0)

    def test_rn01_correo_de_estudiante_da_rol_estudiante(self):
        self.assertEqual(self._register().data['role'], 'ESTUDIANTE')
        self.assertEqual(self._user(ESTUDIANTE)['role'], 'ESTUDIANTE')

    def test_rn01_correo_udem_da_rol_entrenador(self):
        self.assertEqual(self._register(email=PROFESOR).data['role'], 'ENTRENADOR')

    def test_rn01_correo_udemedellin_da_rol_admin(self):
        self.assertEqual(self._register(email=ADMIN).data['role'], 'ADMIN')

    def test_rn01_no_se_puede_elegir_el_rol_desde_el_cliente(self):
        """Un correo de estudiante nunca produce un ADMIN, aunque lo pida."""
        resp = self.client.post(
            '/api/auth/register/',
            {'name': 'Vivo', 'email': ESTUDIANTE, 'password': 'secreto123', 'role': 'ADMIN'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._user(ESTUDIANTE)['role'], 'ESTUDIANTE')

    def test_rechaza_correo_no_institucional(self):
        self.assertEqual(self._register(email='juan@gmail.com').status_code, 400)

    def test_rechaza_password_corta(self):
        self.assertEqual(self._register(password='123').status_code, 400)

    def test_rechaza_correo_duplicado(self):
        self._register()
        self.assertEqual(self._register().status_code, 409)


# ── CU-2: LOGIN Y SESIÓN PERSISTENTE ────────────────────────────────────────
class LoginTests(GymApiTestCase):

    def test_login_devuelve_rol_estado_y_contadores(self):
        self._register()
        resp = self.client.post('/api/auth/login/',
                                {'email': ESTUDIANTE, 'password': 'secreto123'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['role'], 'ESTUDIANTE')
        self.assertEqual(resp.data['estado'], 'ACTIVO')
        self.assertEqual(resp.data['cancel_count'], 0)
        self.assertEqual(resp.data['cancelaciones_restantes'], db_module.CANCELACION_LIMITE)
        self.assertIsNone(resp.data['alerta'])

    def test_login_password_incorrecta(self):
        self._register()
        resp = self.client.post('/api/auth/login/',
                                {'email': ESTUDIANTE, 'password': 'mala'}, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_login_usuario_inexistente(self):
        resp = self.client.post('/api/auth/login/',
                                {'email': 'nadie@udem.edu.co', 'password': 'x'}, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_session_rehidrata_la_sesion_al_recargar(self):
        """El frontend consulta este endpoint tras un F5 en vez de cerrar sesión."""
        self._register()
        resp = self.client.get(f'/api/auth/session/?email={ESTUDIANTE}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['email'], ESTUDIANTE)
        self.assertEqual(resp.data['role'], 'ESTUDIANTE')

    def test_session_de_usuario_inexistente(self):
        self.assertEqual(self.client.get('/api/auth/session/?email=nadie@udem.edu.co').status_code, 404)


# ── GESTIÓN DE USUARIOS POR EL ADMINISTRADOR ────────────────────────────────
class AdminUserTests(GymApiTestCase):
    def setUp(self):
        super().setUp()
        self._register(email=ADMIN, name='Jefa')

    def _crear(self, actor, email, name='Nuevo', password='secreto123', role=None):
        body = {'actor_email': actor, 'name': name, 'email': email, 'password': password}
        if role:
            body['role'] = role
        return self.client.post('/api/admin/users/', body, format='json')

    def test_admin_crea_otro_administrador(self):
        resp = self._crear(ADMIN, 'nueva.admin@udemedellin.edu.co')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['role'], 'ADMIN')
        self.assertEqual(self._user('nueva.admin@udemedellin.edu.co')['role'], 'ADMIN')

    def test_admin_crea_profesor_y_estudiante(self):
        self.assertEqual(self._crear(ADMIN, PROFESOR).data['role'], 'ENTRENADOR')
        self.assertEqual(self._crear(ADMIN, ESTUDIANTE).data['role'], 'ESTUDIANTE')

    def test_estudiante_no_puede_crear_usuarios(self):
        self._register()
        self.assertEqual(self._crear(ESTUDIANTE, 'otra@udemedellin.edu.co').status_code, 403)

    def test_profesor_no_puede_crear_usuarios(self):
        self._register(email=PROFESOR)
        self.assertEqual(self._crear(PROFESOR, 'otra@udemedellin.edu.co').status_code, 403)

    def test_rol_pedido_debe_coincidir_con_el_dominio(self):
        resp = self._crear(ADMIN, ESTUDIANTE, role='ADMIN')
        self.assertEqual(resp.status_code, 400)

    def test_correo_no_institucional_rechazado(self):
        self.assertEqual(self._crear(ADMIN, 'externo@gmail.com').status_code, 400)

    def test_correo_duplicado(self):
        self._crear(ADMIN, PROFESOR)
        self.assertEqual(self._crear(ADMIN, PROFESOR).status_code, 409)

    def test_admin_lista_usuarios(self):
        self._crear(ADMIN, ESTUDIANTE)
        resp = self.client.get(f'/api/admin/users/?actor_email={ADMIN}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)


# ── CU-3 / RN03: CONSULTA DE CUPOS Y FECHA DEL DÍA SIGUIENTE ────────────────
class SlotsTests(GymApiTestCase):
    def test_slots_se_siembran_y_devuelven(self):
        resp = self.client.get('/api/slots/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['slots']), 6)
        self.assertEqual(resp.data['slots'][0]['available'], 20)

    def test_rn03_la_respuesta_expone_la_fecha_del_dia_siguiente(self):
        resp = self.client.get('/api/slots/')
        esperado = db_module.hoy_local() + timedelta(days=1)
        self.assertEqual(resp.data['fecha'], esperado.isoformat())
        # La etiqueta legible se muestra en la interfaz ("martes 18 de agosto de 2026").
        self.assertIn(str(esperado.day), resp.data['fecha_label'])
        self.assertIn('de', resp.data['fecha_label'])

    def test_formato_fecha_en_espanol(self):
        etiqueta = db_module.formato_fecha_es(date(2026, 8, 18))
        self.assertEqual(etiqueta, 'martes 18 de agosto de 2026')


# ── CU-4 / RN02 / RN05: CREAR RESERVA ───────────────────────────────────────
class ReservationTests(GymApiTestCase):
    def setUp(self):
        super().setUp()
        self._register()
        self.client.get('/api/slots/')

    def test_reserva_descuenta_cupo(self):
        resp = self._reserve(ESTUDIANTE, 1)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['estado'], 'ACTIVA')
        self.assertEqual(self._slot(1)['available'], 19)

    def test_rn03_la_reserva_queda_fechada_para_manana(self):
        resp = self._reserve(ESTUDIANTE, 1)
        manana = db_module.hoy_local() + timedelta(days=1)
        self.assertEqual(resp.data['reserva_date'], manana.isoformat())
        self.assertEqual(resp.data['date'], db_module.formato_fecha_es(manana))

    def test_rn05_solo_una_reserva_por_dia(self):
        self.assertEqual(self._reserve(ESTUDIANTE, 1).status_code, 201)
        # Un segundo bloque el mismo día se rechaza y no descuenta cupo.
        resp = self._reserve(ESTUDIANTE, 2)
        self.assertEqual(resp.status_code, 409)
        self.assertIn('una reserva por día', resp.data['error'])
        self.assertEqual(self._slot(2)['available'], 20)

    def test_rn05_repetir_el_mismo_bloque_tambien_se_rechaza(self):
        self._reserve(ESTUDIANTE, 1)
        self.assertEqual(self._reserve(ESTUDIANTE, 1).status_code, 409)
        self.assertEqual(self._slot(1)['available'], 19)

    def test_rn05_tras_cancelar_puede_reservar_otro_bloque_del_dia(self):
        rid = self._reserve(ESTUDIANTE, 1).data['id']
        self.client.delete(f'/api/reservations/{rid}/')
        self.assertEqual(self._reserve(ESTUDIANTE, 3).status_code, 201)

    def test_rn02_el_profesor_no_puede_reservar(self):
        self._register(email=PROFESOR, name='Coach')
        resp = self._reserve(PROFESOR, 1)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self._slot(1)['available'], 20)

    def test_rn02_el_administrador_no_puede_reservar(self):
        self._register(email=ADMIN, name='Jefa')
        self.assertEqual(self._reserve(ADMIN, 1).status_code, 403)

    def test_usuario_inexistente_no_reserva(self):
        self.assertEqual(self._reserve('fantasma@soyudemedellin.edu.co', 1).status_code, 404)

    def test_rechaza_sin_cupos(self):
        db_module.get_db().slots.update_one({'slotId': 1}, {'$set': {'available': 0}})
        self.assertEqual(self._reserve(ESTUDIANTE, 1).status_code, 409)

    def test_rechaza_slot_inexistente(self):
        self.assertEqual(self._reserve(ESTUDIANTE, 999).status_code, 404)

    def test_descuento_atomico_no_sobrevende(self):
        self._register(email='ana.gomez@soyudemedellin.edu.co', name='Ana Gomez')
        db_module.get_db().slots.update_one({'slotId': 1}, {'$set': {'available': 1}})
        r1 = self._reserve(ESTUDIANTE, 1)
        r2 = self._reserve('ana.gomez@soyudemedellin.edu.co', 1)
        self.assertEqual(sorted([r1.status_code, r2.status_code]), [201, 409])
        self.assertEqual(self._slot(1)['available'], 0)

    def test_solo_muestra_activas(self):
        r = self._reserve(ESTUDIANTE, 1)
        self.client.delete(f"/api/reservations/{r.data['id']}/")
        listado = self.client.get(f'/api/reservations/?email={ESTUDIANTE}')
        self.assertEqual(len(listado.data), 0)  # la cancelada no aparece


# ── CU-5 / RN10: CANCELAR, CONTADOR Y ALERTA ────────────────────────────────
class CancelTests(GymApiTestCase):
    def setUp(self):
        super().setUp()
        self._register()
        self.client.get('/api/slots/')
        self.rid = self._reserve(ESTUDIANTE, 1).data['id']

    def test_cancelar_libera_cupo(self):
        self.assertEqual(self._slot(1)['available'], 19)
        resp = self.client.delete(f'/api/reservations/{self.rid}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._slot(1)['available'], 20)

    def test_doble_cancelacion_no_suma_cupo_ni_contador(self):
        self.client.delete(f'/api/reservations/{self.rid}/')
        resp = self.client.delete(f'/api/reservations/{self.rid}/')
        self.assertEqual(resp.status_code, 409)          # ya no está activa
        self.assertEqual(self._slot(1)['available'], 20)
        self.assertEqual(self._user(ESTUDIANTE)['cancel_count'], 1)

    def test_id_invalido(self):
        self.assertEqual(self.client.delete('/api/reservations/no-es-objectid/').status_code, 400)

    def test_rn10_cada_cancelacion_suma_al_contador(self):
        resp = self.client.delete(f'/api/reservations/{self.rid}/')
        self.assertEqual(resp.data['cancel_count'], 1)
        self.assertEqual(resp.data['cancelaciones_restantes'], db_module.CANCELACION_LIMITE - 1)
        self.assertFalse(resp.data['penalizado'])
        self.assertIsNone(resp.data['alerta'])           # aún lejos del límite

    def test_rn10_alerta_cuando_faltan_dos_cancelaciones(self):
        """Con 3 de 5 cancelaciones la app avisa que faltan 2 para la penalización."""
        self.client.delete(f'/api/reservations/{self.rid}/')          # 1
        self._cancelar_n_veces(ESTUDIANTE, 2)                          # 2 y 3
        user = self._user(ESTUDIANTE)
        self.assertEqual(user['cancel_count'], 3)
        alerta = db_module.alerta_cancelaciones(user)
        self.assertIsNotNone(alerta)
        self.assertIn('2 cancelaciones de ser penalizado', alerta)
        self.assertEqual(user['estado'], 'ACTIVO')                     # todavía no penalizado

    def test_rn10_quinta_cancelacion_penaliza_y_bloquea(self):
        self.client.delete(f'/api/reservations/{self.rid}/')           # 1
        self._cancelar_n_veces(ESTUDIANTE, 3)                          # 2, 3 y 4
        rid = self._reserve(ESTUDIANTE, 1).data['id']
        resp = self.client.delete(f'/api/reservations/{rid}/')         # 5 -> penaliza
        self.assertTrue(resp.data['penalizado'])
        self.assertEqual(resp.data['cancelaciones_restantes'], 0)
        self.assertEqual(self._user(ESTUDIANTE)['estado'], 'PENALIZADO')
        # Penalizado: no puede volver a reservar.
        self.assertEqual(self._reserve(ESTUDIANTE, 2).status_code, 403)


# ── RN09: NO-SHOW Y PENALIZACIÓN ────────────────────────────────────────────
class NoShowTests(GymApiTestCase):
    def setUp(self):
        super().setUp()
        self._register(email=PROFESOR, name='Coach')
        self._register(email=ESTUDIANTE, name='Estudiante')
        self.client.get('/api/slots/')

    def _no_show(self, rid):
        return self.client.post(f'/api/reservations/{rid}/no-show/',
                                {'actor_email': PROFESOR}, format='json')

    def test_solo_el_profesor_marca_no_show(self):
        rid = self._reserve(ESTUDIANTE, 1).data['id']
        resp = self.client.post(f'/api/reservations/{rid}/no-show/',
                                {'actor_email': ESTUDIANTE}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_tres_no_show_penaliza_y_bloquea_reserva(self):
        for _ in range(3):
            rid = self._reserve(ESTUDIANTE, 1).data['id']
            self._no_show(rid)
        self.assertEqual(self._user(ESTUDIANTE)['estado'], 'PENALIZADO')
        resp = self._reserve(ESTUDIANTE, 2)
        self.assertEqual(resp.status_code, 403)


# ── RF11–RF19: FEATURES COMPLEMENTARIAS ─────────────────────────────────────
class FeaturesTests(GymApiTestCase):
    ANA = 'ana@soyudemedellin.edu.co'

    def setUp(self):
        super().setUp()
        self._register(email=PROFESOR, name='Coach')
        self._register(email=self.ANA, name='Ana')
        self.client.get('/api/slots/')

    def test_rf11_historial_incluye_canceladas(self):
        rid = self._reserve(self.ANA, 1).data['id']
        self.client.delete(f'/api/reservations/{rid}/')
        resp = self.client.get(f'/api/reservations/history/?email={self.ANA}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['estado'], 'CANCELADA')

    def test_rf17_completar_asistencia(self):
        rid = self._reserve(self.ANA, 1).data['id']
        resp = self.client.post(f'/api/reservations/{rid}/complete/',
                                {'actor_email': PROFESOR}, format='json')
        self.assertEqual(resp.status_code, 200)
        hist = self.client.get(f'/api/reservations/history/?email={self.ANA}')
        self.assertEqual(hist.data[0]['estado'], 'COMPLETADA')

    def test_rf12_lista_de_espera(self):
        db_module.get_db().slots.update_one({'slotId': 1}, {'$set': {'available': 0}})
        r1 = self.client.post('/api/slots/1/waitlist/', {'email': self.ANA}, format='json')
        self.assertEqual(r1.status_code, 201)
        r2 = self.client.post('/api/slots/1/waitlist/', {'email': self.ANA}, format='json')
        self.assertEqual(r2.status_code, 409)

    def test_rf12_no_lista_si_hay_cupos(self):
        resp = self.client.post('/api/slots/1/waitlist/', {'email': self.ANA}, format='json')
        self.assertEqual(resp.status_code, 409)

    def test_rf13_perfil_fisico(self):
        resp = self.client.put('/api/users/profile/',
                               {'email': self.ANA, 'peso': 65, 'altura': 170, 'meta': 'Resistencia'},
                               format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['peso'], 65)
        self.assertEqual(resp.data['meta'], 'Resistencia')

    def test_rf13_el_perfil_muestra_las_cancelaciones_del_estudiante(self):
        rid = self._reserve(self.ANA, 1).data['id']
        self.client.delete(f'/api/reservations/{rid}/')
        resp = self.client.get(f'/api/users/profile/?email={self.ANA}')
        self.assertEqual(resp.data['cancel_count'], 1)
        self.assertEqual(resp.data['cancelacion_limite'], db_module.CANCELACION_LIMITE)
        self.assertEqual(resp.data['cancelaciones_restantes'], db_module.CANCELACION_LIMITE - 1)

    def test_rf15_calificacion(self):
        self.client.post('/api/ratings/', {'email': self.ANA, 'stars': 5, 'comment': 'Excelente'}, format='json')
        self.client.post('/api/ratings/', {'email': self.ANA, 'stars': 3}, format='json')
        resp = self.client.get('/api/ratings/')
        self.assertEqual(resp.data['total'], 2)
        self.assertEqual(resp.data['promedio'], 4.0)

    def test_rf15_stars_invalido(self):
        resp = self.client.post('/api/ratings/', {'email': self.ANA, 'stars': 9}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_rf16_occupancy(self):
        self._reserve(self.ANA, 1)
        resp = self.client.get('/api/reports/occupancy/')
        self.assertEqual(resp.status_code, 200)
        bloque1 = next(b for b in resp.data if b['slotId'] == 1)
        self.assertEqual(bloque1['reservados'], 1)

    def test_rf17_reporte_por_estudiante(self):
        """El reporte sale por persona: solo estudiantes, con sus contadores."""
        rid = self._reserve(self.ANA, 1).data['id']
        self.client.delete(f'/api/reservations/{rid}/')
        resp = self.client.get('/api/reports/students/')
        self.assertEqual(resp.status_code, 200)
        estudiantes = resp.data['estudiantes']
        # El profesor NO aparece: el reporte es de estudiantes.
        self.assertEqual([e['email'] for e in estudiantes], [self.ANA])
        fila = estudiantes[0]
        self.assertEqual(fila['canceladas'], 1)
        self.assertEqual(fila['cancel_count'], 1)
        self.assertEqual(fila['cancelaciones_restantes'], db_module.CANCELACION_LIMITE - 1)
        self.assertFalse(fila['en_alerta'])

    def test_rf17_el_reporte_marca_a_quien_esta_en_alerta(self):
        for _ in range(3):
            rid = self._reserve(self.ANA, 1).data['id']
            self.client.delete(f'/api/reservations/{rid}/')
        fila = self.client.get('/api/reports/students/').data['estudiantes'][0]
        self.assertEqual(fila['cancel_count'], 3)
        self.assertTrue(fila['en_alerta'])

    def test_rf18_maquinas_seed_y_mantenimiento(self):
        listado = self.client.get('/api/machines/')
        self.assertEqual(len(listado.data), 5)
        # Estudiante NO puede cambiar estado
        deny = self.client.patch('/api/machines/1/', {'actor_email': self.ANA, 'estado': 'FUERA_DE_SERVICIO'}, format='json')
        self.assertEqual(deny.status_code, 403)
        # Profesor SÍ
        ok = self.client.patch('/api/machines/1/', {'actor_email': PROFESOR, 'estado': 'FUERA_DE_SERVICIO', 'note': 'Mantenimiento'}, format='json')
        self.assertEqual(ok.status_code, 200)
        m = db_module.get_db().machines.find_one({'machineId': 1})
        self.assertEqual(m['estado'], 'FUERA_DE_SERVICIO')

    def test_rf19_csv_export_por_estudiante(self):
        resp = self.client.get('/api/reports/usage.csv')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp['Content-Type'])
        cuerpo = resp.content.decode()
        self.assertIn('email', cuerpo)
        self.assertIn('canceladas', cuerpo)
        self.assertIn(self.ANA, cuerpo)
