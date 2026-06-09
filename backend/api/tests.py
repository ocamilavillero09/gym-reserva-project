"""
Pruebas unitarias del sistema de reservas.

Cubren los casos de uso críticos (views.py) y las reglas de negocio del
documento de análisis: RN05 (máx. 2 activas), RN07 (1 por bloque), RN09
(penalización por No-Show) y RF07 (reserva por entrenador). Se usa `mongomock`
para simular MongoDB en memoria.
"""
import mongomock
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api import db as db_module


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class GymApiTestCase(TestCase):
    def setUp(self):
        db_module._client = mongomock.MongoClient()
        self.client = APIClient()

    def tearDown(self):
        db_module._client = None

    # Helpers ----------------------------------------------------------------
    def _register(self, email='juan.perez@udem.edu.co', name='Juan Perez',
                  password='secreto123', role=None):
        body = {'name': name, 'email': email, 'password': password}
        if role:
            body['role'] = role
        return self.client.post('/api/auth/register/', body, format='json')

    def _reserve(self, email, slot_id, actor_email=None):
        body = {'email': email, 'slotId': slot_id}
        if actor_email:
            body['actor_email'] = actor_email
        return self.client.post('/api/reservations/', body, format='json')

    def _slot(self, slot_id):
        return db_module.get_db().slots.find_one({'slotId': slot_id})

    def _user(self, email):
        return db_module.get_db().users.find_one({'email': email})


# ── CU-1: REGISTRO ────────────────────────────────────────────────────────
class RegisterTests(GymApiTestCase):

    def test_registro_exitoso_guarda_password_hasheada_y_rol(self):
        resp = self._register()
        self.assertEqual(resp.status_code, 201)
        user = self._user('juan.perez@udem.edu.co')
        self.assertNotEqual(user['password'], 'secreto123')
        self.assertIn(':', user['password'])
        self.assertEqual(user['role'], 'ESTUDIANTE')   # rol por defecto
        self.assertEqual(user['estado'], 'ACTIVO')

    def test_puede_crear_entrenador(self):
        resp = self._register(email='coach@udem.edu.co', role='ENTRENADOR')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._user('coach@udem.edu.co')['role'], 'ENTRENADOR')

    def test_rol_invalido_rechazado(self):
        resp = self._register(email='x@udem.edu.co', role='SUPERMAN')
        self.assertEqual(resp.status_code, 400)

    def test_rechaza_correo_no_institucional(self):
        self.assertEqual(self._register(email='juan@gmail.com').status_code, 400)

    def test_rechaza_password_corta(self):
        self.assertEqual(self._register(password='123').status_code, 400)

    def test_rechaza_correo_duplicado(self):
        self._register()
        self.assertEqual(self._register().status_code, 409)


# ── CU-2: LOGIN ─────────────────────────────────────────────────────────────
class LoginTests(GymApiTestCase):

    def test_login_correcto_devuelve_rol_y_estado(self):
        self._register()
        resp = self.client.post('/api/auth/login/',
                                {'email': 'juan.perez@udem.edu.co', 'password': 'secreto123'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['role'], 'ESTUDIANTE')
        self.assertEqual(resp.data['estado'], 'ACTIVO')

    def test_login_password_incorrecta(self):
        self._register()
        resp = self.client.post('/api/auth/login/',
                                {'email': 'juan.perez@udem.edu.co', 'password': 'mala'}, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_login_usuario_inexistente(self):
        resp = self.client.post('/api/auth/login/',
                                {'email': 'nadie@udem.edu.co', 'password': 'x'}, format='json')
        self.assertEqual(resp.status_code, 401)


# ── CU-3: CONSULTA DE CUPOS ─────────────────────────────────────────────────
class SlotsTests(GymApiTestCase):
    def test_slots_se_siembran_y_devuelven(self):
        resp = self.client.get('/api/slots/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 6)
        self.assertEqual(resp.data[0]['available'], 20)


# ── CU-4: CREAR RESERVA ─────────────────────────────────────────────────────
class ReservationTests(GymApiTestCase):
    def setUp(self):
        super().setUp()
        self._register()
        self.client.get('/api/slots/')

    def test_reserva_descuenta_cupo(self):
        resp = self._reserve('juan.perez@udem.edu.co', 1)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['estado'], 'ACTIVA')
        self.assertEqual(self._slot(1)['available'], 19)

    def test_usuario_inexistente_no_reserva(self):
        self.assertEqual(self._reserve('fantasma@udem.edu.co', 1).status_code, 404)

    def test_rn07_no_doble_reserva_mismo_bloque(self):
        self._reserve('juan.perez@udem.edu.co', 1)
        resp = self._reserve('juan.perez@udem.edu.co', 1)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self._slot(1)['available'], 19)

    def test_rn05_maximo_dos_reservas_activas(self):
        self.assertEqual(self._reserve('juan.perez@udem.edu.co', 1).status_code, 201)
        self.assertEqual(self._reserve('juan.perez@udem.edu.co', 2).status_code, 201)
        # La tercera debe ser rechazada (límite = 2).
        resp = self._reserve('juan.perez@udem.edu.co', 3)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self._slot(3)['available'], 20)  # no descontó

    def test_rechaza_sin_cupos(self):
        db_module.get_db().slots.update_one({'slotId': 1}, {'$set': {'available': 0}})
        self.assertEqual(self._reserve('juan.perez@udem.edu.co', 1).status_code, 409)

    def test_rechaza_slot_inexistente(self):
        self.assertEqual(self._reserve('juan.perez@udem.edu.co', 999).status_code, 404)

    def test_descuento_atomico_no_sobrevende(self):
        self._register(email='ana.gomez@udem.edu.co', name='Ana Gomez')
        db_module.get_db().slots.update_one({'slotId': 1}, {'$set': {'available': 1}})
        r1 = self._reserve('juan.perez@udem.edu.co', 1)
        r2 = self._reserve('ana.gomez@udem.edu.co', 1)
        self.assertEqual(sorted([r1.status_code, r2.status_code]), [201, 409])
        self.assertEqual(self._slot(1)['available'], 0)

    def test_solo_muestra_activas(self):
        r = self._reserve('juan.perez@udem.edu.co', 1)
        self.client.delete(f"/api/reservations/{r.data['id']}/")
        listado = self.client.get('/api/reservations/?email=juan.perez@udem.edu.co')
        self.assertEqual(len(listado.data), 0)  # la cancelada no aparece


