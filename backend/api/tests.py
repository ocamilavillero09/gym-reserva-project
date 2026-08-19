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

# RF01/RF02 — El documento de identidad identifica a la persona y es su contraseña.
DOCUMENTOS = {
    ESTUDIANTE: '1001234567',
    PROFESOR:   '7009998881',
    ADMIN:      '3005554442',
}


class GymApiTestCase(TestCase):
    def setUp(self):
        db_module._client = mongomock.MongoClient()
        self.client = APIClient()

    def tearDown(self):
        db_module._client = None

    # Helpers ----------------------------------------------------------------
    def _documento(self, email: str) -> str:
        """Documento de identidad único y estable por correo (RF01)."""
        return DOCUMENTOS.get(email, '10' + str(abs(hash(email)) % 100_000_000).zfill(8))

    def _register(self, email=ESTUDIANTE, name='Juan Perez', documento=None):
        return self.client.post(
            '/api/auth/register/',
            {'name': name, 'email': email, 'documento': documento or self._documento(email)},
            format='json',
        )

    def _login(self, email, documento=None):
        return self.client.post(
            '/api/auth/login/',
            {'email': email, 'documento': documento or self._documento(email)},
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
        # RF01 — se guarda el documento de identidad de la persona...
        self.assertEqual(user['documento'], DOCUMENTOS[ESTUDIANTE])
        # ...y como contraseña solo su hash, nunca el valor en claro.
        self.assertNotEqual(user['password'], DOCUMENTOS[ESTUDIANTE])
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
            {'name': 'Vivo', 'email': ESTUDIANTE, 'documento': DOCUMENTOS[ESTUDIANTE], 'role': 'ADMIN'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._user(ESTUDIANTE)['role'], 'ESTUDIANTE')

    def test_rechaza_correo_no_institucional(self):
        self.assertEqual(self._register(email='juan@gmail.com').status_code, 400)

    def test_rechaza_documento_corto(self):
        self.assertEqual(self._register(documento='123').status_code, 400)

    def test_rechaza_documento_duplicado(self):
        """RF01 — Dos personas no pueden compartir el mismo documento."""
        self._register()
        otra = self._register(email='otra@soyudemedellin.edu.co', name='Otra',
                              documento=DOCUMENTOS[ESTUDIANTE])
        self.assertEqual(otra.status_code, 409)

    def test_rechaza_correo_duplicado(self):
        self._register()
        self.assertEqual(self._register().status_code, 409)


# ── CU-2: LOGIN Y SESIÓN PERSISTENTE ────────────────────────────────────────
class LoginTests(GymApiTestCase):

    def test_login_devuelve_rol_estado_y_contadores(self):
        self._register()
        resp = self._login(ESTUDIANTE)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['role'], 'ESTUDIANTE')
        self.assertEqual(resp.data['documento'], DOCUMENTOS[ESTUDIANTE])
        self.assertEqual(resp.data['estado'], 'ACTIVO')
        self.assertEqual(resp.data['cancel_count'], 0)
        self.assertEqual(resp.data['cancelaciones_restantes'], db_module.CANCELACION_LIMITE)
        self.assertIsNone(resp.data['alerta'])

    def test_login_documento_incorrecto(self):
        """RF02 — El documento es la contraseña: uno distinto no entra."""
        self._register()
        resp = self._login(ESTUDIANTE, documento='9999999999')
        self.assertEqual(resp.status_code, 401)

    def test_login_usuario_inexistente(self):
        resp = self._login('nadie@udem.edu.co', documento='1234567')
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

    def _crear(self, actor, email, name='Nuevo', documento=None, role=None):
        body = {'actor_email': actor, 'name': name, 'email': email,
                'documento': documento or self._documento(email)}
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

    def test_rf16_cinco_no_show_penaliza_y_bloquea_reserva(self):
        for _ in range(db_module.NO_SHOW_LIMITE):
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


