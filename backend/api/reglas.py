"""
REGLAS DE NEGOCIO DEL GIMNASIO

Esta capa no toca la base de datos ni responde peticiones: solo contiene los
límites, los cálculos y los formatos que definen cómo funciona el gimnasio.
Recibe datos ya cargados y devuelve valores; por eso se puede leer y razonar
sin saber nada de MongoDB ni de Django.

Las tres capas del backend:
    reglas.py     -> qué reglas rigen el gimnasio      (este archivo)
    datos.py      -> cómo se consultan y guardan datos
    views.py y compañía -> qué expone la API
"""
from datetime import date, datetime, timedelta

from django.utils import timezone

# ──────────────────────────────────────────────────────────────────────────
# ROLES Y ESTADOS
# ──────────────────────────────────────────────────────────────────────────
# SIN_ROL es el estado final de una cuenta a la que se le retiró el rol de
# administrador.
ROLES = ('ESTUDIANTE', 'ENTRENADOR', 'ADMIN', 'SIN_ROL')
ESTADOS = ('ACTIVO', 'PENALIZADO', 'INACTIVO')

# El dominio del correo determina el rol: no se elige en el formulario, se
# deduce del correo con el que la persona se registra. Así un estudiante no
# puede auto-asignarse un rol de entrenador o administrador.
DOMINIOS_ROL = {
    '@soyudemedellin.edu.co': 'ESTUDIANTE',
    '@udem.edu.co':           'ENTRENADOR',
    '@udemedellin.edu.co':    'ADMIN',
}

ROLES_STAFF = ('ENTRENADOR', 'ADMIN')

# ──────────────────────────────────────────────────────────────────────────
# LÍMITES CONFIGURABLES
# ──────────────────────────────────────────────────────────────────────────
MAX_RESERVAS_POR_DIA = 1       # una única reserva activa por día
NO_SHOW_LIMITE = 5             # inasistencias que provocan la penalización
NO_SHOW_ALERTA = 2             # avisar cuando falten 2 inasistencias
PENALIZACION_DIAS_HABILES = 5  # duración de la penalización
DOCUMENTO_MIN = 6              # longitud mínima del documento de identidad

# No existe un límite de cancelaciones: cancelar no sanciona. Ver el bloque
# «CANCELACIONES» más abajo.

# Nombres en español para las fechas: strftime depende del locale del sistema
# (en los contenedores suele ser inglés), así que se formatea a mano.
_DIAS = ('lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo')
_MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
          'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre')


# ──────────────────────────────────────────────────────────────────────────
# IDENTIDAD Y ROLES
# ──────────────────────────────────────────────────────────────────────────
def normalizar_documento(documento) -> str:
    """Deja el documento sin espacios, puntos ni guiones: '1.020 304' -> '1020304'."""
    texto = str(documento or '').strip()
    return texto.replace('.', '').replace(' ', '').replace('-', '')


def normalizar_correo(correo) -> str:
    """Deja el correo en minúsculas y sin espacios sobrantes."""
    return str(correo or '').strip().lower()


def role_for_email(email: str):
    """Rol que corresponde al dominio del correo, o None si no es institucional."""
    email = normalizar_correo(email)
    for dominio, rol in DOMINIOS_ROL.items():
        if email.endswith(dominio):
            return rol
    return None


def es_staff(user: dict) -> bool:
    """True si la persona es entrenador o administrador."""
    return bool(user and user.get('role') in ROLES_STAFF)


def dominios_texto() -> str:
    """'@soyudemedellin.edu.co (estudiante), @udem.edu.co (profesor), ...'"""
    etiquetas = {'ESTUDIANTE': 'estudiante', 'ENTRENADOR': 'profesor', 'ADMIN': 'administrador'}
    return ', '.join(f'{d} ({etiquetas[r]})' for d, r in DOMINIOS_ROL.items())


# ──────────────────────────────────────────────────────────────────────────
# FECHAS DEL GIMNASIO
# ──────────────────────────────────────────────────────────────────────────
def hoy_local() -> date:
    """Fecha de hoy en la zona horaria del gimnasio (America/Bogota)."""
    return timezone.localtime().date()


def fecha_reserva() -> date:
    """Las reservas siempre son para el DÍA SIGUIENTE."""
    return hoy_local() + timedelta(days=1)


def formato_fecha_es(d: date) -> str:
    """'martes 18 de agosto de 2026' — etiqueta legible para la interfaz."""
    return f'{_DIAS[d.weekday()]} {d.day} de {_MESES[d.month - 1]} de {d.year}'


# ──────────────────────────────────────────────────────────────────────────
# INFORMACIÓN DE ENTRENAMIENTO DEL ESTUDIANTE
#
# Rangos con los que se acepta un dato como creíble. No son caprichos: un peso
# negativo o una altura de 9 metros ensucian el perfil y falsean cualquier
# cálculo que se haga después con ellos.
# ──────────────────────────────────────────────────────────────────────────
RANGO_EDAD   = (10, 100)    # años
RANGO_PESO   = (20, 300)    # kilogramos
RANGO_ALTURA = (100, 250)   # centímetros
META_MAX     = 120          # caracteres del objetivo de entrenamiento

