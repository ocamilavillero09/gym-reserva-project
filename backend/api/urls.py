from django.urls import path
from . import views

urlpatterns = [
    path('auth/register/',              views.register,            name='register'),
    path('auth/login/',                 views.login,               name='login'),
    path('slots/',                      views.get_slots,           name='slots'),
    path('reservations/',               views.reservations,        name='reservations'),
    path('reservations/<str:reservation_id>/', views.cancel_reservation, name='cancel-reservation'),
]