# ══════════════════════════════════════════════════════════════════════════
#  REQUISITOS FUNCIONALES RF01–RF25 DEL DOCUMENTO DE ANÁLISIS
# ══════════════════════════════════════════════════════════════════════════

class PerfilTests(GymApiTestCase):
    """RF04 — Perfil del estudiante · RF05 — Perfil de entrenador/admin."""

    def setUp(self):
        super().setUp()
        self._register()
        self._register(email=PROFESOR, name='Coach')

    def test_rf04_el_estudiante_gestiona_edad_peso_altura_y_objetivo(self):
        resp = self.client.put('/api/users/profile/', {
            'email': ESTUDIANTE, 'edad': 21, 'peso': 70, 'altura': 175,
            'meta': 'Ganar resistencia',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['edad'], 21)
        self.assertEqual(resp.data['peso'], 70)
        self.assertEqual(resp.data['altura'], 175)
        self.assertEqual(resp.data['meta'], 'Ganar resistencia')

    def test_rf04_el_estudiante_consulta_su_informacion_personal(self):
        self.client.put('/api/users/profile/', {'email': ESTUDIANTE, 'edad': 22}, format='json')
        resp = self.client.get(f'/api/users/profile/?email={ESTUDIANTE}')
        self.assertEqual(resp.data['edad'], 22)

    def test_rf05_el_profesor_consulta_nombre_documento_y_rol(self):
        resp = self.client.get(f'/api/users/profile/?email={PROFESOR}')
        self.assertEqual(resp.data['name'], 'Coach')
        self.assertEqual(resp.data['documento'], DOCUMENTOS[PROFESOR])
        self.assertEqual(resp.data['role'], 'ENTRENADOR')


class AsistenciaTests(GymApiTestCase):
    """RF11 · RF13 · RF14 · RF15 · RF16 — Asistencia, inasistencia y penalización."""

    def setUp(self):
        super().setUp()
        self._register(email=PROFESOR, name='Coach')
        self._register(email=ADMIN, name='Jefa')
        self._register(email=ESTUDIANTE, name='Juan Perez')
        self.client.get('/api/slots/')
        # La jornada que se procesa es la de la reserva: siempre el día siguiente.
        self.jornada = db_module.fecha_reserva().isoformat()

    # ── RF11 / HU11 — Buscar al estudiante por su documento ────────────────
    def test_rf11_el_entrenador_encuentra_la_reserva_por_documento(self):
        self._reserve(ESTUDIANTE, 1)
        resp = self.client.get(
            f'/api/students/lookup/?documento={DOCUMENTOS[ESTUDIANTE]}&actor_email={PROFESOR}')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['tiene_reserva'])
        self.assertEqual(resp.data['estudiante']['name'], 'Juan Perez')
        self.assertEqual(len(resp.data['reservas']), 1)

    def test_rf11_documento_sin_estudiante(self):
        resp = self.client.get(f'/api/students/lookup/?documento=0000000&actor_email={PROFESOR}')
        self.assertEqual(resp.status_code, 404)

    def test_rf11_el_estudiante_no_puede_buscar_a_otros(self):
        resp = self.client.get(
            f'/api/students/lookup/?documento={DOCUMENTOS[ESTUDIANTE]}&actor_email={ESTUDIANTE}')
        self.assertEqual(resp.status_code, 403)

    # ── RF13 / HU12 — Registrar la asistencia ──────────────────────────────
    def test_rf13_el_entrenador_registra_la_asistencia_por_documento(self):
        self._reserve(ESTUDIANTE, 1)
        resp = self.client.post('/api/attendance/register/', {
            'actor_email': PROFESOR, 'documento': DOCUMENTOS[ESTUDIANTE], 'fecha': self.jornada,
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        reserva = db_module.get_db().reservations.find_one({'email': ESTUDIANTE})
        self.assertEqual(reserva['estado'], 'COMPLETADA')

    def test_rf13_no_se_registra_asistencia_sin_reserva(self):
        resp = self.client.post('/api/attendance/register/', {
            'actor_email': PROFESOR, 'documento': DOCUMENTOS[ESTUDIANTE], 'fecha': self.jornada,
        }, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_rf13_solo_el_entrenador_registra_asistencia(self):
        self._reserve(ESTUDIANTE, 1)
        resp = self.client.post('/api/attendance/register/', {
            'actor_email': ESTUDIANTE, 'documento': DOCUMENTOS[ESTUDIANTE],
        }, format='json')
        self.assertEqual(resp.status_code, 403)

    # ── RF14 / HU13 / HU15 — Estudiantes sin asistencia registrada ─────────
    def test_rf14_lista_los_estudiantes_sin_asistencia(self):
        self._reserve(ESTUDIANTE, 1)
        resp = self.client.get(f'/api/attendance/pending/?actor_email={PROFESOR}&fecha={self.jornada}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['total'], 1)
        self.assertEqual(resp.data['pendientes'][0]['documento'], DOCUMENTOS[ESTUDIANTE])

    def test_rf14_quien_ya_asistio_no_aparece_como_pendiente(self):
        self._reserve(ESTUDIANTE, 1)
        self.client.post('/api/attendance/register/', {
            'actor_email': PROFESOR, 'documento': DOCUMENTOS[ESTUDIANTE], 'fecha': self.jornada,
        }, format='json')
        resp = self.client.get(f'/api/attendance/pending/?actor_email={PROFESOR}&fecha={self.jornada}')
        self.assertEqual(resp.data['total'], 0)

    def test_rf14_el_administrador_tambien_consulta_las_inasistencias(self):
        self._reserve(ESTUDIANTE, 1)
        resp = self.client.get(f'/api/attendance/pending/?actor_email={ADMIN}&fecha={self.jornada}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['total'], 1)

    def test_rf14_el_estudiante_no_consulta_las_inasistencias(self):
        resp = self.client.get(f'/api/attendance/pending/?actor_email={ESTUDIANTE}')
        self.assertEqual(resp.status_code, 403)

    # ── RF15 / HU14 / HU16 — Procesamiento general de inasistencias ────────
    def test_rf15_procesa_de_forma_general_las_inasistencias(self):
        ana = 'ana@soyudemedellin.edu.co'
        self._register(email=ana, name='Ana')
        self._reserve(ESTUDIANTE, 1)
        self._reserve(ana, 2)

        resp = self.client.post('/api/attendance/process/',
                                {'actor_email': PROFESOR, 'fecha': self.jornada}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['total_procesadas'], 2)
        self.assertEqual(self._user(ESTUDIANTE)['no_show_count'], 1)
        self.assertEqual(self._user(ana)['no_show_count'], 1)

    def test_rf15_no_toca_a_quien_si_asistio(self):
        self._reserve(ESTUDIANTE, 1)
        self.client.post('/api/attendance/register/', {
            'actor_email': PROFESOR, 'documento': DOCUMENTOS[ESTUDIANTE], 'fecha': self.jornada,
        }, format='json')
        resp = self.client.post('/api/attendance/process/',
                                {'actor_email': PROFESOR, 'fecha': self.jornada}, format='json')
        self.assertEqual(resp.data['total_procesadas'], 0)
        self.assertEqual(self._user(ESTUDIANTE)['no_show_count'], 0)

    def test_rf15_procesar_dos_veces_no_cuenta_doble(self):
        self._reserve(ESTUDIANTE, 1)
        self.client.post('/api/attendance/process/',
                         {'actor_email': PROFESOR, 'fecha': self.jornada}, format='json')
        segunda = self.client.post('/api/attendance/process/',
                                   {'actor_email': PROFESOR, 'fecha': self.jornada}, format='json')
        self.assertEqual(segunda.data['total_procesadas'], 0)
        self.assertEqual(self._user(ESTUDIANTE)['no_show_count'], 1)

    def test_rf15_el_administrador_tambien_procesa(self):
        self._reserve(ESTUDIANTE, 1)
        resp = self.client.post('/api/attendance/process/',
                                {'actor_email': ADMIN, 'fecha': self.jornada}, format='json')
        self.assertEqual(resp.data['total_procesadas'], 1)

    def test_rf15_el_estudiante_no_puede_procesar(self):
        resp = self.client.post('/api/attendance/process/',
                                {'actor_email': ESTUDIANTE}, format='json')
        self.assertEqual(resp.status_code, 403)

    # ── RF16 — Penalización a las CINCO (5) inasistencias ──────────────────
    def test_rf16_el_limite_de_inasistencias_es_cinco(self):
        self.assertEqual(db_module.NO_SHOW_LIMITE, 5)

    def test_rf16_la_quinta_inasistencia_penaliza(self):
        for i in range(db_module.NO_SHOW_LIMITE):
            self._reserve(ESTUDIANTE, 1)
            resp = self.client.post('/api/attendance/process/',
                                    {'actor_email': PROFESOR, 'fecha': self.jornada}, format='json')
            esperado = i == db_module.NO_SHOW_LIMITE - 1
            self.assertEqual(resp.data['total_penalizados'], 1 if esperado else 0)
        self.assertEqual(self._user(ESTUDIANTE)['estado'], 'PENALIZADO')

    def test_rf16_con_cuatro_inasistencias_todavia_no_hay_penalizacion(self):
        for _ in range(db_module.NO_SHOW_LIMITE - 1):
            self._reserve(ESTUDIANTE, 1)
            self.client.post('/api/attendance/process/',
                             {'actor_email': PROFESOR, 'fecha': self.jornada}, format='json')
        self.assertEqual(self._user(ESTUDIANTE)['estado'], 'ACTIVO')
        self.assertEqual(self._user(ESTUDIANTE)['no_show_count'], 4)


class ReportesTests(GymApiTestCase):
    """RF17 — Historial · RF18 — Reporte personal · RF19/RF20 — Reporte diario."""

    def setUp(self):
        super().setUp()
        self._register(email=PROFESOR, name='Coach')
        self._register(email=ESTUDIANTE, name='Juan Perez')
        self.client.get('/api/slots/')
        self.jornada = db_module.fecha_reserva().isoformat()

    def _procesar(self):
        return self.client.post('/api/attendance/process/',
                                {'actor_email': PROFESOR, 'fecha': self.jornada}, format='json')

    # ── RF17 / HU07 — Historial completo ───────────────────────────────────
    def test_rf17_el_historial_incluye_reservas_cancelaciones_y_asistencias(self):
        rid = self._reserve(ESTUDIANTE, 1).data['id']
        self.client.delete(f'/api/reservations/{rid}/')          # CANCELADA
        self._reserve(ESTUDIANTE, 2)
        self.client.post('/api/attendance/register/', {
            'actor_email': PROFESOR, 'documento': DOCUMENTOS[ESTUDIANTE], 'fecha': self.jornada,
        }, format='json')                                        # COMPLETADA
        self._reserve(ESTUDIANTE, 3)
        self._procesar()                                         # NO_SHOW

        resp = self.client.get(f'/api/reservations/history/?email={ESTUDIANTE}')
        estados = sorted(h['estado'] for h in resp.data)
        self.assertEqual(estados, ['CANCELADA', 'COMPLETADA', 'NO_SHOW'])

    # ── RF18 / HU08 — Reporte personal ─────────────────────────────────────
    def test_rf18_el_estudiante_consulta_sus_inasistencias_y_penalizaciones(self):
        self._reserve(ESTUDIANTE, 1)
        self._procesar()
        resp = self.client.get(f'/api/reports/personal/?email={ESTUDIANTE}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['no_show_count'], 1)
        self.assertEqual(resp.data['no_show_limite'], 5)
        self.assertEqual(resp.data['inasistencias_restantes'], 4)
        self.assertFalse(resp.data['penalizado'])
        self.assertEqual(len(resp.data['inasistencias']), 1)

    def test_rf18_el_reporte_personal_muestra_la_penalizacion(self):
        for _ in range(db_module.NO_SHOW_LIMITE):
            self._reserve(ESTUDIANTE, 1)
            self._procesar()
        resp = self.client.get(f'/api/reports/personal/?email={ESTUDIANTE}')
        self.assertTrue(resp.data['penalizado'])
        self.assertEqual(resp.data['inasistencias_restantes'], 0)
        self.assertIsNotNone(resp.data['penalizado_hasta'])

    # ── RF19 / HU17 / HU18 — Reporte general diario ────────────────────────
    def test_rf19_reporte_general_diario_con_totales(self):
        ana = 'ana@soyudemedellin.edu.co'
        self._register(email=ana, name='Ana')
        rid = self._reserve(ESTUDIANTE, 1).data['id']
        self.client.delete(f'/api/reservations/{rid}/')            # cancelación
        self._reserve(ESTUDIANTE, 2)
        self.client.post('/api/attendance/register/', {
            'actor_email': PROFESOR, 'documento': DOCUMENTOS[ESTUDIANTE], 'fecha': self.jornada,
        }, format='json')                                          # asistencia
        self._reserve(ana, 3)
        self._procesar()                                           # inasistencia

        resp = self.client.get(f'/api/reports/daily/?actor_email={PROFESOR}&fecha={self.jornada}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['totales']['asistencias'], 1)
        self.assertEqual(resp.data['totales']['cancelaciones'], 1)
        self.assertEqual(resp.data['totales']['inasistencias'], 1)

    def test_rf19_el_estudiante_no_ve_el_reporte_general(self):
        resp = self.client.get(f'/api/reports/daily/?actor_email={ESTUDIANTE}')
        self.assertEqual(resp.status_code, 403)

    def test_rf19_el_reporte_lista_a_los_estudiantes_penalizados(self):
        for _ in range(db_module.NO_SHOW_LIMITE):
            self._reserve(ESTUDIANTE, 1)
            self._procesar()
        resp = self.client.get(f'/api/reports/daily/?actor_email={PROFESOR}&fecha={self.jornada}')
        self.assertEqual(resp.data['totales']['estudiantes_penalizados'], 1)
        self.assertEqual(resp.data['penalizados'][0]['documento'], DOCUMENTOS[ESTUDIANTE])

    # ── RF20 / HU19 / HU20 — El reporte diario en PDF ──────────────────────
    def test_rf20_el_reporte_diario_se_genera_en_pdf(self):
        self._reserve(ESTUDIANTE, 1)
        self._procesar()
        resp = self.client.get(f'/api/reports/daily.pdf?actor_email={PROFESOR}&fecha={self.jornada}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))

    def test_rf20_el_estudiante_no_genera_el_pdf_general(self):
        resp = self.client.get(f'/api/reports/daily.pdf?actor_email={ESTUDIANTE}')
        self.assertEqual(resp.status_code, 403)


class AdministradorPrincipalTests(GymApiTestCase):
    """RF21 — Crear administradores · RF22 — Retirar el rol de administrador."""

    OTRO_ADMIN = 'segunda.admin@udemedellin.edu.co'

    def setUp(self):
        super().setUp()
        self._register(email=ADMIN, name='Jefa')       # primer ADMIN = principal

    def _crear_admin(self, actor=ADMIN, email=None):
        email = email or self.OTRO_ADMIN
        return self.client.post('/api/admin/users/', {
            'actor_email': actor, 'name': 'Segunda Admin', 'email': email,
            'documento': self._documento(email),
        }, format='json')

    def test_rf21_el_primer_admin_es_el_principal(self):
        self.assertTrue(self._user(ADMIN)['es_principal'])

    def test_rf21_el_principal_crea_cuentas_de_administrador(self):
        resp = self._crear_admin()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._user(self.OTRO_ADMIN)['role'], 'ADMIN')
        self.assertFalse(self._user(self.OTRO_ADMIN)['es_principal'])

    def test_rf21_un_admin_no_principal_no_crea_administradores(self):
        self._crear_admin()
        resp = self._crear_admin(actor=self.OTRO_ADMIN, email='tercera@udemedellin.edu.co')
        self.assertEqual(resp.status_code, 403)

    def test_rf22_el_principal_retira_el_rol_de_administrador(self):
        self._crear_admin()
        resp = self.client.patch(f'/api/admin/users/{self.OTRO_ADMIN}/',
                                 {'actor_email': ADMIN, 'accion': 'retirar'}, format='json')
        self.assertEqual(resp.status_code, 200)
        retirado = self._user(self.OTRO_ADMIN)
        self.assertEqual(retirado['role'], 'SIN_ROL')
        self.assertEqual(retirado['estado'], 'INACTIVO')

    def test_rf22_la_cuenta_retirada_ya_no_inicia_sesion(self):
        self._crear_admin()
        self.client.patch(f'/api/admin/users/{self.OTRO_ADMIN}/',
                          {'actor_email': ADMIN, 'accion': 'retirar'}, format='json')
        self.assertEqual(self._login(self.OTRO_ADMIN).status_code, 403)

    def test_rf22_el_principal_puede_restaurar_el_rol(self):
        self._crear_admin()
        self.client.patch(f'/api/admin/users/{self.OTRO_ADMIN}/',
                          {'actor_email': ADMIN, 'accion': 'retirar'}, format='json')
        resp = self.client.patch(f'/api/admin/users/{self.OTRO_ADMIN}/',
                                 {'actor_email': ADMIN, 'accion': 'restaurar'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._user(self.OTRO_ADMIN)['role'], 'ADMIN')

    def test_rf22_no_se_puede_retirar_al_administrador_principal(self):
        self._crear_admin()
        resp = self.client.patch(f'/api/admin/users/{ADMIN}/',
                                 {'actor_email': ADMIN, 'accion': 'retirar'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self._user(ADMIN)['role'], 'ADMIN')

    def test_rf22_un_admin_no_principal_no_retira_roles(self):
        self._crear_admin()
        resp = self.client.patch(f'/api/admin/users/{ADMIN}/',
                                 {'actor_email': self.OTRO_ADMIN, 'accion': 'retirar'}, format='json')
        self.assertEqual(resp.status_code, 403)


class NotificacionesTests(GymApiTestCase):
    """RF23 · RF24 · RF25 — Avisos al estudiante al reservar y cancelar."""

    def setUp(self):
        super().setUp()
        self._register(email=ESTUDIANTE, name='Juan Perez')
        self.client.get('/api/slots/')

    def test_rf23_notifica_la_reserva_confirmada(self):
        resp = self._reserve(ESTUDIANTE, 1)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['tipo'], 'RESERVA_CONFIRMADA')
        self.assertIn('confirmada', resp.data['notificacion'].lower())

    def test_rf24_notifica_la_segunda_reserva_del_mismo_dia(self):
        self._reserve(ESTUDIANTE, 1)
        resp = self._reserve(ESTUDIANTE, 2)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['tipo'], 'RESERVA_DUPLICADA')
        self.assertIn('ya tienes una reserva', resp.data['notificacion'].lower())

    def test_rf25_notifica_la_cancelacion(self):
        rid = self._reserve(ESTUDIANTE, 1).data['id']
        resp = self.client.delete(f'/api/reservations/{rid}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['tipo'], 'RESERVA_CANCELADA')
        self.assertIn('cancelaste', resp.data['notificacion'].lower())
