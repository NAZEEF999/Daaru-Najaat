"""
Email notification service for Daaru Najat.
Uses Django's email backend — configure Gmail SMTP in .env to activate.
Falls back to console printing if EMAIL_BACKEND is not set.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_appointment_confirmation(appointment):
    """Send confirmation email to patient after booking."""
    if not appointment.contact_email:
        return  # No email address — skip silently

    from .models import SiteSettings
    site = SiteSettings.get()

    subject = f'Appointment Received — {site.site_name}'
    context = {
        'site_name':       site.site_name,
        'patient_name':    appointment.contact_name,
        'service_name':    appointment.service_name or 'General Consultation',
        'appointment_date': str(appointment.appointment_date) if appointment.appointment_date else '',
        'preferred_time':  appointment.preferred_time or '',
        'phone':           appointment.contact_phone,
        'contact_phone':   site.contact_phone,
        'whatsapp_number': site.whatsapp_number,
        'address':         site.address,
        'notes':           appointment.notes or '',
    }

    html_body  = render_to_string('emails/appointment_confirmation.html', context)
    text_body  = (
        f"Salaam {appointment.contact_name},\n\n"
        f"Your appointment at {site.site_name} has been received.\n"
        f"Service: {context['service_name']}\n"
        f"Date: {context['appointment_date'] or 'To be confirmed'}\n"
        f"Time: {context['preferred_time'] or 'To be confirmed'}\n\n"
        f"We will call you at {appointment.contact_phone} to confirm.\n\n"
        f"WE CURE, ALLAH HEALS.\n{site.site_name}"
    )

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[appointment.contact_email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        logger.info(f'Confirmation email sent to {appointment.contact_email}')
    except Exception as e:
        logger.error(f'Email send failed: {e}')


def send_appointment_status_update(appointment):
    """Notify patient when admin changes appointment status."""
    if not appointment.contact_email:
        return

    from .models import SiteSettings
    site = SiteSettings.get()

    STATUS_MESSAGES = {
        'confirmed': 'Your appointment has been CONFIRMED.',
        'cancelled': 'Your appointment has been cancelled. Please contact us to reschedule.',
        'completed': 'Thank you for visiting us. We hope you found healing and relief.',
    }

    msg_text = STATUS_MESSAGES.get(appointment.status)
    if not msg_text:
        return

    subject  = f'Appointment Update — {site.site_name}'
    body     = (
        f"Salaam {appointment.contact_name},\n\n"
        f"{msg_text}\n\n"
        f"Service: {appointment.service_name or 'General Consultation'}\n"
        f"Date: {appointment.appointment_date or 'N/A'}\n\n"
        f"Questions? Call: {site.contact_phone}\n\n"
        f"WE CURE, ALLAH HEALS.\n{site.site_name}"
    )

    try:
        from django.core.mail import send_mail
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL,
                  [appointment.contact_email], fail_silently=False)
    except Exception as e:
        logger.error(f'Status update email failed: {e}')
