"""
FUNCIONALIDADES DE ACCESO Y DE RESERVAS

Este archivo expone la API: recibe la petición, aplica las reglas del gimnasio
y devuelve la respuesta. No consulta MongoDB directamente ni define límites
propios; para eso llama a las otras dos capas del backend:

    reglas.py   -> los límites y cálculos del gimnasio
    datos.py    -> las consultas a la base de datos
    seguridad.py-> el tratamiento de las contraseñas

REQUISITOS FUNCIONALES CUBIERTOS EN ESTE ARCHIVO
    RF02  Inicio de sesión con el correo institucional y el documento
    RF08  Reserva del estudiante para el día siguiente
    RF12  El personal visualiza los bloques sin poder reservar
    RF23  Notificación de reserva confirmada

REQUISITOS FUNCIONALES IGNORADOS EN ESTE ARCHIVO
    Son responsabilidad de otros integrantes del equipo o quedaron fuera del
    alcance de las pruebas. El código sigue funcionando, pero no se diseñaron
    escenarios ni casos de prueba para ellos.
    RF01  Registro de usuarios
    RF03  Asignación automática del rol según el dominio
    RF06  Consulta de los bloques horarios disponibles
    RF07  Cupos ocupados y disponibles de cada bloque
    RF09  Una única reserva por estudiante y día
    RF10  Consulta de las reservas hechas
    RF16  Penalización al alcanzar cinco inasistencias
    RF21  Creación de cuentas de administrador
    RF22  Gestión de las cuentas de otros administradores
    RF24  Cancelación de reservas
    RF25  Notificación de cancelación
"""
from datetime import datetime

from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from . import datos, reglas
from .seguridad import hash_password, verify_password


# ══════════════════════════════════════════════════════════════════════════
#  CASOS DE USO CRÍTICOS DEL SISTEMA
#  --------------------------------------------------------------------------
#  Son los flujos que, si fallan, comprometen la integridad de los datos o la
#  seguridad del sistema:
#
#    CU-1  Registro con correo institucional       (control de acceso)
#    CU-2  Inicio de sesión y verificación del hash (credenciales)
#    CU-3  Consulta de cupos en tiempo real         (consistencia de lectura)
#    CU-4  Crear reserva con descuento ATÓMICO      (concurrencia)
#    CU-5  Cancelar reserva y liberar cupo          (no perder cupos)
# ══════════════════════════════════════════════════════════════════════════


def _perfil_sesion(user: dict) -> dict:
    """Datos de sesión que el frontend necesita para pintar la interfaz.

    Incluye siempre nombre, documento de identidad y rol asignado, que es lo
    que consultan entrenadores y administradores en su perfil.
    """
    return {
        'name':      user['name'],
        'email':     user['email'],
        'documento': user.get('documento', ''),
        'role':      user.get('role', 'ESTUDIANTE'),
        'estado':    user.get('estado', 'ACTIVO'),
        'es_principal': bool(user.get('es_principal')),
        # Cancelaciones: solo informativo, no sanciona.
        'cancel_count':  user.get('cancel_count', 0),
        # Inasistencias: son las que penalizan la cuenta.
        'no_show_count': user.get('no_show_count', 0),
        'inasistencias_restantes': reglas.inasistencias_restantes(user),
        'no_show_limite': reglas.NO_SHOW_LIMITE,
        'alerta_inasistencias': reglas.alerta_inasistencias(user),
    }


def _leer_documento(data) -> str:
    """Toma el documento de identidad del cuerpo de la petición.

    El campo se llama `documento`; se acepta `password` como alias porque el
    documento ES la contraseña con la que la persona inicia sesión.
    """
    return reglas.normalizar_documento(data.get('documento') or data.get('password') or '')


# ══════════════════════════════════════════════════════════════════════════
#  AUTENTICACIÓN
# ══════════════════════════════════════════════════════════════════════════

