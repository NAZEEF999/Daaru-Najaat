from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)

from .models import (
    SiteSettings, Service, Product, Healer,
    Appointment, BlogPost, Inquiry, Testimonial, Subscriber, Notification
)
from .forms import (
    AppointmentForm, InquiryForm, ProductOrderForm,
    SubscriberForm, TestimonialForm
)
from .utils import (
    create_notification, trigger_whatsapp_alert,
    build_appointment_wa_message, build_order_wa_message, build_inquiry_wa_message
)
from .email_service import send_appointment_confirmation

TRUST_INDICATORS = [
    ('Experienced Healers', 'Qualified & Trusted'),
    ('Traditional & Herbal Care', '100% Natural Remedies'),
    ('Personalized Attention', 'Care Just for You'),
    ('Confidential Service', 'Private & Secure'),
]

CONDITIONS = [
    'Spiritual Divination','Financial Problems','Barrenness','Business Promotion',
    'Long Lasting Marriage','Marriage Compatibility','Stomach Ulcer','Diabetes',
    'Low Sperm Count','Tuberculosis','Strokes','Typhoid Fever','Rheumatism',
    'Fibroid','Gonorrhea','Menstruation Malfunction','Piles','Asthma',
    'Man-power','Virginal Discharge','Hypertension','Malaria','Family Planning',
    'Toilet Infections','Anaemia','Menstruation Pain','Pelvic Inflammatory','Blood Disease',
]

VALUES = [
    ('Compassion','Every patient deserves empathy, dignity, and respect on their healing journey.','M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z'),
    ('Integrity','We uphold the highest standards of traditional medicine ethics and patient care.','M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z'),
    ('Wholeness','True healing addresses body, mind, and spirit in complete harmony.','M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064'),
]
HOURS = [
    ('Monday – Friday','8:00 AM – 6:00 PM'),
    ('Saturday','9:00 AM – 4:00 PM'),
    ('Sunday','By Appointment'),
]


