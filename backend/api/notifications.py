"""
Módulo de notificaciones por correo.

La interfaz de usuario promete un "correo de confirmación automático" al
reservar y avisa que el cupo se libera al cancelar. Aquí se implementa ese
envío usando el sistema de correo de Django.

Por defecto se usa el backend de consola (EMAIL_BACKEND=console), de modo que
el "correo" se imprime en los logs del contenedor — esto es ideal para
desarrollo, demos y para que la observabilidad (Loki/Grafana) capture el
evento sin necesidad de un servidor SMTP real. Si se configuran las variables
de entorno SMTP (EMAIL_HOST, EMAIL_HOST_USER, ...) Django enviará correos
reales sin cambiar este código.
"""
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger('gym.notifications')


def _send(to_email: str, subject: str, body: str) -> None:
    """Envía un correo de forma tolerante a fallos.

    Un fallo de SMTP nunca debe tumbar la operación de negocio (reservar /
    cancelar), por eso se captura cualquier excepción y solo se registra.
    """
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info('Correo enviado a %s: %s', to_email, subject)
    except Exception as exc:  # noqa: BLE001 - notificar nunca debe romper el flujo
        logger.warning('No se pudo enviar correo a %s: %s', to_email, exc)


def send_reservation_confirmation(email: str, name: str, hour: str, date: str) -> None:
    """Confirmación de reserva (lo que la UI anuncia al confirmar)."""
    _send(
        email,
        'Reserva confirmada — Gimnasio UdeM',
        (
            f'Hola {name},\n\n'
            f'Tu reserva fue confirmada para el bloque de las {hour} ({date}).\n\n'
            'Recuerda: si no puedes asistir, cancela tu reserva con anticipación '
            'para liberar el cupo a otro compañero.\n\n'
            'Gimnasio Universidad de Medellín.'
        ),
    )


def send_waitlist_available(email: str, hour: str) -> None:
    """Avisa al primero en lista de espera que se liberó un cupo (RF12)."""
    _send(
        email,
        '¡Se liberó un cupo! — Gimnasio UdeM',
        (
            f'Hola,\n\n'
            f'Se liberó un cupo en el bloque de las {hour}. Ingresa a la app y '
            'resérvalo antes de que otro compañero lo tome.\n\n'
            'Gimnasio Universidad de Medellín.'
        ),
    )


def send_cancellation_notice(email: str, hour: str) -> None:
    """Aviso de cancelación: confirma que el cupo quedó liberado."""
    _send(
        email,
        'Reserva cancelada — Gimnasio UdeM',
        (
            f'Hola,\n\n'
            f'Tu reserva del bloque de las {hour} fue cancelada y el cupo quedó '
            'liberado inmediatamente para otros estudiantes.\n\n'
            'Gimnasio Universidad de Medellín.'
        ),
    )