# ── RF01 · [IGNORADO] Registro de usuarios ────────────────────────────────
# ── RF03 · [IGNORADO] Asignación automática del rol según el dominio ──────
@swagger_auto_schema(
    method='post',
    operation_description="Registro de usuarios. El rol se deduce del dominio del correo institucional.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['name', 'email', 'documento'],
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, example='Juan Pérez'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='juan.perez@soyudemedellin.edu.co'),
            'documento': openapi.Schema(type=openapi.TYPE_STRING, example='1001234567', description='Documento de identidad: es también la contraseña.'),
        }
    ),
    responses={
        201: openapi.Response('Registro exitoso.'),
        400: openapi.Response('Datos inválidos.'),
        409: openapi.Response('Correo ya existe.'),
    }
)
@api_view(['POST'])
def register(request):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #1 — REGISTRO CON CORREO INSTITUCIONAL       ║
    # ║ Es el control de acceso: solo miembros de la universidad crean    ║
    # ║ cuenta, la contraseña se almacena derivada (nunca en claro) y el  ║
    # ║ correo es único. El ROL SE DEDUCE DEL DOMINIO, así nadie se       ║
    # ║ auto-asigna privilegios de profesor o administrador.              ║
    # ╚══════════════════════════════════════════════════════════════════╝
    name      = request.data.get('name', '').strip()
    email     = reglas.normalizar_correo(request.data.get('email'))
    documento = _leer_documento(request.data)

    if not name or not email or not documento:
        return Response(
            {'error': 'Nombre, correo institucional y documento de identidad son obligatorios.'},
            status=400,
        )

    if len(documento) < reglas.DOCUMENTO_MIN:
        return Response(
            {'error': f'El documento de identidad debe tener al menos {reglas.DOCUMENTO_MIN} caracteres.'},
            status=400,
        )

    role = reglas.role_for_email(email)
    if role is None:
        return Response(
            {'error': f'Debes usar un correo institucional válido: {reglas.dominios_texto()}.'},
            status=400,
        )

    if datos.buscar_usuario(email):
        return Response({'error': 'Ya existe una cuenta con este correo.'}, status=409)

    if datos.buscar_usuario_por_documento(documento):
        return Response({'error': 'Ya existe una cuenta con este documento de identidad.'}, status=409)

    # El PRIMER administrador del sistema es el administrador principal: es
    # quien puede crear y gestionar las cuentas de los demás administradores.
    es_principal = role == 'ADMIN' and datos.contar_administradores() == 0

    datos.crear_usuario({
        'name':       name,
        'email':      email,
        'documento':  documento,                # se busca al estudiante por él
        'password':   hash_password(documento),  # el documento es la contraseña
        'role':       role,
        'estado':     'ACTIVO',                 # ACTIVO | PENALIZADO | INACTIVO
        'es_principal': es_principal,
        'no_show_count': 0,
        'cancel_count':  0,
        'penalizado_hasta': None,
        'created_at': datetime.utcnow(),
    })

    return Response({
        'message': 'Registro exitoso.',
        'role': role,
        'documento': documento,
        'es_principal': es_principal,
    }, status=201)


# ── RF02 · Inicio de sesión con el correo institucional y el documento ────
@swagger_auto_schema(
    method='post',
    operation_description="Inicio de sesión y validación de credenciales.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'documento'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='juan.perez@soyudemedellin.edu.co'),
            'documento': openapi.Schema(type=openapi.TYPE_STRING, example='1001234567', description='Documento de identidad usado como contraseña.'),
        }
    ),
    responses={
        200: openapi.Response('Login exitoso.'),
        401: openapi.Response('Credenciales incorrectas.'),
    }
)
@api_view(['POST'])
def login(request):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #2 — INICIO DE SESIÓN                        ║
    # ║ La verificación compara el hash almacenado sin exponer la clave, ║
    # ║ y devuelve un mensaje genérico ante correo o documento incorrectos║
    # ║ para no revelar si el correo existe (evita enumerar cuentas).     ║
    # ╚══════════════════════════════════════════════════════════════════╝
    email     = reglas.normalizar_correo(request.data.get('email'))
    documento = _leer_documento(request.data)

    user = datos.buscar_usuario(email)
    if not user or not verify_password(user['password'], documento):
        return Response({'error': 'Correo o documento de identidad incorrectos.'}, status=401)

    # A esta cuenta le retiraron el rol: ya no puede entrar al sistema.
    if user.get('estado') == 'INACTIVO' or user.get('role') == 'SIN_ROL':
        return Response({'error': 'Tu cuenta fue desactivada por el administrador principal.'}, status=403)

    return Response(_perfil_sesion(user))


