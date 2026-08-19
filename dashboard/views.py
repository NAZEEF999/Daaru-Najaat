from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import date

from api.models import (
    Appointment, Inquiry, Notification, ProductOrder, Service, Product,
    Healer, BlogPost, Testimonial, Subscriber, SiteSettings,
)
from api.utils import (
    create_notification, trigger_whatsapp_alert, build_appointment_wa_message,
)
from api.email_service import send_appointment_status_update
from accounts.models import PatientProfile
import logging

logger = logging.getLogger(__name__)

from .auth import staff_required


def _badge_counts():
    return {
        'unread_notifications_count': Notification.objects.filter(is_read=False).count(),
        'unread_messages_count': Inquiry.objects.filter(is_read=False).count(),
    }


# ── AUTH ──────────────────────────────────────────────────────────────────────
def dashboard_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard:overview')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_staff:
                messages.error(request, "This account doesn't have staff dashboard access.")
            else:
                auth_login(request, user)
                next_url = request.GET.get('next') or request.POST.get('next') or ''
                if not url_has_allowed_host_and_scheme(
                        url=next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                    next_url = ''
                return redirect(next_url or 'dashboard:overview')
        else:
            messages.error(request, 'Invalid staff username/email or password.')
    else:
        form = AuthenticationForm(request)

    return render(request, 'dashboard/login.html', {'form': form})


@staff_required
def dashboard_logout(request):
    auth_logout(request)
    messages.success(request, 'Signed out of the staff dashboard.')
    return redirect('dashboard:login')


def _build_overview_calendar(request):
    """
    Real appointment calendar for the dashboard overview. One query per
    month (not per day), grouped in Python by date. 'Upcoming' = pending or
    confirmed appointments today or in the future -- matches the project's
    real Appointment.STATUS_CHOICES, no separate status system.
    """
    import calendar as cal_module

    today = timezone.localdate()
    try:
        year = int(request.GET.get('cal_year', today.year))
    except (TypeError, ValueError):
        year = today.year
    try:
        month = int(request.GET.get('cal_month', today.month))
    except (TypeError, ValueError):
        month = today.month
    if not (1 <= month <= 12):
        month = today.month
    year = max(1900, min(2200, year))

    first_of_month = date(year, month, 1)
    if month == 12:
        next_month_first, next_year, next_month = date(year + 1, 1, 1), year + 1, 1
    else:
        next_month_first, next_year, next_month = date(year, month + 1, 1), year, month + 1
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    range_start = max(first_of_month, today)  # only "upcoming" (today or later) counts
    appts = (Appointment.objects
             .filter(status__in=['pending', 'confirmed'],
                     appointment_date__gte=range_start,
                     appointment_date__lt=next_month_first)
             .select_related('service', 'healer', 'patient')
             .order_by('appointment_date', 'preferred_time'))

    by_date = {}
    for a in appts:
        key = a.appointment_date.isoformat()
        by_date.setdefault(key, []).append({
            'id': a.pk,
            'time': a.preferred_time or 'TBC',
            'name': a.contact_name,
            'service': a.service_name or 'General Consultation',
            'healer': a.healer.full_name if a.healer_id else 'Unassigned',
            'status': a.status,
            'status_display': a.get_status_display(),
            'detail_url': reverse('dashboard:appointment_detail', args=[a.pk]),
        })

    weeks = []
    for week in cal_module.Calendar(firstweekday=6).monthdatescalendar(year, month):
        row = []
        for d in week:
            iso = d.isoformat()
            row.append({
                'date': d, 'day': d.day, 'iso': iso,
                'in_month': d.month == month,
                'is_today': d == today,
                'appointments': by_date.get(iso, []),
                'count': len(by_date.get(iso, [])),
            })
        weeks.append(row)

    return {
        'cal_weeks': weeks,
        'cal_month_name': cal_module.month_name[month],
        'cal_year': year,
        'cal_month': month,
        'cal_today': today,
        'cal_prev_year': prev_year, 'cal_prev_month': prev_month,
        'cal_next_year': next_year, 'cal_next_month': next_month,
        'cal_data_json': by_date,
        'cal_day_names': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    }


# ── OVERVIEW ──────────────────────────────────────────────────────────────────
@staff_required
def overview(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    stats = {
        'total_appointments':     Appointment.objects.count(),
        'pending_appointments':   Appointment.objects.filter(status='pending').count(),
        'today_appointments':     Appointment.objects.filter(appointment_date=today).count(),
        'completed_this_month':   Appointment.objects.filter(
            status='completed', updated_at__date__gte=month_start).count(),
        'unread_messages':        Inquiry.objects.filter(is_read=False).count(),
        'new_orders':             ProductOrder.objects.filter(status='pending').count(),
        'unread_notifications':   Notification.objects.filter(is_read=False).count(),
    }

    top_services = (Appointment.objects
                    .exclude(service_name='')
                    .values('service_name')
                    .annotate(bookings=Count('id'))
                    .order_by('-bookings')[:5])

    context = {
        'active_nav': 'overview',
        'stats': stats,
        'recent_appointments': Appointment.objects.select_related('service', 'healer').order_by('-created_at')[:6],
        'recent_notifications': Notification.objects.order_by('-created_at')[:6],
        'recent_messages': Inquiry.objects.order_by('-created_at')[:5],
        'top_services': top_services,
        **_badge_counts(),
    }
    context.update(_build_overview_calendar(request))
    return render(request, 'dashboard/overview.html', context)


# ── APPOINTMENTS ──────────────────────────────────────────────────────────────
@staff_required
def appointments_list(request):
    qs = Appointment.objects.select_related('service', 'healer', 'patient').order_by('-created_at')
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(contact_name__icontains=q) | Q(contact_phone__icontains=q) |
                        Q(contact_email__icontains=q))
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/appointments_list.html', {
        'active_nav': 'appointments',
        'page_obj': page, 'active_status': status, 'q': q,
        'status_choices': Appointment.STATUS_CHOICES,
        **_badge_counts(),
    })


