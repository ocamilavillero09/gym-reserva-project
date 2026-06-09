from django.urls import path
from . import views, features, reports, push

urlpatterns = [
    # Auth
    path('auth/register/',              views.register,            name='register'),
    path('auth/login/',                 views.login,               name='login'),

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

    # RF16 / RF17 — Reportes
    path('reports/occupancy/',          features.occupancy_report,  name='occupancy'),
    path('reports/no-shows/',           features.no_show_report,    name='no-shows'),

    # RF18 — Máquinas
    path('machines/',                   features.machines,          name='machines'),
    path('machines/<int:machine_id>/',  features.machine_detail,    name='machine-detail'),

    # RF19 — Exportación
    path('reports/usage.csv',           reports.usage_csv,          name='usage-csv'),
    path('reports/usage.pdf',           reports.usage_pdf,          name='usage-pdf'),

    # RF14 — Push
    path('push/public-key/',            push.public_key,            name='push-public-key'),
    path('push/subscribe/',             push.subscribe,             name='push-subscribe'),
    path('push/remind/',                push.remind,                name='push-remind'),
]