# ── RF02 · Recuperación de la sesión al recargar la página ────────────────
@swagger_auto_schema(
    method='get',
    operation_description="Devuelve la sesión actualizada de un usuario (se usa al recargar la página).",
    manual_parameters=[
        openapi.Parameter('email', openapi.IN_QUERY, description="Correo del usuario", type=openapi.TYPE_STRING, required=True),
    ],
    responses={200: openapi.Response('Sesión vigente.'), 404: openapi.Response('Usuario no encontrado.')}
)
@api_view(['GET'])
def session(request):
    """Rehidrata la sesión tras recargar la página.

    El frontend guarda la sesión en el navegador; al recargar consulta este
    recurso para traer datos frescos (rol, estado, contadores) en vez de
    confiar ciegamente en lo guardado localmente.
    """
    email = reglas.normalizar_correo(request.query_params.get('email'))
    if not email:
        return Response({'error': 'Parámetro email requerido.'}, status=400)
    user = datos.buscar_usuario(email)
    if not user:
        return Response({'error': 'Usuario no encontrado.'}, status=404)
    return Response(_perfil_sesion(user))


# ══════════════════════════════════════════════════════════════════════════
#  ADMINISTRACIÓN DE USUARIOS
# ══════════════════════════════════════════════════════════════════════════