@staff_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment.objects.select_related('service', 'healer', 'patient'), pk=pk)
    return render(request, 'dashboard/appointment_detail.html', {
        'active_nav': 'appointments',
        'appointment': appointment,
        'healers': Healer.objects.filter(is_active=True),
        'wa_url': trigger_whatsapp_alert(build_appointment_wa_message(appointment)),
        **_badge_counts(),
    })


@staff_required
@require_POST
def appointment_update_status(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    new_status = request.POST.get('status')
    healer_id = request.POST.get('healer', '')

    if new_status not in dict(Appointment.STATUS_CHOICES):
        messages.error(request, 'Invalid status.')
        return redirect('dashboard:appointment_detail', pk=pk)

    if healer_id:
        appointment.healer_id = healer_id

    # Backend is the source of truth for conflicts — never trust the frontend alone.
    if new_status == 'confirmed':
        appointment.status = 'confirmed'
        if appointment.conflicts_with_confirmed():
            messages.warning(
                request,
                'This time slot is already booked for that healer. Please choose another time '
                'or reassign the healer before confirming.'
            )
            appointment.refresh_from_db(fields=['status'])
            if healer_id:
                appointment.healer_id = healer_id
                appointment.save(update_fields=['healer'])
            return redirect('dashboard:appointment_detail', pk=pk)

    appointment.status = new_status
    try:
        with transaction.atomic():
            appointment.save()
    except IntegrityError:
        # The Python check above already passed, but another staff member's
        # confirmation committed in the gap between that check and this
        # save -- the database-level constraint is the real backstop here.
        # Wrapping the save in its own atomic block/savepoint means this
        # failure rolls back cleanly on PostgreSQL too, instead of poisoning
        # the rest of the request's transaction.
        logger.warning(f'Confirmed-slot race condition caught for appointment {pk}')
        messages.error(
            request,
            'This appointment slot was just taken by another appointment. Please choose another time.'
        )
        return redirect('dashboard:appointment_detail', pk=pk)

    try:
        send_appointment_status_update(appointment)
    except Exception:
        logger.exception(f'Failed to send status-update email for appointment {appointment.pk}')

    if new_status == 'confirmed':
        create_notification('appointment', f'Appointment confirmed: {appointment.contact_name}',
                            f"{appointment.contact_name}'s appointment was confirmed.")
    elif new_status == 'cancelled':
        create_notification('appointment', f'Appointment cancelled: {appointment.contact_name}',
                            f"{appointment.contact_name}'s appointment was cancelled.")

    messages.success(request, f'Appointment marked as {appointment.get_status_display()}.')
    return redirect('dashboard:appointment_detail', pk=pk)


# ── PATIENTS ──────────────────────────────────────────────────────────────────
@staff_required
def patients_list(request):
    q = request.GET.get('q', '').strip()
    qs = PatientProfile.objects.select_related('user').order_by('-created_at')
    if q:
        qs = qs.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) |
                        Q(user__email__icontains=q) | Q(phone__icontains=q))
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/patients_list.html', {
        'active_nav': 'patients',
        'page_obj': page, 'q': q,
        **_badge_counts(),
    })