def home(request):
    explore_links = [
        ('Our Services', reverse('api:services'), 'M12 2v20M2 12h20'),
        ('Book Appointment', reverse('api:book'), 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z'),
        ('Meet Our Healers', reverse('api:healers'), 'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75'),
        ('Herbal Products', reverse('api:products'), 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4'),
        ('Blog & Articles', reverse('api:blog'), 'M4 19.5A2.5 2.5 0 016.5 17H20M4 4.5A2.5 2.5 0 016.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15z'),
        ('Contact Us', reverse('api:contact'), 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z'),
    ]
    return render(request, 'home/index.html', {
        'featured_services': Service.objects.filter(active=True, is_featured=True)[:6],
        'featured_products': Product.objects.filter(active=True, is_featured=True)[:4],
        'featured_healers':  Healer.objects.filter(is_active=True, is_featured=True)[:4],
        'testimonials':      Testimonial.objects.filter(is_approved=True)[:6],
        'recent_posts':      BlogPost.objects.filter(is_published=True)[:3],
        'stats': {
            'healers':  Healer.objects.filter(is_active=True).count(),
            'services': Service.objects.filter(active=True).count(),
            'products': Product.objects.filter(active=True).count(),
        },
        'trust_indicators': TRUST_INDICATORS,
        'explore_links': explore_links,
        'conditions':        CONDITIONS,
    })


def services(request):
    category = request.GET.get('category', '')
    qs = Service.objects.filter(active=True)
    if category:
        qs = qs.filter(category=category)
    site = SiteSettings.get()
    return render(request, 'services/list.html', {
        'services': qs, 'active_category': category, 'categories': Service.CATEGORY_CHOICES,
        'page_title': f"Our Services | {site.site_name}",
        'page_description': f"Explore {site.site_name}'s traditional and herbal healthcare services.",
    })


def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, active=True)
    related = Service.objects.filter(active=True, category=service.category).exclude(pk=service.pk)[:3]
    return render(request, 'services/detail.html', {
        'service': service, 'related': related,
        'page_title': f"{service.title} | {SiteSettings.get().site_name}",
        'page_description': service.short_description[:160],
    })


def products(request):
    site = SiteSettings.get()
    return render(request, 'products/list.html', {
        'products': Product.objects.filter(active=True),
        'page_title': f"Herbal Products | {site.site_name}",
        'page_description': f"Browse traditional herbal remedies from {site.site_name}.",
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, active=True)
    if request.method == 'POST':
        form = ProductOrderForm(request.POST)
        if form.is_valid():
            from .models import ProductOrder
            order = ProductOrder.objects.create(
                product=product, product_name=product.title,
                quantity=form.cleaned_data['quantity'], price=product.price,
                customer_name=form.cleaned_data['customer_name'],
                customer_phone=form.cleaned_data['customer_phone'],
                customer_email=form.cleaned_data.get('customer_email', ''),
            )
            create_notification('product_order', f'New Order: {product.title}',
                                f'{order.customer_name} ordered {order.quantity}x {product.title}')
            wa_url = trigger_whatsapp_alert(build_order_wa_message(order))
            return render(request, 'products/order_success.html', {
                'order': order, 'wa_url': wa_url,
                'page_title': f"Order Received | {SiteSettings.get().site_name}",
            })
    else:
        form = ProductOrderForm()
    site = SiteSettings.get()
    return render(request, 'products/detail.html', {
        'product': product, 'form': form,
        'page_title': f"{product.title} | {site.site_name}",
        'page_description': product.short_description[:160],
    })


def book(request):
    initial = {}
    service_slug = request.GET.get('service', '')
    if service_slug:
        try:
            initial['service'] = Service.objects.get(slug=service_slug, active=True)
        except Service.DoesNotExist:
            pass

    # Pre-fill if logged in
    if request.user.is_authenticated:
        initial.setdefault('contact_name', request.user.get_full_name())
        initial.setdefault('contact_email', request.user.email)
        try:
            initial.setdefault('contact_phone', request.user.patient_profile.phone)
        except ObjectDoesNotExist:
            pass  # user has no PatientProfile yet — nothing to prefill, not an error

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            if request.user.is_authenticated:
                appointment.patient = getattr(request.user, 'patient_profile', None)
            appointment.save()
            create_notification('appointment', f'New Appointment: {appointment.contact_name}',
                                f'{appointment.contact_name} booked {appointment.service_name or "General Consultation"}')
            wa_url = trigger_whatsapp_alert(build_appointment_wa_message(appointment))
            # Send confirmation email (non-blocking)
            send_appointment_confirmation(appointment)
            messages.success(request, 'Your appointment has been booked. We will confirm shortly.')
            return render(request, 'booking/success.html', {
                'appointment': appointment, 'wa_url': wa_url,
                'page_title': f"Booking Received | {SiteSettings.get().site_name}",
            })
        else:
            messages.warning(request, 'Please correct the errors below and try again.')
    else:
        form = AppointmentForm(initial=initial)

    site = SiteSettings.get()
    return render(request, 'booking/book.html', {
        'form': form,
        'is_guest': not request.user.is_authenticated,
        'page_title': f"Book a Session | {site.site_name}",
        'page_description': f"Book a healing appointment with {site.site_name} — guest booking allowed, no account required.",
    })


def blog(request):
    qs = BlogPost.objects.filter(is_published=True)
    category = request.GET.get('category', '')
    if category:
        qs = qs.filter(category=category)
    paginator = Paginator(qs, 9)
    page = paginator.get_page(request.GET.get('page'))
    categories = BlogPost.objects.filter(is_published=True).values_list('category', flat=True).distinct()
    site = SiteSettings.get()
    return render(request, 'blog/list.html', {
        'page_obj': page, 'categories': categories, 'active_category': category,
        'page_title': f"Healing Blog | {site.site_name}",
        'page_description': f"Healing wisdom, guides and traditional health insights from {site.site_name}.",
    })


def blog_detail(request, slug):
    post    = get_object_or_404(BlogPost, slug=slug, is_published=True)
    related = BlogPost.objects.filter(is_published=True).exclude(pk=post.pk)[:3]
    return render(request, 'blog/detail.html', {
        'post': post, 'related': related,
        'page_title': f"{post.title} | {SiteSettings.get().site_name}",
        'page_description': post.excerpt[:160],
    })


def healers(request):
    site = SiteSettings.get()
    return render(request, 'healers/list.html', {
        'healers': Healer.objects.filter(is_active=True),
        'page_title': f"Our Healers | {site.site_name}",
        'page_description': f"Meet the experienced, trusted healers at {site.site_name}.",
    })


def healer_detail(request, pk):
    healer = get_object_or_404(Healer, pk=pk, is_active=True)
    site = SiteSettings.get()
    return render(request, 'healers/detail.html', {
        'healer': healer,
        'page_title': f"{healer.full_name} | {site.site_name}",
        'page_description': f"{healer.full_name} — {healer.specialty} at {site.site_name}.",
    })


def about(request):
    site = SiteSettings.get()
    return render(request, 'about/index.html', {
        'healers': Healer.objects.filter(is_active=True, is_featured=True)[:4],
        'testimonials': Testimonial.objects.filter(is_approved=True)[:3],
        'values': VALUES, 'hours': HOURS,
        'page_title': f"About Us | {site.site_name}",
        'page_description': site.about_description[:160],
    })


def contact(request):
    if request.method == 'POST':
        form = InquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save()
            create_notification('inquiry', f'New Inquiry: {inquiry.name}', inquiry.message[:100])
            wa_url = trigger_whatsapp_alert(build_inquiry_wa_message(inquiry))
            messages.success(request, 'Message sent. We will get back to you soon.')
            return render(request, 'contact/success.html', {
                'inquiry': inquiry, 'wa_url': wa_url,
                'page_title': f"Message Sent | {SiteSettings.get().site_name}",
            })
    else:
        form = InquiryForm()
    site = SiteSettings.get()
    return render(request, 'contact/index.html', {
        'form': form, 'hours': HOURS,
        'page_title': f"Contact Us | {site.site_name}",
        'page_description': f"Get in touch with {site.site_name} — phone, WhatsApp, email and location.",
    })


@require_POST
def subscribe(request):
    form = SubscriberForm(request.POST)
    if form.is_valid():
        sub, created = Subscriber.objects.get_or_create(email=form.cleaned_data['email'])
        if created:
            create_notification('subscriber', 'New Subscriber', sub.email)
        return JsonResponse({'ok': True, 'message': 'Subscribed! May healing find you.'})
    return JsonResponse({'ok': False, 'message': 'Invalid email address.'}, status=400)


def submit_testimonial(request):
    if request.method == 'POST':
        form = TestimonialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you! Your testimonial will appear after review.')
            return redirect('api:home')
    else:
        form = TestimonialForm()
    return render(request, 'testimonials/submit.html', {'form': form})


# ── ADMIN: APPOINTMENT CALENDAR (deprecated) ──────────────────────────────────
@staff_member_required
def admin_calendar(request):
    """
    Deprecated. The real appointment calendar now lives in the custom
    staff dashboard overview (/dashboard/), which is the single source of
    truth for appointment calendar data — this route now just redirects
    there instead of maintaining a second, separate calendar implementation.
    """
    return redirect('dashboard:overview')

# ── ADMIN: WHATSAPP REPLY TEMPLATES ───────────────────────────────────────────
@staff_member_required
def whatsapp_templates(request):
    """Pre-written WhatsApp reply templates for the admin to copy."""
    site = SiteSettings.get()
    templates = [
        {
            'title':    'Appointment Confirmed',
            'category': 'Appointments',
            'message':  f"Salaam! This is {site.site_name}. Your appointment has been CONFIRMED. We look forward to seeing you. May Allah grant you healing. ...healing hands, divine touch!",
        },
        {
            'title':    'Appointment Reminder',
            'category': 'Appointments',
            'message':  f"Salaam! A reminder from {site.site_name} about your upcoming appointment. Please arrive 10 minutes early. Call us on {site.contact_phone} for any changes. Jazakallahu khairan.",
        },
        {
            'title':    'Appointment Rescheduled',
            'category': 'Appointments',
            'message':  f"Salaam! We need to reschedule your appointment at {site.site_name}. Please call us on {site.contact_phone} or reply here to agree on a new time. We apologise for any inconvenience.",
        },
        {
            'title':    'Appointment Cancelled',
            'category': 'Appointments',
            'message':  f"Salaam! Your appointment at {site.site_name} has been cancelled. Please contact us on {site.contact_phone} to rebook at your convenience. We are sorry for any inconvenience.",
        },
        {
            'title':    'Order Received — Contact for Delivery',
            'category': 'Product Orders',
            'message':  f"Salaam! Thank you for your order from {site.site_name}. We have received it and will contact you shortly to arrange payment and delivery. Jazakallahu khairan.",
        },
        {
            'title':    'Order Ready for Pickup',
            'category': 'Product Orders',
            'message':  f"Salaam! Your herbal product order from {site.site_name} is READY. You can pick it up at {site.address}. Opening hours: Mon–Sat 8am–6pm. Please bring this message. ...healing hands, divine touch!",
        },
        {
            'title':    'General Inquiry Response',
            'category': 'Inquiries',
            'message':  f"Salaam! Thank you for contacting {site.site_name}. We have received your message and will respond within 24 hours. For urgent matters please call {site.contact_phone}. Jazakallahu khairan.",
        },
        {
            'title':    'Treatment Follow-Up',
            'category': 'Follow-Up',
            'message':  f"Salaam! This is {site.site_name} checking in. How are you feeling after your treatment? We hope you are experiencing healing and improvement. Do not hesitate to reach out if you need anything. WE CURE, ALLAH HEALS.",
        },
        {
            'title':    'Directions to the Clinic',
            'category': 'General',
            'message':  f"Salaam! {site.site_name} is located at: {site.address}. Nearest landmark: Iyana-ipaja area. Call {site.contact_phone} when you are close and we will guide you. ...healing hands, divine touch!",
        },
        {
            'title':    'Prayer & Spiritual Consultation Info',
            'category': 'General',
            'message':  f"Salaam! For spiritual consultation and prayer assistance at {site.site_name}, please book an appointment or visit us at {site.address}. Sessions are by appointment. Call {site.contact_phone} to schedule. WE CURE, ALLAH HEALS.",
        },
    ]
    return render(request, 'calendar/whatsapp_templates.html', {
        'templates': templates, 'site': site
    })


# ── ADMIN: APPOINTMENT RECEIPT PDF ────────────────────────────────────────────
@staff_member_required
def admin_appointment_pdf(request, pk):
    """Admin can print/download any appointment receipt."""
    appointment = get_object_or_404(Appointment, pk=pk)
    site = SiteSettings.get()
    html = render(request, 'pdf/appointment_receipt.html', {
        'appointment': appointment, 'site': site, 'now': timezone.now(),
    }).content
    try:
        from xhtml2pdf import pisa
        from io import BytesIO
        buf = BytesIO()
        pisa.CreatePDF(html.decode('utf-8'), dest=buf)
        buf.seek(0)
        response = HttpResponse(buf, content_type='application/pdf')
        response['Content-Disposition'] = f'filename="receipt_{pk}.pdf"'
        return response
    except Exception:
        logger.exception(f'Appointment receipt PDF generation failed for appointment {pk}')
        messages.error(request, 'We could not generate the PDF right now. Please try again.')
        return redirect('dashboard:appointment_detail', pk=pk)