# ── RF21 · [IGNORADO] Creación de cuentas de administrador ───────────────
@swagger_auto_schema(
    method='get',
    operation_description="Lista los usuarios del sistema (solo ADMIN).",
    manual_parameters=[
        openapi.Parameter('actor_email', openapi.IN_QUERY, description="Correo del administrador", type=openapi.TYPE_STRING, required=True),
    ],
    responses={200: openapi.Response('Listado de usuarios.'), 403: openapi.Response('Solo administradores.')}
)
@swagger_auto_schema(
    method='post',
    operation_description="Un ADMIN crea nuevos usuarios, incluidos otros administradores.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['actor_email', 'name', 'email', 'documento'],
        properties={
            'actor_email': openapi.Schema(type=openapi.TYPE_STRING, example='soporte@udemedellin.edu.co'),
            'name': openapi.Schema(type=openapi.TYPE_STRING, example='Nueva Administradora'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='nueva.admin@udemedellin.edu.co'),
            'documento': openapi.Schema(type=openapi.TYPE_STRING, example='1009998887'),
            'role': openapi.Schema(type=openapi.TYPE_STRING, example='ADMIN', description='Debe coincidir con el dominio del correo.'),
        }
    ),
    responses={
        201: openapi.Response('Usuario creado.'),
        400: openapi.Response('Datos inválidos.'),
        403: openapi.Response('Solo administradores.'),
        409: openapi.Response('El correo ya existe.'),
    }
)
@api_view(['GET', 'POST'])
def admin_users(request):
    """Solo un ADMIN autenticado da de alta cuentas, y es la única vía para
    crear NUEVOS ADMINISTRADORES. El rol sigue amarrado al dominio del correo:
    un admin no puede crear un administrador con un correo de estudiante.
    """
    actor_email = (request.query_params.get('actor_email') if request.method == 'GET'
                   else request.data.get('actor_email', ''))
    actor = datos.buscar_usuario(reglas.normalizar_correo(actor_email))
    if not actor or actor.get('role') != 'ADMIN':
        return Response({'error': 'Solo un administrador puede gestionar usuarios.'}, status=403)

    if request.method == 'GET':
        return Response([{
            'name': u.get('name'), 'email': u['email'], 'role': u.get('role'),
            'documento': u.get('documento', ''),
            'estado': u.get('estado'), 'cancel_count': u.get('cancel_count', 0),
            'no_show_count': u.get('no_show_count', 0),
            'es_principal': bool(u.get('es_principal')),
        } for u in datos.listar_usuarios()])

    name      = request.data.get('name', '').strip()
    email     = reglas.normalizar_correo(request.data.get('email'))
    documento = _leer_documento(request.data)
    if not name or not email or not documento:
        return Response({'error': 'Nombre, correo y documento de identidad son obligatorios.'}, status=400)
    if len(documento) < reglas.DOCUMENTO_MIN:
        return Response(
            {'error': f'El documento de identidad debe tener al menos {reglas.DOCUMENTO_MIN} caracteres.'},
            status=400,
        )

    role = reglas.role_for_email(email)
    if role is None:
        return Response(
            {'error': f'Debes usar un correo institucional válido: {reglas.dominios_texto()}.'},
            status=400,
        )

    # Si el admin indica un rol explícito, debe coincidir con el dominio.
    pedido = request.data.get('role')
    if pedido:
        pedido = pedido.strip().upper()
        if pedido not in reglas.ROLES:
            return Response({'error': f'Rol inválido. Use uno de: {", ".join(reglas.ROLES)}.'}, status=400)
        if pedido != role:
            return Response(
                {'error': f'El correo {email} corresponde al rol {role}, no a {pedido}. '
                          f'Para crear un {pedido} usa un correo del dominio correspondiente.'},
                status=400,
            )

    # Solo el ADMINISTRADOR PRINCIPAL crea cuentas con rol de administrador.
    if role == 'ADMIN' and not _es_principal(actor):
        return Response(
            {'error': 'Solo el administrador principal puede crear cuentas de administrador.'},
            status=403,
        )

    if datos.buscar_usuario(email):
        return Response({'error': 'Ya existe una cuenta con este correo.'}, status=409)
    if datos.buscar_usuario_por_documento(documento):
        return Response({'error': 'Ya existe una cuenta con este documento de identidad.'}, status=409)

    datos.crear_usuario({
        'name':       name,
        'email':      email,
        'documento':  documento,
        'password':   hash_password(documento),
        'role':       role,
        'estado':     'ACTIVO',
        'es_principal': False,
        'no_show_count': 0,
        'cancel_count':  0,
        'penalizado_hasta': None,
        'created_at': datetime.utcnow(),
        'created_by': actor['email'],
    })
    return Response({'message': f'Usuario creado con rol {role}.', 'role': role}, status=201)


def _es_principal(actor: dict) -> bool:
    """¿El actor es el administrador principal del sistema?

    Es principal quien tiene la marca `es_principal`. Para no dejar el sistema
    sin administrador principal (por ejemplo en instalaciones creadas antes de
    que existiera la marca), si NINGÚN administrador la tiene se considera
    principal al administrador más antiguo.
    """
    if not actor or actor.get('role') != 'ADMIN':
        return False
    if actor.get('es_principal'):
        return True
    if datos.hay_administrador_principal():
        return False
    primero = datos.administrador_mas_antiguo()
    return bool(primero and primero['email'] == actor['email'])


