from django.urls import path
from . import views, features, reports, attendance

urlpatterns = [
    # Auth
    path('auth/register/',              views.register,            name='register'),
    path('auth/login/',                 views.login,               name='login'),
    path('auth/session/',               views.session,             name='session'),

    # RF21 — Gestión de usuarios (solo el administrador principal crea ADMIN)
    path('admin/users/',                views.admin_users,         name='admin-users'),
    # RF22 — Retirar / restaurar el rol de administrador
    path('admin/users/<str:user_email>/', views.admin_user_detail, name='admin-user-detail'),

    # Slots y reservas (core)
    path('slots/',                      views.get_slots,           name='slots'),
    path('reservations/',               views.reservations,        name='reservations'),

    # RF11 — Historial (antes de las rutas con <reservation_id> para no colisionar)
    path('reservations/history/',       features.reservation_history, name='history'),

    path('reservations/<str:reservation_id>/',          views.cancel_reservation,    name='cancel-reservation'),
    path('reservations/<str:reservation_id>/no-show/',  views.mark_no_show,          name='mark-no-show'),
    path('reservations/<str:reservation_id>/complete/', features.complete_reservation, name='complete-reservation'),  # RF17

    # RF12 — Lista de espera
    path('slots/<int:slot_id>/waitlist/', features.waitlist,        name='waitlist'),

    # RF13 — Perfil y metas
    path('users/profile/',              features.user_profile,      name='profile'),

    # RF15 — Calificaciones
    path('ratings/',                    features.ratings,           name='ratings'),

    # RF16 — Aforo · RF17 — Reporte por estudiante
    path('reports/occupancy/',          features.occupancy_report,  name='occupancy'),
    path('reports/students/',           features.students_report,   name='students-report'),

    # RF18 — Máquinas
    path('machines/',                   features.machines,          name='machines'),
    path('machines/<int:machine_id>/',  features.machine_detail,    name='machine-detail'),

    # RF19 — Exportación del reporte por estudiante
    path('reports/usage.csv',           reports.usage_csv,          name='usage-csv'),
    path('reports/usage.pdf',           reports.usage_pdf,          name='usage-pdf'),

    # ── Asistencia, inasistencias y penalizaciones ────────────────────────
    # RF11 — El entrenador busca al estudiante por su DOCUMENTO de identidad
    path('students/lookup/',            attendance.student_lookup,     name='student-lookup'),
    # RF13 — Registrar la asistencia del estudiante
    path('attendance/register/',        attendance.register_attendance, name='attendance-register'),
    # RF14 — Estudiantes con reserva y sin asistencia registrada
    path('attendance/pending/',         attendance.pending_attendance,  name='attendance-pending'),
    # RF15/RF16 — Procesar de forma general las inasistencias de la jornada
    path('attendance/process/',         attendance.process_no_shows,    name='attendance-process'),

    # RF18 — Reporte personal del estudiante (inasistencias y penalizaciones)
    path('reports/personal/',           attendance.personal_report,     name='personal-report'),
    # RF19 — Reporte general diario · RF20 — el mismo reporte en PDF
    path('reports/daily/',              attendance.daily_report,        name='daily-report'),
    path('reports/daily.pdf',           reports.daily_pdf,              name='daily-pdf'),
]
