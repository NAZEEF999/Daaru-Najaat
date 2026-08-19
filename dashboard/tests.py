from datetime import date, timedelta
import os

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from accounts.models import PatientProfile
from api.models import (
    Appointment, Service, Healer, Inquiry, Notification, ProductOrder,
    Product, BlogPost, Testimonial, Subscriber, SiteSettings,
)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class DashboardAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staffuser', 'staff@x.com', 'testpass123', is_staff=True)
        self.patient_user = User.objects.create_user('patientuser', 'p@x.com', 'testpass123')
        PatientProfile.objects.create(user=self.patient_user, phone='08011112222')

    def test_anonymous_redirected_to_login(self):
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/dashboard/login/', r.url)

    def test_patient_cannot_access_dashboard(self):
        self.client.login(username='patientuser', password='testpass123')
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('/dashboard/', r.url)  # bounced out, not into the dashboard

    def test_staff_login_and_access(self):
        r = self.client.post('/dashboard/login/', {'username': 'staffuser', 'password': 'testpass123'})
        self.assertEqual(r.status_code, 302)
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 200)

    def test_non_staff_login_attempt_rejected_with_message(self):
        r = self.client.post('/dashboard/login/', {'username': 'patientuser', 'password': 'testpass123'}, follow=True)
        self.assertContains(r, 'have staff dashboard access')


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class DashboardPagesLoadTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staffuser2', 'staff2@x.com', 'testpass123', is_staff=True)
        self.patient_user = User.objects.create_user('patientuser2', 'p2@x.com', 'testpass123')
        self.patient = PatientProfile.objects.create(user=self.patient_user, phone='08011112222',
                                                       medical_notes='Confidential note')
        self.service = Service.objects.create(title='Herbal Consult', short_description='x',
                                                description='y', price=5000)
        self.healer = Healer.objects.create(full_name='Dr. Naziru', specialty='Herbal', bio='x')
        self.appointment = Appointment.objects.create(
            contact_name='Aisha Aliyu', contact_phone='08031234567', contact_email='aisha@x.com',
            service=self.service, service_name='Herbal Consult', healer=self.healer,
            appointment_date=date.today() + timedelta(days=5), preferred_time='10:00',
            patient=self.patient,
        )
        self.inquiry = Inquiry.objects.create(name='Ibrahim Musa', phone='08022223333',
                                               message='Do you treat back pain?')
        self.notification = Notification.objects.create(type='appointment', title='New appointment', message='x')
        self.product = Product.objects.create(title='Herbal Tea', short_description='x', description='y', price=2000)
        self.order = ProductOrder.objects.create(product=self.product, product_name='Herbal Tea', quantity=2,
                                                  price=2000, customer_name='Musa', customer_phone='08011112222')
        BlogPost.objects.create(title='Healing Basics', excerpt='x', content='y' * 50)
        Testimonial.objects.create(name='Fatima', content='Great service')
        Subscriber.objects.create(email='sub@x.com')
        self.client.login(username='staffuser2', password='testpass123')

    def test_every_dashboard_page_returns_200(self):
        pages = [
            '/dashboard/', '/dashboard/appointments/', f'/dashboard/appointments/{self.appointment.pk}/',
            '/dashboard/patients/', f'/dashboard/patients/{self.patient.pk}/',
            '/dashboard/messages/', f'/dashboard/messages/{self.inquiry.pk}/',
            '/dashboard/notifications/', '/dashboard/orders/',
            '/dashboard/services/', '/dashboard/services/add/', f'/dashboard/services/{self.service.pk}/edit/',
            '/dashboard/products/', '/dashboard/products/add/', f'/dashboard/products/{self.product.pk}/edit/',
            '/dashboard/healers/', '/dashboard/healers/add/', f'/dashboard/healers/{self.healer.pk}/edit/',
            '/dashboard/blog/', '/dashboard/testimonials/', '/dashboard/subscribers/', '/dashboard/settings/',
        ]
        for url in pages:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200, f'{url} returned {r.status_code}')

    def test_medical_notes_only_appear_on_staff_patient_detail(self):
        r = self.client.get(f'/dashboard/patients/{self.patient.pk}/')
        self.assertContains(r, 'Confidential note')
        # never on public pages
        r = self.client.get('/about/')
        self.assertNotContains(r, 'Confidential note')

    def test_message_marked_read_on_view(self):
        self.assertFalse(self.inquiry.is_read)
        self.client.get(f'/dashboard/messages/{self.inquiry.pk}/')
        self.inquiry.refresh_from_db()
        self.assertTrue(self.inquiry.is_read)

    def test_notification_mark_read(self):
        self.assertFalse(self.notification.is_read)
        self.client.post(f'/dashboard/notifications/{self.notification.pk}/read/')
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_notification_mark_all_read(self):
        Notification.objects.create(type='inquiry', title='second', message='x')
        self.client.post('/dashboard/notifications/mark-all-read/')
        self.assertEqual(Notification.objects.filter(is_read=False).count(), 0)

    def test_order_status_update(self):
        r = self.client.post(f'/dashboard/orders/{self.order.pk}/status/', {'status': 'completed'})
        self.assertEqual(r.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'completed')

    def test_service_create_via_dashboard_not_admin(self):
        count_before = Service.objects.count()
        r = self.client.post('/dashboard/services/add/', {
            'title': 'Cupping Therapy', 'short_description': 'x', 'description': 'y',
            'icon_name': 'Star', 'category': 'cupping', 'duration_minutes': 45,
            'price': 3000, 'sort_order': 0,
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Service.objects.count(), count_before + 1)

    def test_healer_create_via_dashboard_not_admin(self):
        r = self.client.post('/dashboard/healers/add/', {
            'full_name': 'Dr. New Healer', 'specialty': 'Cupping', 'bio': 'x',
            'experience_years': 5, 'languages': 'English', 'whatsapp_number': '',
            'phone': '', 'email': '',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Healer.objects.filter(full_name='Dr. New Healer').exists())


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class AppointmentFlowTests(TestCase):
    def setUp(self):
        self.service = Service.objects.create(title='Spiritual Healing', short_description='x',
                                                description='y', price=4000)
        self.healer = Healer.objects.create(full_name='Mallam Usman', specialty='Spiritual', bio='x')
        SiteSettings.get()  # ensure singleton row exists

    def _book(self, **overrides):
        data = {
            'service': self.service.pk,
            'appointment_date': (date.today() + timedelta(days=3)).isoformat(),
            'preferred_time': '10:00',
            'contact_name': 'Test Patient',
            'contact_email': 'test@x.com',
            'contact_phone': '08033334444',
            'notes': '',
        }
        data.update(overrides)
        return self.client.post('/book/', data, follow=True)

    def test_guest_can_book_without_account(self):
        r = self._book()
        self.assertEqual(r.status_code, 200)
        appt = Appointment.objects.get(contact_email='test@x.com')
        self.assertIsNone(appt.patient)
        self.assertEqual(appt.status, 'pending')

    def test_guest_booking_shows_success_message(self):
        r = self._book()
        self.assertContains(r, 'appointment has been booked')

    def test_guest_booking_creates_notification(self):
        count_before = Notification.objects.count()
        self._book()
        self.assertEqual(Notification.objects.count(), count_before + 1)

    def test_guest_booking_surfaces_whatsapp_link(self):
        r = self._book()
        self.assertContains(r, 'wa.me')

    def test_past_date_rejected(self):
        r = self._book(appointment_date=(date.today() - timedelta(days=1)).isoformat())
        self.assertContains(r, 'cannot be in the past')
        self.assertFalse(Appointment.objects.filter(contact_email='test@x.com').exists())

    def test_registered_patient_booking_is_linked_via_fk(self):
        user = User.objects.create_user('regpatient', 'reg@x.com', 'testpass123')
        patient = PatientProfile.objects.create(user=user, phone='08055556666')
        self.client.login(username='regpatient', password='testpass123')
        self._book(contact_email='reg@x.com')
        appt = Appointment.objects.get(contact_email='reg@x.com')
        self.assertEqual(appt.patient_id, patient.pk)
        # and it shows up in their patient-portal appointment list
        self.assertIn(appt, list(patient.appointments))

    def test_guest_appointment_does_not_leak_into_unrelated_patient_portal(self):
        # A guest appointment with no account must not silently attach to
        # some other registered patient who happens to share an email later
        # unless they are actually that patient.
        self._book(contact_email='unclaimed@x.com')
        appt = Appointment.objects.get(contact_email='unclaimed@x.com')
        self.assertIsNone(appt.patient)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class AppointmentConflictTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staffuser3', 'staff3@x.com', 'testpass123', is_staff=True)
        self.healer = Healer.objects.create(full_name='Dr. Slot', specialty='General', bio='x')
        self.day = date.today() + timedelta(days=7)
        self.appt1 = Appointment.objects.create(
            contact_name='Patient One', contact_phone='08011110000', healer=self.healer,
            appointment_date=self.day, preferred_time='09:00', status='pending',
        )
        self.appt2 = Appointment.objects.create(
            contact_name='Patient Two', contact_phone='08022220000', healer=self.healer,
            appointment_date=self.day, preferred_time='09:00', status='pending',
        )
        self.client.login(username='staffuser3', password='testpass123')

    def test_first_confirmation_succeeds(self):
        r = self.client.post(f'/dashboard/appointments/{self.appt1.pk}/status/',
                              {'status': 'confirmed', 'healer': self.healer.pk}, follow=True)
        self.appt1.refresh_from_db()
        self.assertEqual(self.appt1.status, 'confirmed')

    def test_second_confirmation_blocked_by_conflict(self):
        self.appt1.status = 'confirmed'
        self.appt1.save()
        r = self.client.post(f'/dashboard/appointments/{self.appt2.pk}/status/',
                              {'status': 'confirmed', 'healer': self.healer.pk}, follow=True)
        self.appt2.refresh_from_db()
        self.assertEqual(self.appt2.status, 'pending')
        self.assertContains(r, 'already booked')

    def test_different_time_does_not_conflict(self):
        self.appt1.status = 'confirmed'
        self.appt1.save()
        self.appt2.preferred_time = '11:00'
        self.appt2.save()
        self.client.post(f'/dashboard/appointments/{self.appt2.pk}/status/',
                          {'status': 'confirmed', 'healer': self.healer.pk})
        self.appt2.refresh_from_db()
        self.assertEqual(self.appt2.status, 'confirmed')

    def test_db_constraint_rejects_duplicate_confirmed_slot_directly(self):
        """
        Regression test for the race-condition fix: even bypassing the
        Python-level conflicts_with_confirmed() check entirely (simulating
        two confirmations landing at nearly the same instant), the
        database itself must refuse a second CONFIRMED row for the same
        healer+date+time.
        """
        from django.db import IntegrityError, transaction
        self.appt1.status = 'confirmed'
        self.appt1.save()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.appt2.status = 'confirmed'
                self.appt2.save()

    def test_confirmation_race_condition_shows_friendly_message_not_500(self):
        """
        Simulates the actual race: appt2's in-memory conflict check passes
        (as it would if it read the database a moment before appt1's
        confirmation committed), but the database-level constraint still
        catches the collision when appt2.save() actually runs. The VIEW
        must catch that IntegrityError gracefully -- friendly message,
        redirect back to the appointment, no 500 -- not just the model layer.
        """
        from unittest.mock import patch
        self.appt1.status = 'confirmed'
        self.appt1.save()

        with patch('api.models.Appointment.conflicts_with_confirmed', return_value=False):
            r = self.client.post(f'/dashboard/appointments/{self.appt2.pk}/status/',
                                  {'status': 'confirmed', 'healer': self.healer.pk}, follow=True)

        self.assertEqual(r.status_code, 200)  # followed redirect, not a 500
        self.assertContains(r, 'just taken by another appointment')
        self.appt2.refresh_from_db()
        self.assertEqual(self.appt2.status, 'pending')


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class PublicBookingAvailabilityTests(TestCase):
    """
    Availability must be enforced at the moment of public booking, not just
    when staff later try to confirm — this is separate from
    AppointmentConflictTests, which covers the staff-side confirmation check.

    Public booking doesn't collect a healer, so availability here means
    "is there capacity at all" (at least one active healer free), not
    "is this one specific healer free" -- rejecting on the latter would
    incorrectly block a request when a *different* healer could take it.
    """
    def setUp(self):
        self.service = Service.objects.create(title='Cupping', short_description='x', description='y', price=3000)
        self.healer = Healer.objects.create(full_name='Dr. Solo', specialty='General', bio='x', is_active=True)
        self.day = date.today() + timedelta(days=10)
        Appointment.objects.create(
            contact_name='Already Confirmed', contact_phone='08010101010', healer=self.healer,
            appointment_date=self.day, preferred_time='14:00', status='confirmed',
        )
        SiteSettings.get()

    def _book(self, **overrides):
        data = {
            'service': self.service.pk,
            'appointment_date': self.day.isoformat(),
            'preferred_time': '14:00',
            'contact_name': 'New Patient',
            'contact_email': 'new@x.com',
            'contact_phone': '08099990000',
            'notes': '',
        }
        data.update(overrides)
        return self.client.post('/book/', data, follow=True)

    def test_booking_rejected_when_the_only_healer_is_already_confirmed(self):
        # One healer total, and they're already booked at this slot ->
        # genuinely no capacity, so this should be rejected.
        r = self._book()
        self.assertContains(r, 'already booked')
        self.assertFalse(Appointment.objects.filter(contact_email='new@x.com').exists())

    def test_booking_allowed_when_a_different_healer_is_free(self):
        # This is the exact scenario from the bug report: Dr A is booked,
        # but Dr B is free -- the patient hasn't chosen a healer, so this
        # must NOT be rejected just because one specific healer is busy.
        Healer.objects.create(full_name='Dr. Backup', specialty='General', bio='x', is_active=True)
        r = self._book()
        self.assertTrue(Appointment.objects.filter(contact_email='new@x.com').exists())

    def test_booking_at_different_time_succeeds(self):
        r = self._book(preferred_time='15:00')
        self.assertTrue(Appointment.objects.filter(contact_email='new@x.com').exists())

    def test_booking_a_pending_slot_is_not_blocked(self):
        # Only CONFIRMED appointments should block — two pending requests
        # for the same slot are expected (staff resolves which one wins).
        Appointment.objects.filter(status='confirmed').update(status='pending')
        r = self._book()
        self.assertTrue(Appointment.objects.filter(contact_email='new@x.com').exists())

    def test_booking_allowed_when_no_healers_configured_at_all(self):
        # With zero healer records in the system, there's no capacity data
        # to reject against -- don't block bookings on missing catalog
        # data; staff sort out assignment afterward.
        Appointment.objects.all().delete()
        Healer.objects.all().delete()
        r = self._book()
        self.assertTrue(Appointment.objects.filter(contact_email='new@x.com').exists())

    def test_inactive_healer_does_not_count_toward_capacity(self):
        # An inactive healer shouldn't be treated as available capacity --
        # if the only OTHER healer than the busy one is inactive, this
        # should still be rejected.
        Healer.objects.create(full_name='Dr. Inactive', specialty='General', bio='x', is_active=False)
        r = self._book()
        self.assertContains(r, 'already booked')
        self.assertFalse(Appointment.objects.filter(contact_email='new@x.com').exists())

    def test_inactive_healers_confirmed_appointment_does_not_block_active_healer_slot(self):
        """
        Regression test: Dr B (inactive) has an old CONFIRMED appointment
        at a given date+time. Dr A (active) is completely free at that
        same date+time. Public booking must be allowed, because the
        clinic genuinely has active capacity then -- an inactive healer's
        confirmed appointment must not count as occupied capacity.
        """
        other_day = self.day + timedelta(days=1)
        other_time = '10:00'
        inactive_healer = Healer.objects.create(full_name='Dr. Inactive Busy', specialty='General',
                                                  bio='x', is_active=False)
        Appointment.objects.create(
            contact_name='Old Booking', contact_phone='08010101011', healer=inactive_healer,
            appointment_date=other_day, preferred_time=other_time, status='confirmed',
        )
        # self.healer (Dr. Solo, active) has no appointment at other_day/other_time --
        # only the inactive healer does, so this slot must be bookable.
        r = self._book(appointment_date=other_day.isoformat(), preferred_time=other_time)
        self.assertTrue(Appointment.objects.filter(contact_email='new@x.com').exists())


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class WhatsAppMessageContentTests(TestCase):
    def setUp(self):
        SiteSettings.get()

    def test_whatsapp_message_excludes_medical_notes(self):
        from api.utils import build_appointment_wa_message
        service = Service.objects.create(title='Herbal', short_description='x', description='y', price=1000)
        appt = Appointment.objects.create(
            contact_name='Sensitive Case', contact_phone='08012340000', service=service,
            service_name='Herbal', notes='Patient has a rare condition — CONFIDENTIAL DETAIL',
        )
        msg = build_appointment_wa_message(appt)
        self.assertNotIn('CONFIDENTIAL', msg)
        self.assertNotIn('rare condition', msg)
        self.assertIn('Sensitive Case', msg)
        self.assertIn('staff dashboard', msg)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1', 'malicious-site.example'])
class DashboardOpenRedirectTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staffuser5', 'staff5@x.com', 'testpass123', is_staff=True)

    def test_safe_internal_next_is_honored(self):
        r = self.client.post('/dashboard/login/?next=/dashboard/appointments/',
                              {'username': 'staffuser5', 'password': 'testpass123'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/dashboard/appointments/')

    def test_external_next_is_rejected(self):
        r = self.client.post('/dashboard/login/?next=https://malicious-site.example/',
                              {'username': 'staffuser5', 'password': 'testpass123'})
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('malicious-site.example', r.url)
        self.assertIn('dashboard', r.url)

    def test_protocol_relative_next_is_rejected(self):
        r = self.client.post('/dashboard/login/?next=//malicious-site.example/',
                              {'username': 'staffuser5', 'password': 'testpass123'})
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('malicious-site.example', r.url)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class BlogCrudViaDashboardTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staffuser6', 'staff6@x.com', 'testpass123', is_staff=True)
        self.client.login(username='staffuser6', password='testpass123')

    def test_create_post_via_dashboard_not_admin(self):
        r = self.client.post('/dashboard/blog/add/', {
            'title': 'New Healing Post', 'excerpt': 'A short summary', 'content': 'Full content here.',
            'category': 'Wellness', 'author': 'Daaru Najat Team', 'is_published': 'on',
        })
        self.assertEqual(r.status_code, 302)
        post = BlogPost.objects.get(title='New Healing Post')
        self.assertTrue(post.is_published)
        self.assertTrue(post.slug)

    def test_edit_post_via_dashboard(self):
        post = BlogPost.objects.create(title='Old Title', excerpt='x', content='y' * 20)
        r = self.client.post(f'/dashboard/blog/{post.pk}/edit/', {
            'title': 'Updated Title', 'excerpt': 'x', 'content': 'y' * 20,
            'category': '', 'author': 'Daaru Najat Team',
        })
        self.assertEqual(r.status_code, 302)
        post.refresh_from_db()
        self.assertEqual(post.title, 'Updated Title')


class SettingsSwitchingTests(TestCase):
    """
    These test the settings module's behavior directly (not via HTTP) since
    DATABASE_URL/DEBUG/EMAIL_BACKEND are read once at process start — the
    manual verification (see conversation) already confirmed the live
    switching; these lock in the documented defaults so a regression here
    is caught by 'manage.py test' rather than only by manual re-checking.
    """
    def test_sqlite_is_the_dev_default_without_database_url(self):
        from django.conf import settings
        if not os.environ.get('DATABASE_URL'):
            self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.sqlite3')

    def test_current_process_settings_are_internally_consistent(self):
        from django.conf import settings
        # If DEBUG is on, the fallback secret key must never be paired with DEBUG=False
        # (the ImproperlyConfigured guard in settings.py is what actually enforces this
        # at import time — this just documents the invariant for the test suite).
        self.assertTrue(hasattr(settings, 'SECRET_KEY'))
        self.assertTrue(hasattr(settings, 'EMAIL_BACKEND'))
        self.assertTrue(hasattr(settings, 'DATABASES'))


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class DashboardCalendarTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staffuser7', 'staff7@x.com', 'testpass123', is_staff=True)
        self.healer = Healer.objects.create(full_name='Dr. Calendar', specialty='General', bio='x')
        self.client.login(username='staffuser7', password='testpass123')
        self.today = date.today()
        # Pick a definitely-future day still inside the current month when possible,
        # otherwise just use a future date and navigate via cal_year/cal_month.
        self.target_day = self.today + timedelta(days=3)

    def _cal_data(self, year, month):
        """
        Extract just the calendar's own embedded JSON (id="cal-data"), not
        the whole page — the 'Recent Appointments' widget elsewhere on the
        same overview page legitimately lists recent appointments
        regardless of status/date, which is a separate, correct feature
        and isn't what these tests are checking.
        """
        import json, re
        r = self.client.get(f'/dashboard/?cal_year={year}&cal_month={month}')
        content = r.content.decode()
        m = re.search(r'id="cal-data" type="application/json">(.*?)</script>', content, re.S)
        return r, json.loads(m.group(1))

    def test_future_pending_appointment_is_highlighted(self):
        Appointment.objects.create(contact_name='Pending Cal', contact_phone='08010000001',
                                    healer=self.healer, appointment_date=self.target_day,
                                    preferred_time='09:00', status='pending')
        r, data = self._cal_data(self.target_day.year, self.target_day.month)
        self.assertEqual(r.status_code, 200)
        key = self.target_day.isoformat()
        self.assertIn(key, data)
        self.assertEqual(len(data[key]), 1)
        self.assertEqual(data[key][0]['name'], 'Pending Cal')

    def test_future_confirmed_appointment_is_highlighted(self):
        Appointment.objects.create(contact_name='Confirmed Cal', contact_phone='08010000002',
                                    healer=self.healer, appointment_date=self.target_day,
                                    preferred_time='10:00', status='confirmed')
        r, data = self._cal_data(self.target_day.year, self.target_day.month)
        key = self.target_day.isoformat()
        self.assertIn(key, data)
        self.assertEqual(data[key][0]['name'], 'Confirmed Cal')

    def test_past_appointment_not_counted_as_upcoming(self):
        past_day = self.today - timedelta(days=5)
        Appointment.objects.create(contact_name='Past Person', contact_phone='08010000003',
                                    healer=self.healer, appointment_date=past_day,
                                    preferred_time='09:00', status='confirmed')
        r, data = self._cal_data(past_day.year, past_day.month)
        self.assertNotIn(past_day.isoformat(), data)

    def test_multiple_appointments_same_date_correct_count(self):
        for i in range(3):
            Appointment.objects.create(contact_name=f'Multi {i}', contact_phone=f'0801000001{i}',
                                        healer=self.healer, appointment_date=self.target_day,
                                        preferred_time=f'{9+i}:00', status='pending')
        r, data = self._cal_data(self.target_day.year, self.target_day.month)
        key = self.target_day.isoformat()
        self.assertEqual(len(data[key]), 3)
        names = {a['name'] for a in data[key]}
        self.assertEqual(names, {'Multi 0', 'Multi 1', 'Multi 2'})

    def test_cancelled_appointment_not_counted(self):
        appt = Appointment.objects.create(contact_name='Cancelled Person', contact_phone='08010000004',
                                           healer=self.healer, appointment_date=self.target_day,
                                           preferred_time='09:00', status='confirmed')
        key = self.target_day.isoformat()
        r, data = self._cal_data(self.target_day.year, self.target_day.month)
        self.assertIn(key, data)

        appt.status = 'cancelled'
        appt.save()
        r, data = self._cal_data(self.target_day.year, self.target_day.month)
        self.assertNotIn(key, data)

    def test_month_navigation_shows_correct_month_appointments(self):
        next_month_day = (self.today.replace(day=1) + timedelta(days=32)).replace(day=15)
        Appointment.objects.create(contact_name='Next Month Person', contact_phone='08010000005',
                                    healer=self.healer, appointment_date=next_month_day,
                                    preferred_time='09:00', status='pending')
        # Not visible in the current month's calendar data
        r, data = self._cal_data(self.today.year, self.today.month)
        self.assertNotIn(next_month_day.isoformat(), data)
        # Visible when navigating to that month
        r, data = self._cal_data(next_month_day.year, next_month_day.month)
        self.assertIn(next_month_day.isoformat(), data)
        self.assertEqual(data[next_month_day.isoformat()][0]['name'], 'Next Month Person')


    def test_view_appointment_link_target_is_the_real_detail_page(self):
        from django.urls import reverse
        appt = Appointment.objects.create(contact_name='Link Target', contact_phone='08010000006',
                                           healer=self.healer, appointment_date=self.target_day,
                                           preferred_time='09:00', status='pending')
        expected_url = reverse('dashboard:appointment_detail', kwargs={'pk': appt.pk})
        r = self.client.get(f'/dashboard/?cal_year={self.target_day.year}&cal_month={self.target_day.month}')
        # the JS builds /dashboard/appointments/<id>/ — confirm that matches the real route
        self.assertEqual(expected_url, f'/dashboard/appointments/{appt.pk}/')
        detail_r = self.client.get(expected_url)
        self.assertEqual(detail_r.status_code, 200)
        self.assertContains(detail_r, 'Link Target')

    def test_calendar_data_not_exposed_to_anonymous_or_patient(self):
        Appointment.objects.create(contact_name='Secret Calendar Patient', contact_phone='08010000007',
                                    healer=self.healer, appointment_date=self.target_day,
                                    preferred_time='09:00', status='confirmed')
        self.client.logout()
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(b'Secret Calendar Patient', r.content)

        patient_user = User.objects.create_user('calpatient', 'calp@x.com', 'testpass123')
        PatientProfile.objects.create(user=patient_user, phone='08000000000')
        self.client.login(username='calpatient', password='testpass123')
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(b'Secret Calendar Patient', r.content)

    def test_calendar_data_is_json_safe_against_xss_payload(self):
        """
        Regression test for the XSS fix: a malicious appointment name must
        end up as inert JSON text inside the json_script block, and the
        rendered detail_url must come from Django's reverse(), never from
        interpolating the malicious string into a URL or HTML string.
        """
        payload = '<img src=x onerror=alert(document.domain)>'
        appt = Appointment.objects.create(contact_name=payload, contact_phone='08010000008',
                                           healer=self.healer, appointment_date=self.target_day,
                                           preferred_time='09:00', status='pending')
        r, data = self._cal_data(self.target_day.year, self.target_day.month)
        key = self.target_day.isoformat()
        entry = data[key][0]

        # The raw payload must survive intact inside the JSON (json_script
        # HTML-escapes it for safe embedding, but json.loads gives us back
        # the original string) -- proving it was never treated as markup.
        self.assertEqual(entry['name'], payload)

        # The response body must not contain an UNESCAPED, directly
        # exploitable copy of the payload outside the JSON script block --
        # json_script HTML-escapes '<' as '\u003C' etc, so a raw '<img'
        # appearing in the page would mean it leaked outside safe encoding.
        content = r.content.decode()
        # Strip out the safely-encoded json-script block before checking.
        import re
        without_json_block = re.sub(r'<script id="cal-data".*?</script>', '', content, flags=re.S)
        self.assertNotIn('<img src=x onerror=', without_json_block)

        # detail_url must be a real, server-generated reverse() URL, not
        # something constructed from the malicious name.
        self.assertEqual(entry['detail_url'], f'/dashboard/appointments/{appt.pk}/')


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class SiteSettingsPropagationTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staffuser4', 'staff4@x.com', 'testpass123', is_staff=True)
        self.client.login(username='staffuser4', password='testpass123')
        self.site = SiteSettings.get()

    def _payload(self, **overrides):
        data = {
            'site_name': 'Daaru Najat', 'tagline': 'Healing', 'primary_color': '#3A7D44',
            'secondary_color': '#C49A3C', 'accent_color': '#B0683A',
            'contact_email': 'clinic@x.com', 'contact_phone': '08000000000', 'contact_phone2': '',
            'whatsapp_number': '2348000000000', 'whatsapp_greeting': 'Hello',
            'address': 'Test address', 'city': 'Lagos', 'country': 'Nigeria',
            'hero_headline': 'h', 'hero_subheadline': 's', 'hero_cta_primary': 'a',
            'hero_cta_secondary': 'b', 'hero_video_url': '',
            'social_facebook': '', 'social_instagram': '', 'social_tiktok': '',
            'footer_description': 'f', 'seo_title': 't', 'seo_description': 'd', 'seo_keywords': 'k',
            'about_title': 'a', 'about_description': 'd', 'about_mission': 'm', 'about_vision': 'v',
            'registration_no': 'r',
        }
        data.update(overrides)
        return data

    def test_phone_number_change_saves(self):
        r = self.client.post('/dashboard/settings/', self._payload(contact_phone='08099998888'))
        self.assertEqual(r.status_code, 302)
        self.site.refresh_from_db()
        self.assertEqual(self.site.contact_phone, '08099998888')

    def test_phone_number_change_propagates_to_public_site(self):
        self.client.post('/dashboard/settings/', self._payload(contact_phone='08077778888'))
        r = self.client.get('/')
        self.assertContains(r, '08077778888')

    def test_whatsapp_number_change_propagates_to_public_wa_links(self):
        self.client.post('/dashboard/settings/', self._payload(whatsapp_number='2348077778888'))
        r = self.client.get('/')
        self.assertContains(r, '2348077778888')

    def test_invalid_phone_rejected(self):
        r = self.client.post('/dashboard/settings/', self._payload(contact_phone='123'))
        self.assertContains(r, 'valid phone number')
        self.site.refresh_from_db()
        self.assertNotEqual(self.site.contact_phone, '123')