# ── RF22 · [IGNORADO] Gestión de las cuentas de otros administradores ────
@swagger_auto_schema(
    method='patch',
    operation_description=(
        "El administrador principal gestiona las cuentas de otros administradores. "
        "Con accion='retirar' le quita el rol; con accion='restaurar' se lo devuelve."
    ),
    manual_parameters=[
        openapi.Parameter('user_email', openapi.IN_PATH, description="Correo de la cuenta a gestionar", type=openapi.TYPE_STRING, required=True),
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['actor_email', 'accion'],
        properties={
            'actor_email': openapi.Schema(type=openapi.TYPE_STRING, example='soporte@udemedellin.edu.co'),
            'accion': openapi.Schema(type=openapi.TYPE_STRING, enum=['retirar', 'restaurar'], example='retirar'),
        },
    ),
    responses={
        200: openapi.Response('Cuenta actualizada.'),
        400: openapi.Response('Acción inválida.'),
        403: openapi.Response('Solo el administrador principal.'),
        404: openapi.Response('Cuenta no encontrada.'),
    },
)
@api_view(['PATCH'])
def admin_user_detail(request, user_email):
    """Solo el ADMINISTRADOR PRINCIPAL puede retirar (o devolver) el rol de
    administrador. Retirarlo deja la cuenta con rol SIN_ROL y estado INACTIVO,
    de modo que ya no puede iniciar sesión. El propio principal NO puede ser
    retirado: el sistema nunca queda sin administrador.
    """
    actor = datos.buscar_usuario(reglas.normalizar_correo(request.data.get('actor_email')))
    if not _es_principal(actor):
        return Response(
            {'error': 'Solo el administrador principal puede gestionar las cuentas de administrador.'},
            status=403,
        )

    objetivo = datos.buscar_usuario(reglas.normalizar_correo(user_email))
    if not objetivo:
        return Response({'error': 'Cuenta no encontrada.'}, status=404)

    accion = (request.data.get('accion') or '').strip().lower()

    if accion == 'retirar':
        if objetivo['email'] == actor['email'] or objetivo.get('es_principal'):
            return Response(
                {'error': 'No puedes retirar el rol del administrador principal.'},
                status=400,
            )
        if objetivo.get('role') != 'ADMIN':
            return Response({'error': 'La cuenta no tiene rol de administrador.'}, status=400)
        datos.actualizar_usuario(objetivo['email'], {
            'role': 'SIN_ROL', 'estado': 'INACTIVO',
            'admin_retirado_por': actor['email'],
            'admin_retirado_at': datetime.utcnow(),
        })
        return Response({
            'message': f"Se retiró el rol de administrador a {objetivo['email']}.",
            'role': 'SIN_ROL', 'estado': 'INACTIVO',
        })

    if accion == 'restaurar':
        if reglas.role_for_email(objetivo['email']) != 'ADMIN':
            return Response(
                {'error': 'El correo de la cuenta no corresponde al dominio de administrador.'},
                status=400,
            )
        datos.actualizar_usuario(
            objetivo['email'],
            {'role': 'ADMIN', 'estado': 'ACTIVO'},
            quitar={'admin_retirado_por': '', 'admin_retirado_at': ''},
        )
        return Response({
            'message': f"Se restauró el rol de administrador a {objetivo['email']}.",
            'role': 'ADMIN', 'estado': 'ACTIVO',
        })

    return Response({'error': "Acción inválida. Use 'retirar' o 'restaurar'."}, status=400)


# ══════════════════════════════════════════════════════════════════════════
#  BLOQUES HORARIOS
# ══════════════════════════════════════════════════════════════════════════

# ── RF06 · [IGNORADO] Consulta de los bloques horarios disponibles ───────
# ── RF07 · [IGNORADO] Cupos ocupados y disponibles de cada bloque ────────
# ── RF12 · El personal visualiza los bloques y su disponibilidad ─────────
@swagger_auto_schema(
    method='get',
    operation_description="Bloques horarios y cupos disponibles para la fecha de reserva (el día siguiente).",
    responses={200: openapi.Response('Disponibilidad del día siguiente.')}
)
@api_view(['GET'])
def get_slots(request):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #3 — CONSULTA DE CUPOS EN TIEMPO REAL        ║
    # ║ El frontend decide qué bloques se pueden reservar a partir de     ║
    # ║ este valor, así que debe reflejar el estado real de los bloques.  ║
    # ║ La respuesta incluye la FECHA DE LA RESERVA (el día siguiente)    ║
    # ║ para que la interfaz la muestre de forma explícita.               ║
    # ╚══════════════════════════════════════════════════════════════════╝
    datos.sembrar_bloques()
    bloques = [
        {'id': s['slotId'], 'hour': s['hour'], 'available': s['available'], 'total': s['total']}
        for s in datos.listar_bloques(sin_id=True)
    ]
    fecha = reglas.fecha_reserva()
    return Response({
        'fecha': fecha.isoformat(),
        'fecha_label': reglas.formato_fecha_es(fecha),
        'slots': bloques,
    })