@staff_required
def patient_detail(request, pk):
    patient = get_object_or_404(PatientProfile.objects.select_related('user'), pk=pk)
    # Medical notes are only ever rendered here, behind @staff_required — never
    # on public pages, WhatsApp messages, or patient-facing confirmations.
    return render(request, 'dashboard/patient_detail.html', {
        'active_nav': 'patients',
        'patient': patient,
        'appointments': patient.appointments,
        **_badge_counts(),
    })


# ── MESSAGES / INQUIRIES ──────────────────────────────────────────────────────
@staff_required
def messages_list(request):
    qs = Inquiry.objects.order_by('-created_at')
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/messages_list.html', {
        'active_nav': 'messages',
        'page_obj': page,
        **_badge_counts(),
    })


@staff_required
def message_detail(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk)
    if not inquiry.is_read:
        inquiry.is_read = True
        inquiry.save(update_fields=['is_read'])
    return render(request, 'dashboard/message_detail.html', {
        'active_nav': 'messages',
        'inquiry': inquiry,
        **_badge_counts(),
    })


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────
@staff_required
def notifications_list(request):
    qs = Notification.objects.order_by('-created_at')
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/notifications_list.html', {
        'active_nav': 'notifications',
        'page_obj': page,
        **_badge_counts(),
    })


@staff_required
@require_POST
def notification_mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return redirect(request.POST.get('next') or 'dashboard:notifications')


@staff_required
@require_POST
def notifications_mark_all_read(request):
    Notification.objects.filter(is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('dashboard:notifications')


# ── ORDERS ────────────────────────────────────────────────────────────────────
@staff_required
def orders_list(request):
    qs = ProductOrder.objects.select_related('product').order_by('-created_at')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/orders_list.html', {
        'active_nav': 'orders',
        'page_obj': page, 'active_status': status,
        'status_choices': ProductOrder.STATUS_CHOICES,
        **_badge_counts(),
    })


@staff_required
@require_POST
def order_update_status(request, pk):
    order = get_object_or_404(ProductOrder, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(ProductOrder.STATUS_CHOICES):
        order.status = new_status
        order.save(update_fields=['status'])
        messages.success(request, f'Order marked as {order.get_status_display()}.')
    return redirect('dashboard:orders')


# ── CATALOG (services / products / healers / blog / testimonials / subscribers) ─
# Full editing (images, rich text) stays in Django admin for now — linked
# directly from each row — while browsing, search, and quick status toggles
# live here in the dashboard.
@staff_required
def services_list(request):
    return render(request, 'dashboard/services_list.html', {
        'active_nav': 'services',
        'services': Service.objects.order_by('sort_order', 'title'),
        **_badge_counts(),
    })


@staff_required
def service_edit(request, pk=None):
    from .forms import ServiceForm
    instance = get_object_or_404(Service, pk=pk) if pk else None
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f'Service {"updated" if pk else "created"}.')
            return redirect('dashboard:services')
        else:
            messages.warning(request, 'Please correct the errors below.')
    else:
        form = ServiceForm(instance=instance)
    return render(request, 'dashboard/service_form.html', {
        'active_nav': 'services', 'form': form, 'is_edit': bool(pk),
        **_badge_counts(),
    })


