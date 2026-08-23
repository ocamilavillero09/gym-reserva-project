"""
RUTAS DE LA API

Cada ruta responde a uno o varios requisitos funcionales de la especificación
RF01–RF25. No hay rutas sin requisito que las respalde: lo que no aparece en la
especificación no está en el sistema.

Las marcadas como [IGNORADO] funcionan igual, pero quedaron fuera del alcance
de pruebas acordado con el equipo.

Cuando una ruta responde a varios requisitos se indica qué le toca a cada uno.
En la función que la atiende está la explicación completa.
"""
from django.urls import path

from . import views, features, reports, attendance

urlpatterns = [
    # ── Autenticación y perfiles ──────────────────────────────────────────
    # RF01 — El formulario: nombre, correo institucional y documento de identidad
    # RF03 — El rol: se deduce del dominio del correo, no se elige
    path('auth/register/',              views.register,             name='register'),
    # RF02 — Inicio de sesión con el documento como contraseña
    path('auth/login/',                 views.login,                name='login'),
    # RF02 — Recuperación de la sesión al recargar la página
    path('auth/session/',               views.session,              name='session'),
    # RF04 — Perfil del estudiante: consulta sus datos y EDITA con PUT su
    #        información de entrenamiento (edad, peso, altura y objetivo)
    # RF05 — Perfil del personal: entrenadores y administradores solo consultan
    #        con GET; no tienen datos de entrenamiento porque no reservan
    path('users/profile/',              features.user_profile,      name='profile'),

    # ── Administración de usuarios ────────────────────────────────────────
    # RF21 · [IGNORADO] — El administrador principal crea cuentas de administrador
    path('admin/users/',                views.admin_users,          name='admin-users'),
    # RF22 · [IGNORADO] — Retirar o restaurar el rol de administrador
    path('admin/users/<str:user_email>/', views.admin_user_detail,  name='admin-user-detail'),

    # ── Bloques horarios y reservas ───────────────────────────────────────
    # RF06 · [IGNORADO] — La lista de bloques horarios y la fecha de la jornada
    # RF07 · [IGNORADO] — El cupo libre de cada bloque para esa fecha
    # RF12 — El personal consulta esta misma respuesta, pero no puede reservar
    path('slots/',                      views.get_slots,            name='slots'),
    # RF10 — GET:  las reservas activas del estudiante
    # RF08 — POST: crea la reserva del día siguiente respetando el aforo
    # RF09 — POST: rechaza si ya tiene una reserva para esa jornada
    # RF23 · [IGNORADO] — POST: el aviso de reserva confirmada de la respuesta
    path('reservations/',               views.reservations,         name='reservations'),
    # RF17 — Historial (antes de las rutas con <reservation_id> para no colisionar)
    path('reservations/history/',       features.reservation_history, name='history'),
    # RF24 · [IGNORADO] — La cancelación: la reserva se anula y libera su cupo
    # RF25 — El aviso: qué reserva se canceló y que el cupo quedó liberado
    path('reservations/<str:reservation_id>/',         views.cancel_reservation, name='cancel-reservation'),
    # RF16 — Registro individual de una inasistencia
    path('reservations/<str:reservation_id>/no-show/', views.mark_no_show,       name='mark-no-show'),

    # ── Asistencia e inasistencias ────────────────────────────────────────
    # RF11 — El entrenador busca al estudiante por su documento de identidad
    path('students/lookup/',            attendance.student_lookup,      name='student-lookup'),
    # RF13 — Registrar la asistencia del estudiante
    path('attendance/register/',        attendance.register_attendance, name='attendance-register'),
    # RF14 · [IGNORADO] — Estudiantes con reserva y sin asistencia registrada
    path('attendance/pending/',         attendance.pending_attendance,  name='attendance-pending'),
    # RF15 · [IGNORADO] — El recorrido: marca NO_SHOW las reservas sin asistencia
    # RF16 — La consecuencia: suma la inasistencia y penaliza al llegar al límite
    path('attendance/process/',         attendance.process_no_shows,    name='attendance-process'),

    # ── Reportes ──────────────────────────────────────────────────────────
    # RF07 · [IGNORADO] — El cálculo: reservados, libres y porcentaje de ocupación
    # RF12 — El destinatario: entrenadores y administradores
    path('reports/occupancy/',          features.occupancy_report,      name='occupancy'),
    # RF18 — Reporte personal de inasistencias y penalizaciones
    path('reports/personal/',           attendance.personal_report,     name='personal-report'),
    # RF19 · [IGNORADO] — Los datos de la jornada: asistencias, inasistencias y totales
    path('reports/daily/',              attendance.daily_report,        name='daily-report'),
    # RF20 · [IGNORADO] — Los mismos datos de RF19 maquetados en PDF, para imprimir
    path('reports/daily.pdf',           reports.daily_pdf,              name='daily-pdf'),
]