# ══════════════════════════════════════════════════════════════════════════
#  RESERVAS
# ══════════════════════════════════════════════════════════════════════════

# ── RF08 · Reserva del estudiante para el día siguiente ──────────────────
# ── RF23 · Notificación de reserva confirmada ────────────────────────────
# ── RF09 · [IGNORADO] Una única reserva por estudiante y día ─────────────
# ── RF10 · [IGNORADO] Consulta de las reservas hechas ────────────────────
@swagger_auto_schema(
    method='get',
    operation_description="Lista las reservas activas de un estudiante.",
    manual_parameters=[
        openapi.Parameter('email', openapi.IN_QUERY, description="Correo del usuario", type=openapi.TYPE_STRING, required=True),
    ],
    responses={200: openapi.Response('Lista de reservas.'), 400: openapi.Response('Parámetro email requerido.')}
)
@swagger_auto_schema(
    method='post',
    operation_description="Crea la reserva del día siguiente y descuenta cupo. Una sola reserva por día.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'slotId'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, example='juan.perez@soyudemedellin.edu.co'),
            'slotId': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
        }
    ),
    responses={
        201: openapi.Response('Reserva creada.'),
        400: openapi.Response('Datos inválidos.'),
        403: openapi.Response('Perfil sin permiso de reserva.'),
        404: openapi.Response('Horario no encontrado.'),
        409: openapi.Response('Sin cupos o ya reservó hoy.'),
    }
)
@api_view(['GET', 'POST'])
def reservations(request):
    if request.method == 'GET':
        email = reglas.normalizar_correo(request.query_params.get('email'))
        if not email:
            return Response({'error': 'Parámetro email requerido.'}, status=400)
        # Solo las ACTIVA: las canceladas o marcadas No-Show no se listan.
        return Response([datos.serialize(r) for r in datos.reservas_activas(email)])

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #4 — CREAR RESERVA (DESCUENTO ATÓMICO)       ║
    # ║ El más crítico del sistema. Con varios estudiantes reservando el  ║
    # ║ último cupo a la vez, un patrón "leer-luego-escribir" permitiría  ║
    # ║ SOBREVENTA. Por eso el cupo se descuenta con una única operación  ║
    # ║ atómica condicional (datos.tomar_cupo) y la reserva solo se       ║
    # ║ inserta DESPUÉS de haber ganado el cupo.                          ║
    # ║ Reglas aplicadas aquí:                                            ║
    # ║   Solo los ESTUDIANTES reservan; el personal solo consulta.       ║
    # ║   La reserva es SIEMPRE para el día siguiente.                    ║
    # ║   Una única reserva por día.                                      ║
    # ║   Bloqueo si la cuenta está penalizada.                           ║
    # ╚══════════════════════════════════════════════════════════════════╝
    email   = reglas.normalizar_correo(request.data.get('email'))
    slot_id = request.data.get('slotId')

    if not email or slot_id is None:
        return Response({'error': 'email y slotId son obligatorios.'}, status=400)

    owner = datos.buscar_usuario(email)
    if not owner:
        return Response({'error': 'El usuario de la reserva no existe.'}, status=404)

    # El gimnasio reserva cupos para estudiantes. Profesores y administradores
    # usan el sistema únicamente para consultar el aforo.
    if owner.get('role') != 'ESTUDIANTE':
        return Response(
            {'error': 'Los profesores y administradores no reservan cupos: solo consultan el aforo.'},
            status=403,
        )

    # Un usuario PENALIZADO no puede crear reservas (sí consultar).
    if owner.get('estado') == 'PENALIZADO':
        if reglas.penalizacion_vigente(owner):
            return Response({'error': 'Tu cuenta está penalizada. No puedes reservar por ahora.'}, status=403)
        # Penalización vencida: se reactiva la cuenta y se reinician contadores.
        datos.actualizar_usuario(email, {
            'estado': 'ACTIVO', 'no_show_count': 0, 'penalizado_hasta': None,
        })

    slot = datos.buscar_bloque(slot_id)
    if not slot:
        return Response({'error': 'Horario no encontrado.'}, status=404)

    fecha = reglas.fecha_reserva()
    fecha_iso = fecha.isoformat()
    fecha_label = reglas.formato_fecha_es(fecha)

    # UNA SOLA RESERVA POR DÍA. Se cuenta sobre la fecha de la reserva (el día
    # siguiente), no sobre el total histórico de reservas activas.
    del_dia = datos.contar_reservas(
        {'email': email, 'estado': 'ACTIVA', 'reserva_date': fecha_iso})
    if del_dia >= reglas.MAX_RESERVAS_POR_DIA:
        aviso = (f'Ya tienes una reserva para el {fecha_label}. '
                 'Solo se permite una reserva por día: cancela la actual si quieres cambiar de horario.')
        return Response({'error': aviso, 'notificacion': aviso, 'tipo': 'RESERVA_DUPLICADA'}, status=409)

    # Descuento ATÓMICO: solo descuenta si todavía queda cupo.
    if datos.tomar_cupo(slot_id) is None:
        # Otro estudiante tomó el último cupo entre la lectura y este punto.
        return Response({'error': 'No hay cupos disponibles en este horario.'}, status=409)

    nueva = datos.crear_reserva({
        'email':        email,
        'slotId':       slot_id,
        'hour':         slot['hour'],
        'reserva_date': fecha_iso,    # fecha efectiva: el día siguiente
        'date':         fecha_label,  # etiqueta legible para la interfaz
        'estado':       'ACTIVA',     # ACTIVA | CANCELADA | NO_SHOW | COMPLETADA
        'created_by':   email,
        'created_at':   datetime.utcnow(),
    })

    respuesta = datos.serialize(nueva)
    # Notificación de confirmación que muestra la aplicación.
    respuesta['notificacion'] = f"Reserva confirmada para las {slot['hour']} del {fecha_label}."
    respuesta['tipo'] = 'RESERVA_CONFIRMADA'
    return Response(respuesta, status=201)