_RANGOS = {'edad': RANGO_EDAD, 'peso': RANGO_PESO, 'altura': RANGO_ALTURA}
_UNIDAD = {'edad': 'años', 'peso': 'kg', 'altura': 'cm'}
_ARTICULO = {'edad': 'La edad', 'peso': 'El peso', 'altura': 'La altura'}


def validar_datos_entrenamiento(datos: dict):
    """Revisa edad, peso, altura y objetivo antes de guardarlos.

    Devuelve (valores_limpios, error). Si error no es None, no se guarda nada.
    Un campo enviado vacío o nulo significa «borrar este dato», y se acepta.
    """
    limpios = {}

    for campo, (minimo, maximo) in _RANGOS.items():
        if campo not in datos:
            continue
        valor = datos[campo]
        if valor is None or valor == '':
            limpios[campo] = None          # el estudiante borra el dato
            continue
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return None, f'{_ARTICULO[campo]} debe ser un número.'
        if numero != numero or numero in (float('inf'), float('-inf')):
            return None, f'{_ARTICULO[campo]} debe ser un número.'
        if not (minimo <= numero <= maximo):
            return None, (f'{_ARTICULO[campo]} debe estar entre {minimo} y {maximo} '
                          f'{_UNIDAD[campo]}.')
        limpios[campo] = int(numero) if campo == 'edad' else round(numero, 1)

    if 'meta' in datos:
        meta = str(datos['meta'] or '').strip()
        if len(meta) > META_MAX:
            return None, f'El objetivo no puede pasar de {META_MAX} caracteres.'
        limpios['meta'] = meta

    return limpios, None


def jornada_ya_llegada(fecha_iso: str) -> bool:
    """True si esa fecha es hoy o ya pasó.

    La asistencia y la inasistencia solo pueden registrarse cuando la jornada
    ha llegado: mientras la reserva sea para mañana, el estudiante todavía no
    ha tenido ocasión de presentarse, así que ni asistió ni faltó.
    """
    return bool(fecha_iso) and fecha_iso <= hoy_local().isoformat()


def limitar_a_hoy(fecha_iso: str) -> str:
    """Recorta una fecha futura a hoy.

    Cerrar la jornada de un día que aún no ha ocurrido convertiría en
    inasistencias reservas que todavía se pueden cumplir.
    """
    hoy = hoy_local().isoformat()
    return hoy if not fecha_iso or fecha_iso > hoy else fecha_iso


def add_business_days(start: datetime, days: int) -> datetime:
    """Suma N días hábiles (lunes a viernes) a una fecha."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def fin_de_penalizacion(desde: datetime = None) -> datetime:
    """Hasta cuándo dura la penalización que empieza ahora."""
    return add_business_days(desde or datetime.utcnow(), PENALIZACION_DIAS_HABILES)


# ──────────────────────────────────────────────────────────────────────────
# INASISTENCIAS Y PENALIZACIONES
# ──────────────────────────────────────────────────────────────────────────
def inasistencias_restantes(user: dict) -> int:
    """Cuántas inasistencias le faltan al estudiante para ser penalizado."""
    usadas = (user or {}).get('no_show_count', 0)
    return max(NO_SHOW_LIMITE - usadas, 0)


def alerta_inasistencias(user: dict):
    """Mensaje sobre el estado de inasistencias del estudiante, o None."""
    restantes = inasistencias_restantes(user)
    usadas = (user or {}).get('no_show_count', 0)
    if restantes == 0:
        return (f'Alcanzaste el límite de {NO_SHOW_LIMITE} inasistencias. '
                'Tu cuenta quedó penalizada.')
    if usadas > 0 and restantes <= NO_SHOW_ALERTA:
        veces = 'inasistencia' if restantes == 1 else 'inasistencias'
        return (f'Llevas {usadas} inasistencias. Estás a {restantes} {veces} '
                'de ser penalizado.')
    return None


def alcanza_limite_inasistencias(user: dict) -> bool:
    """True si con las inasistencias acumuladas corresponde penalizar la cuenta."""
    return (user or {}).get('no_show_count', 0) >= NO_SHOW_LIMITE


# ──────────────────────────────────────────────────────────────────────────
# CANCELACIONES
#
# Cancelar NO es faltar. Son dos cosas distintas y el sistema las trata como
# tales:
#
#   · Inasistencia -> el estudiante reservó y no se presentó. Desperdició un
#     cupo que nadie pudo usar. Se acumula y penaliza la cuenta al llegar al
#     límite.
#   · Cancelación  -> el estudiante avisa a tiempo y devuelve el cupo para que
#     otra persona lo aproveche. Es el comportamiento que el gimnasio quiere
#     fomentar, así que NO acumula sanción de ningún tipo.
#
# Por eso aquí no hay ni límite ni alerta de cancelaciones: el contador
# `cancel_count` existe solo como información para el estudiante y para el
# reporte del personal.
# ──────────────────────────────────────────────────────────────────────────
def cancelaciones(user: dict) -> int:
    """Cuántas veces ha cancelado el usuario. Es solo informativo."""
    return (user or {}).get('cancel_count', 0)


def penalizacion_vigente(user: dict) -> bool:
    """True si la cuenta está penalizada y la sanción todavía no ha vencido."""
    if (user or {}).get('estado') != 'PENALIZADO':
        return False
    hasta = user.get('penalizado_hasta')
    return bool(hasta and hasta > datetime.utcnow())