# ── RF07: RESERVA POR ENTRENADOR ────────────────────────────────────────────
class TrainerReservationTests(GymApiTestCase):
    def setUp(self):
        super().setUp()
        self._register(email='coach@udem.edu.co', role='ENTRENADOR')
        self._register(email='estu@udem.edu.co', name='Estudiante')
        self.client.get('/api/slots/')

    def test_entrenador_reserva_para_tercero(self):
        resp = self._reserve('estu@udem.edu.co', 1, actor_email='coach@udem.edu.co')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['created_by'], 'coach@udem.edu.co')

    def test_estudiante_no_puede_reservar_para_otro(self):
        self._register(email='otro@udem.edu.co')
        resp = self._reserve('otro@udem.edu.co', 1, actor_email='estu@udem.edu.co')
        self.assertEqual(resp.status_code, 403)


# ── CU-5: CANCELAR ──────────────────────────────────────────────────────────
class CancelTests(GymApiTestCase):
    def setUp(self):
        super().setUp()
        self._register()
        self.client.get('/api/slots/')
        self.rid = self._reserve('juan.perez@udem.edu.co', 1).data['id']

    def test_cancelar_libera_cupo(self):
        self.assertEqual(self._slot(1)['available'], 19)
        resp = self.client.delete(f'/api/reservations/{self.rid}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._slot(1)['available'], 20)

    def test_doble_cancelacion_no_suma_cupo_de_mas(self):
        self.client.delete(f'/api/reservations/{self.rid}/')
        resp = self.client.delete(f'/api/reservations/{self.rid}/')
        self.assertEqual(resp.status_code, 409)         # ya no está activa
        self.assertEqual(self._slot(1)['available'], 20)

    def test_id_invalido(self):
        self.assertEqual(self.client.delete('/api/reservations/no-es-objectid/').status_code, 400)


# ── RN09: NO-SHOW Y PENALIZACIÓN ────────────────────────────────────────────
class NoShowTests(GymApiTestCase):
    def setUp(self):
        super().setUp()
        self._register(email='coach@udem.edu.co', role='ENTRENADOR')
        self._register(email='estu@udem.edu.co', name='Estudiante')
        self.client.get('/api/slots/')

    def _no_show(self, rid):
        return self.client.post(f'/api/reservations/{rid}/no-show/',
                                {'actor_email': 'coach@udem.edu.co'}, format='json')

    def test_solo_entrenador_marca_no_show(self):
        rid = self._reserve('estu@udem.edu.co', 1).data['id']
        resp = self.client.post(f'/api/reservations/{rid}/no-show/',
                                {'actor_email': 'estu@udem.edu.co'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_tres_no_show_penaliza_y_bloquea_reserva(self):
        for slot in (1, 2, 3):
            rid = self._reserve('estu@udem.edu.co', slot).data['id']
            self._no_show(rid)
        self.assertEqual(self._user('estu@udem.edu.co')['estado'], 'PENALIZADO')
        # Penalizado: no puede crear nuevas reservas.
        resp = self._reserve('estu@udem.edu.co', 4)
        self.assertEqual(resp.status_code, 403)


# ── RF11–RF18: FEATURES COMPLEMENTARIAS ─────────────────────────────────────
class FeaturesTests(GymApiTestCase):
    def setUp(self):
        super().setUp()
        self._register(email='coach@udem.edu.co', role='ENTRENADOR')
        self._register(email='ana@udem.edu.co', name='Ana')
        self.client.get('/api/slots/')

    def test_rf11_historial_incluye_canceladas(self):
        rid = self._reserve('ana@udem.edu.co', 1).data['id']
        self.client.delete(f'/api/reservations/{rid}/')
        resp = self.client.get('/api/reservations/history/?email=ana@udem.edu.co')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['estado'], 'CANCELADA')

    def test_rf17_completar_asistencia(self):
        rid = self._reserve('ana@udem.edu.co', 1).data['id']
        resp = self.client.post(f'/api/reservations/{rid}/complete/',
                                {'actor_email': 'coach@udem.edu.co'}, format='json')
        self.assertEqual(resp.status_code, 200)
        hist = self.client.get('/api/reservations/history/?email=ana@udem.edu.co')
        self.assertEqual(hist.data[0]['estado'], 'COMPLETADA')

    def test_rf12_lista_de_espera(self):
        db_module.get_db().slots.update_one({'slotId': 1}, {'$set': {'available': 0}})
        r1 = self.client.post('/api/slots/1/waitlist/', {'email': 'ana@udem.edu.co'}, format='json')
        self.assertEqual(r1.status_code, 201)
        # Duplicado -> 409
        r2 = self.client.post('/api/slots/1/waitlist/', {'email': 'ana@udem.edu.co'}, format='json')
        self.assertEqual(r2.status_code, 409)

    def test_rf12_no_lista_si_hay_cupos(self):
        resp = self.client.post('/api/slots/1/waitlist/', {'email': 'ana@udem.edu.co'}, format='json')
        self.assertEqual(resp.status_code, 409)

    def test_rf13_perfil_fisico(self):
        resp = self.client.put('/api/users/profile/',
                               {'email': 'ana@udem.edu.co', 'peso': 65, 'altura': 170, 'meta': 'Resistencia'},
                               format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['peso'], 65)
        self.assertEqual(resp.data['meta'], 'Resistencia')

    def test_rf15_calificacion(self):
        self.client.post('/api/ratings/', {'email': 'ana@udem.edu.co', 'stars': 5, 'comment': 'Excelente'}, format='json')
        self.client.post('/api/ratings/', {'email': 'ana@udem.edu.co', 'stars': 3}, format='json')
        resp = self.client.get('/api/ratings/')
        self.assertEqual(resp.data['total'], 2)
        self.assertEqual(resp.data['promedio'], 4.0)

    def test_rf15_stars_invalido(self):
        resp = self.client.post('/api/ratings/', {'email': 'ana@udem.edu.co', 'stars': 9}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_rf16_occupancy(self):
        self._reserve('ana@udem.edu.co', 1)
        resp = self.client.get('/api/reports/occupancy/')
        self.assertEqual(resp.status_code, 200)
        bloque1 = next(b for b in resp.data if b['slotId'] == 1)
        self.assertEqual(bloque1['reservados'], 1)

    def test_rf18_maquinas_seed_y_mantenimiento(self):
        listado = self.client.get('/api/machines/')
        self.assertEqual(len(listado.data), 5)
        # Estudiante NO puede cambiar estado
        deny = self.client.patch('/api/machines/1/', {'actor_email': 'ana@udem.edu.co', 'estado': 'FUERA_DE_SERVICIO'}, format='json')
        self.assertEqual(deny.status_code, 403)
        # Entrenador SÍ
        ok = self.client.patch('/api/machines/1/', {'actor_email': 'coach@udem.edu.co', 'estado': 'FUERA_DE_SERVICIO', 'note': 'Mantenimiento'}, format='json')
        self.assertEqual(ok.status_code, 200)
        m = db_module.get_db().machines.find_one({'machineId': 1})
        self.assertEqual(m['estado'], 'FUERA_DE_SERVICIO')

    def test_csv_export(self):
        resp = self.client.get('/api/reports/usage.csv')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp['Content-Type'])
        self.assertIn('bloque', resp.content.decode())