# ── RF24 · [IGNORADO] Cancelación de reservas ────────────────────────────
# ── RF25 · [IGNORADO] Notificación de cancelación ────────────────────────
@swagger_auto_schema(
    method='delete',
    operation_description="Cancela reserva y libera cupo inmediatamente. Suma al contador de cancelaciones.",
    manual_parameters=[
        openapi.Parameter('reservation_id', openapi.IN_PATH, description="ID de la reserva", type=openapi.TYPE_STRING, required=True),
    ],
    responses={
        200: openapi.Response('Reserva cancelada.'),
        400: openapi.Response('ID inválido.'),
        404: openapi.Response('Reserva no encontrada.'),
    }
)
@api_view(['DELETE'])
def cancel_reservation(request, reservation_id):
    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ CASO DE USO CRÍTICO #5 — CANCELAR RESERVA Y LIBERAR CUPO         ║
    # ║ El cupo solo se devuelve si la reserva estaba ACTIVA y esta        ║
    # ║ operación la pasó a CANCELADA. La transición atómica actúa como   ║
    # ║ guardia: una doble cancelación no vuelve a sumar el cupo.          ║
    # ╚══════════════════════════════════════════════════════════════════╝
    oid = datos.a_object_id(reservation_id)
    if oid is None:
        return Response({'error': 'ID de reserva inválido.'}, status=400)

    reservation = datos.cambiar_estado_reserva(
        oid, 'ACTIVA', {'estado': 'CANCELADA', 'cancelled_at': datetime.utcnow()})
    if reservation is None:
        # O no existe, o ya no estaba activa (cancelada / no-show).
        if datos.buscar_reserva(oid):
            return Response({'error': 'La reserva ya no está activa.'}, status=409)
        return Response({'error': 'Reserva no encontrada.'}, status=404)

    datos.devolver_cupo(reservation['slotId'])

    # Contador de cancelaciones del estudiante. Es SOLO INFORMATIVO: cancelar
    # no suma inasistencias ni penaliza la cuenta, porque avisar a tiempo
    # devuelve el cupo para que otra persona lo aproveche.
    owner = datos.sumar_a_contador(reservation['email'], 'cancel_count')

    return Response({
        'message': 'Reserva cancelada. Cupo liberado.',
        'notificacion': f"Cancelaste tu reserva de las {reservation['hour']} "
                        f"del {reservation.get('date', '')}. El cupo quedó liberado.",
        'tipo': 'RESERVA_CANCELADA',
        'cancel_count': (owner or {}).get('cancel_count', 0),
        # Las inasistencias no cambian al cancelar: son cosas distintas.
        'no_show_count': (owner or {}).get('no_show_count', 0),
    })


