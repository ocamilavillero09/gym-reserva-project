"""
Pruebas unitarias del sistema de reservas.

Cubren los 5 casos de uso críticos definidos en views.py. Se usa `mongomock`
para simular MongoDB en memoria, de modo que el pipeline (Jenkins) pueda
ejecutar las pruebas sin levantar una base de datos real.
"""
import mongomock
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api import db as db_module


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class GymApiTestCase(TestCase):
    """Base: reemplaza el cliente de Mongo por uno en memoria antes de cada test."""

    def setUp(self):
        # Inyecta un cliente mongomock; get_db() lo reutiliza vía db_module._client.
        db_module._client = mongomock.MongoClient()
        self.client = APIClient()

    def tearDown(self):
        db_module._client = None

    # Helpers ----------------------------------------------------------------
    def _register(self, email='juan.perez@udem.edu.co', name='Juan Perez', password='secreto123'):
        return self.client.post('/api/auth/register/',
                                {'name': name, 'email': email, 'password': password}, format='json')

    def _slot(self, slot_id):
        return db_module.get_db().slots.find_one({'slotId': slot_id})


# ── CU-1: REGISTRO ────────────────────────────────────────────────────────
class RegisterTests(GymApiTestCase):

    def test_registro_exitoso_guarda_password_hasheada(self):
        resp = self._register()
        self.assertEqual(resp.status_code, 201)
        user = db_module.get_db().users.find_one({'email': 'juan.perez@udem.edu.co'})
        self.assertIsNotNone(user)
        # La contraseña nunca se guarda en claro.
        self.assertNotEqual(user['password'], 'secreto123')
        self.assertIn(':', user['password'])  # formato salt:hash

    def test_rechaza_correo_no_institucional(self):
        resp = self._register(email='juan@gmail.com')
        self.assertEqual(resp.status_code, 400)

    def test_rechaza_password_corta(self):
        resp = self._register(password='123')
        self.assertEqual(resp.status_code, 400)

    def test_rechaza_correo_duplicado(self):
        self._register()
        resp = self._register()
        self.assertEqual(resp.status_code, 409)


# ── CU-2: LOGIN ─────────────────────────────────────────────────────────────
class LoginTests(GymApiTestCase):

    def test_login_correcto(self):
        self._register()
        resp = self.client.post('/api/auth/login/',
                                {'email': 'juan.perez@udem.edu.co', 'password': 'secreto123'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['email'], 'juan.perez@udem.edu.co')

    def test_login_password_incorrecta(self):
        self._register()
        resp = self.client.post('/api/auth/login/',
                                {'email': 'juan.perez@udem.edu.co', 'password': 'malaclave'}, format='json')
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


# ── CU-4: CREAR RESERVA (descuento atómico) ─────────────────────────────────
class ReservationTests(GymApiTestCase):

    def setUp(self):
        super().setUp()
        self._register()
        self.client.get('/api/slots/')  # siembra los slots

    def test_reserva_descuenta_cupo(self):
        resp = self.client.post('/api/reservations/',
                                {'email': 'juan.perez@udem.edu.co', 'slotId': 1}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._slot(1)['available'], 19)

    def test_no_permite_doble_reserva_mismo_bloque(self):
        self.client.post('/api/reservations/', {'email': 'juan.perez@udem.edu.co', 'slotId': 1}, format='json')
        resp = self.client.post('/api/reservations/', {'email': 'juan.perez@udem.edu.co', 'slotId': 1}, format='json')
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self._slot(1)['available'], 19)  # no descuenta de nuevo

    def test_rechaza_sin_cupos(self):
        db_module.get_db().slots.update_one({'slotId': 1}, {'$set': {'available': 0}})
        resp = self.client.post('/api/reservations/', {'email': 'juan.perez@udem.edu.co', 'slotId': 1}, format='json')
        self.assertEqual(resp.status_code, 409)

    def test_rechaza_slot_inexistente(self):
        resp = self.client.post('/api/reservations/', {'email': 'juan.perez@udem.edu.co', 'slotId': 999}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_descuento_atomico_no_sobrevende_ultimo_cupo(self):
        """Con 1 cupo, dos estudiantes distintos compiten: solo uno gana."""
        db_module.get_db().slots.update_one({'slotId': 1}, {'$set': {'available': 1}})
        r1 = self.client.post('/api/reservations/', {'email': 'juan.perez@udem.edu.co', 'slotId': 1}, format='json')
        r2 = self.client.post('/api/reservations/', {'email': 'ana.gomez@udem.edu.co', 'slotId': 1}, format='json')
        codes = sorted([r1.status_code, r2.status_code])
        self.assertEqual(codes, [201, 409])           # uno crea, el otro es rechazado
        self.assertEqual(self._slot(1)['available'], 0)  # nunca queda negativo


# ── CU-5: CANCELAR RESERVA ──────────────────────────────────────────────────
class CancelTests(GymApiTestCase):

    def setUp(self):
        super().setUp()
        self._register()
        self.client.get('/api/slots/')
        resp = self.client.post('/api/reservations/',
                                {'email': 'juan.perez@udem.edu.co', 'slotId': 1}, format='json')
        self.reservation_id = resp.data['id']

    def test_cancelar_libera_cupo(self):
        self.assertEqual(self._slot(1)['available'], 19)
        resp = self.client.delete(f'/api/reservations/{self.reservation_id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._slot(1)['available'], 20)  # cupo devuelto

    def test_doble_cancelacion_no_suma_cupo_de_mas(self):
        self.client.delete(f'/api/reservations/{self.reservation_id}/')
        resp = self.client.delete(f'/api/reservations/{self.reservation_id}/')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self._slot(1)['available'], 20)  # no pasa de 20 (total)

    def test_id_invalido(self):
        resp = self.client.delete('/api/reservations/no-es-un-objectid/')
        self.assertEqual(resp.status_code, 400)