@staff_required
def products_list(request):
    return render(request, 'dashboard/products_list.html', {
        'active_nav': 'products',
        'products': Product.objects.order_by('sort_order', 'title'),
        **_badge_counts(),
    })


@staff_required
def product_edit(request, pk=None):
    from .forms import ProductForm
    instance = get_object_or_404(Product, pk=pk) if pk else None
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product {"updated" if pk else "created"}.')
            return redirect('dashboard:products')
        else:
            messages.warning(request, 'Please correct the errors below.')
    else:
        form = ProductForm(instance=instance)
    return render(request, 'dashboard/product_form.html', {
        'active_nav': 'products', 'form': form, 'is_edit': bool(pk),
        **_badge_counts(),
    })


@staff_required
def healers_list(request):
    return render(request, 'dashboard/healers_list.html', {
        'active_nav': 'healers',
        'healers': Healer.objects.order_by('-is_featured', 'full_name'),
        **_badge_counts(),
    })


@staff_required
def healer_edit(request, pk=None):
    from .forms import HealerForm
    instance = get_object_or_404(Healer, pk=pk) if pk else None
    if request.method == 'POST':
        form = HealerForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f'Healer {"updated" if pk else "added"}.')
            return redirect('dashboard:healers')
        else:
            messages.warning(request, 'Please correct the errors below.')
    else:
        form = HealerForm(instance=instance)
    return render(request, 'dashboard/healer_form.html', {
        'active_nav': 'healers', 'form': form, 'is_edit': bool(pk),
        **_badge_counts(),
    })


@staff_required
def blog_list(request):
    return render(request, 'dashboard/blog_list.html', {
        'active_nav': 'blog',
        'posts': BlogPost.objects.order_by('-created_at'),
        **_badge_counts(),
    })


@staff_required
def blog_edit(request, pk=None):
    from .forms import BlogPostForm
    instance = get_object_or_404(BlogPost, pk=pk) if pk else None
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f'Post {"updated" if pk else "published"}.')
            return redirect('dashboard:blog')
        else:
            messages.warning(request, 'Please correct the errors below.')
    else:
        form = BlogPostForm(instance=instance)
    return render(request, 'dashboard/blog_form.html', {
        'active_nav': 'blog', 'form': form, 'is_edit': bool(pk),
        **_badge_counts(),
    })


@staff_required
def testimonials_list(request):
    return render(request, 'dashboard/testimonials_list.html', {
        'active_nav': 'testimonials',
        'testimonials': Testimonial.objects.order_by('-created_at'),
        **_badge_counts(),
    })


@staff_required
@require_POST
def testimonial_toggle_approved(request, pk):
    t = get_object_or_404(Testimonial, pk=pk)
    t.is_approved = not t.is_approved
    t.save(update_fields=['is_approved'])
    return redirect('dashboard:testimonials')


@staff_required
def subscribers_list(request):
    qs = Subscriber.objects.order_by('-subscribed_at')
    paginator = Paginator(qs, 40)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/subscribers_list.html', {
        'active_nav': 'subscribers',
        'page_obj': page,
        **_badge_counts(),
    })


# ── SITE SETTINGS ─────────────────────────────────────────────────────────────
@staff_required
def site_settings(request):
    from .forms import SiteSettingsForm
    site = SiteSettings.get()
    if request.method == 'POST':
        form = SiteSettingsForm(request.POST, request.FILES, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, 'Site settings updated.')
            return redirect('dashboard:site_settings')
        else:
            messages.warning(request, 'Please correct the errors below.')
    else:
        form = SiteSettingsForm(instance=site)
    return render(request, 'dashboard/site_settings.html', {
        'active_nav': 'settings',
        'form': form,
        **_badge_counts(),
    })