# ── RF16 · [IGNORADO] Penalización al alcanzar cinco inasistencias ───────
@swagger_auto_schema(
    method='post',
    operation_description="El entrenador o administrador marca una inasistencia y, al llegar al límite, penaliza la cuenta.",
    manual_parameters=[
        openapi.Parameter('reservation_id', openapi.IN_PATH, description="ID de la reserva", type=openapi.TYPE_STRING, required=True),
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['actor_email'],
        properties={'actor_email': openapi.Schema(type=openapi.TYPE_STRING, example='profesor@udem.edu.co')},
    ),
    responses={
        200: openapi.Response('Inasistencia registrada.'),
        403: openapi.Response('Sin permisos.'),
        404: openapi.Response('Reserva no encontrada.'),
    }
)
@api_view(['POST'])
def mark_no_show(request, reservation_id):
    """Solo ENTRENADOR o ADMIN. Marca la reserva como NO_SHOW, incrementa el
    contador de la persona y, al alcanzar el límite, penaliza su cuenta.
    """
    actor = datos.buscar_usuario(reglas.normalizar_correo(request.data.get('actor_email')))
    if not reglas.es_staff(actor):
        return Response({'error': 'Solo un profesor o administrador puede registrar inasistencias.'}, status=403)

    oid = datos.a_object_id(reservation_id)
    if oid is None:
        return Response({'error': 'ID de reserva inválido.'}, status=400)

    # ACTIVA -> NO_SHOW de forma atómica (no se devuelve el cupo: se desperdició).
    # Solo si la jornada de la reserva ya llegó: mientras sea para mañana, el
    # estudiante todavía no ha tenido ocasión de presentarse.
    hoy = reglas.hoy_local().isoformat()
    reservation = datos.cambiar_estado_reserva(
        oid, 'ACTIVA', {'estado': 'NO_SHOW', 'no_show_at': datetime.utcnow()},
        condiciones={'reserva_date': {'$lte': hoy}})
    if reservation is None:
        pendiente = datos.buscar_reserva(oid)
        if pendiente and pendiente.get('estado') == 'ACTIVA':
            return Response(
                {'error': f"La reserva es para el {pendiente.get('date')}. "
                          'La inasistencia solo puede registrarse el día de la reserva.'},
                status=409,
            )
        return Response({'error': 'Reserva no encontrada o ya no está activa.'}, status=404)

    # La lógica vive en attendance.py para que el registro individual y el
    # procesamiento general de la jornada apliquen exactamente la misma regla.
    from .attendance import aplicar_inasistencia
    owner, penalizado = aplicar_inasistencia(reservation['email'])

    return Response({
        'message': 'Inasistencia registrada.',
        'no_show_count': (owner or {}).get('no_show_count', 0),
        'no_show_limite': reglas.NO_SHOW_LIMITE,
        'inasistencias_restantes': reglas.inasistencias_restantes(owner),
        'penalizado': penalizado,
    })
