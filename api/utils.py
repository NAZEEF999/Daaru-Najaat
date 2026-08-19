from .models import Notification, SiteSettings
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def create_notification(ntype, title, message):
    """Create a bell notification in the admin panel."""
    Notification.objects.create(
        type=ntype,
        title=title,
        message=message,
        is_read=False
    )


def get_whatsapp_url(number: str, message: str) -> str:
    clean = ''.join(c for c in number if c.isdigit())
    from urllib.parse import quote
    return f'https://wa.me/{clean}?text={quote(message)}'


def trigger_whatsapp_alert(message: str) -> str | None:
    try:
        settings = SiteSettings.get()
        if not settings.whatsapp_number:
            logger.warning('No WhatsApp number configured in SiteSettings — cannot build notification link.')
            return None
        return get_whatsapp_url(settings.whatsapp_number, message)
    except Exception:
        logger.exception('Failed to build WhatsApp notification link.')
        return None


def build_appointment_wa_message(appointment) -> str:
    try:
        site = SiteSettings.get()
        site_name = site.site_name
    except Exception:
        site_name = 'Daaru Najat'
    # Deliberately excludes appointment.notes: WhatsApp is an external
    # channel outside the authorized staff dashboard, so no medical
    # notes/symptoms/history ever go into this message.
    return (
        f"New Appointment Request — {site_name}\n\n"
        f"Name: {appointment.contact_name}\n"
        f"Service: {appointment.service_name or 'General Consultation'}\n"
        f"Preferred Date: {appointment.appointment_date or 'To be confirmed'}\n"
        f"Preferred Time: {appointment.preferred_time or 'To be confirmed'}\n"
        f"Phone: {appointment.contact_phone}\n"
        f"Email: {appointment.contact_email or 'Not provided'}\n\n"
        f"Please review this appointment in the staff dashboard."
    )


def build_order_wa_message(order) -> str:
    try:
        site = SiteSettings.get()
        site_name = site.site_name
    except Exception:
        site_name = 'Daaru Najat'
    return (
        f"New Product Order at {site_name}!\n"
        f"Customer: {order.customer_name}\n"
        f"Product: {order.product_name}\n"
        f"Quantity: {order.quantity}\n"
        f"Price: NGN {order.price:,.0f} each\n"
        f"Total: NGN {order.total:,.0f}\n"
        f"Phone: {order.customer_phone}\n"
        f"Email: {order.customer_email or 'Not provided'}"
    )


def build_inquiry_wa_message(inquiry) -> str:
    try:
        site = SiteSettings.get()
        site_name = site.site_name
    except Exception:
        site_name = 'Daaru Najat'
    return (
        f"New Inquiry at {site_name}!\n"
        f"From: {inquiry.name}\n"
        f"Phone: {inquiry.phone or 'Not provided'}\n"
        f"Email: {inquiry.email or 'Not provided'}\n"
        f"Message: {inquiry.message}"
    )


def send_admin_email(subject: str, message: str) -> None:
    """Send email notification to admin."""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        admin_email = SiteSettings.get().contact_email
        if not admin_email:
            return
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(f'Failed to send admin notification email: {subject}')


def notify_admin_appointment(appointment) -> None:
    """Email admin about new appointment."""
    send_admin_email(
        subject=f'New Appointment — {appointment.contact_name}',
        message=build_appointment_wa_message(appointment)
    )


def notify_admin_order(order) -> None:
    """Email admin about new product order."""
    send_admin_email(
        subject=f'New Product Order — {order.customer_name}',
        message=build_order_wa_message(order)
    )


def notify_admin_inquiry(inquiry) -> None:
    """Email admin about new inquiry."""
    send_admin_email(
        subject=f'New Inquiry — {inquiry.name}',
        message=build_inquiry_wa_message(inquiry)
    )



    # ── UNFOLD CALLBACKS ──────────────────────────────────────────────────────────

def appointment_badge(request):
    from .models import Appointment
    count = Appointment.objects.filter(status='pending').count()
    return str(count) if count > 0 else None


def inquiry_badge(request):
    from .models import Inquiry
    count = Inquiry.objects.filter(is_read=False).count()
    return str(count) if count > 0 else None


def notification_badge(request):
    from .models import Notification
    count = Notification.objects.filter(is_read=False).count()
    return str(count) if count > 0 else None


def order_badge(request):
    from .models import ProductOrder
    count = ProductOrder.objects.filter(status='pending').count()
    return str(count) if count > 0 else None


def environment_callback(request):
    if settings.DEBUG:
        return "Development"
    return "Production"


def dashboard_callback(request, context):
    from django.urls import reverse
    from .models import Appointment, Inquiry, Notification, Service, Product, ProductOrder, Healer
    context.update({
        "pending_appointments": Appointment.objects.filter(status='pending').count(),
        "unread_inquiries":     Inquiry.objects.filter(is_read=False).count(),
        "pending_orders":       ProductOrder.objects.filter(status='pending').count(),
        "unread_notifications": Notification.objects.filter(is_read=False).count(),
        "total_services":       Service.objects.filter(active=True).count(),
        "total_products":       Product.objects.filter(active=True).count(),
        "total_healers":        Healer.objects.filter(is_active=True).count(),
        "recent_appointments":  Appointment.objects.select_related('service').order_by('-created_at')[:6],
        "recent_inquiries":     Inquiry.objects.order_by('-created_at')[:5],
        # This admin homepage is an internal/emergency fallback -- its own
        # quick actions should route staff back to the real staff
        # interface (/dashboard/) rather than deeper into admin.
        # "Add Appointment" has no dashboard equivalent: appointments are
        # only created through the public booking flow by design, so this
        # points at the appointments list instead of a nonexistent create route.
        "quick_actions": [
            ("View Appointments", reverse('dashboard:appointments'), "calendar_add_on"),
            ("Add Service", reverse('dashboard:service_add'), "add_circle"),
            ("Add Product", reverse('dashboard:product_add'), "eco"),
            ("Add Healer", reverse('dashboard:healer_add'), "person_add"),
            ("Write Blog Post", reverse('dashboard:blog_add'), "edit_note"),
            ("Site Settings", reverse('dashboard:site_settings'), "settings"),
        ],
    })
    return context