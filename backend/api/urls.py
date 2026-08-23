"""
RUTAS DE LA API

Cada ruta responde a uno o varios requisitos funcionales de la especificación
RF01–RF25. No hay rutas sin requisito que las respalde: lo que no aparece en la
especificación no está en el sistema.
"""
from django.urls import path

from . import views, features, reports, attendance

urlpatterns = [
    # ── Autenticación y perfiles ──────────────────────────────────────────
    # RF01 — Registro con nombre, correo institucional y documento
    # RF03 — El rol se asigna según el dominio del correo
    path('auth/register/',              views.register,             name='register'),
    # RF02 — Inicio de sesión con el documento como contraseña
    path('auth/login/',                 views.login,                name='login'),
    # RF02 — Recuperación de la sesión al recargar la página
    path('auth/session/',               views.session,              name='session'),
    # RF04 — Perfil del estudiante (edad, peso, altura y objetivo)
    # RF05 — Perfil de entrenadores y administradores
    path('users/profile/',              features.user_profile,      name='profile'),

    # ── Administración de usuarios ────────────────────────────────────────
    # RF21 — El administrador principal crea cuentas de administrador
    path('admin/users/',                views.admin_users,          name='admin-users'),
    # RF22 — Retirar o restaurar el rol de administrador
    path('admin/users/<str:user_email>/', views.admin_user_detail,  name='admin-user-detail'),

    # ── Bloques horarios y reservas ───────────────────────────────────────
    # RF06 — Bloques horarios disponibles · RF07 — Cupos ocupados y libres
    # RF12 — El personal visualiza los bloques y su disponibilidad
    path('slots/',                      views.get_slots,            name='slots'),
    # RF08 — Reserva para el día siguiente · RF09 — Una reserva por día
    # RF10 — Consulta de las reservas hechas · RF23 — Notificación de reserva
    path('reservations/',               views.reservations,         name='reservations'),
    # RF17 — Historial (antes de las rutas con <reservation_id> para no colisionar)
    path('reservations/history/',       features.reservation_history, name='history'),
    # RF24 — Cancelación de la reserva · RF25 — Notificación de cancelación
    path('reservations/<str:reservation_id>/',         views.cancel_reservation, name='cancel-reservation'),
    # RF16 — Registro individual de una inasistencia
    path('reservations/<str:reservation_id>/no-show/', views.mark_no_show,       name='mark-no-show'),

    # ── Asistencia e inasistencias ────────────────────────────────────────
    # RF11 — El entrenador busca al estudiante por su documento de identidad
    path('students/lookup/',            attendance.student_lookup,      name='student-lookup'),
    # RF13 — Registrar la asistencia del estudiante
    path('attendance/register/',        attendance.register_attendance, name='attendance-register'),
    # RF14 — Estudiantes con reserva y sin asistencia registrada
    path('attendance/pending/',         attendance.pending_attendance,  name='attendance-pending'),
    # RF15 — Procesar la jornada · RF16 — Penalizar al llegar al límite
    path('attendance/process/',         attendance.process_no_shows,    name='attendance-process'),

    # ── Reportes ──────────────────────────────────────────────────────────
    # RF07 — Cupos ocupados y disponibles · RF12 — Aforo para el personal
    path('reports/occupancy/',          features.occupancy_report,      name='occupancy'),
    # RF18 — Reporte personal de inasistencias y penalizaciones
    path('reports/personal/',           attendance.personal_report,     name='personal-report'),
    # RF19 — Reporte general diario del gimnasio
    path('reports/daily/',              attendance.daily_report,        name='daily-report'),
    # RF20 — El mismo reporte diario en PDF, para imprimir
    path('reports/daily.pdf',           reports.daily_pdf,              name='daily-pdf'),
]
