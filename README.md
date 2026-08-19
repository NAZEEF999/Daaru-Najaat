# Daaru Najat — Tradomedical Healing Home
## Django 5.2

> "...healing hands, divine touch!"

---

## Quick Start

```bash
# 1. Create virtual environment
python -m venv env
source env/bin/activate        # Mac/Linux
env\Scripts\activate           # Windows

# 2. Install all dependencies
pip install -r requirements.txt

# 3. Configure — copy the example and fill in real values
cp .env.example .env

# 4. Run migrations
python manage.py migrate

# 5. Create a staff account (you'll be prompted for a username/password —
#    nothing is printed or stored anywhere else)
python manage.py createsuperuser

# 6. Start
python manage.py runserver
```

- **Public site**: http://127.0.0.1:8000/
- **Patient portal**: http://127.0.0.1:8000/portal/login/ (optional — booking never requires an account)
- **Staff dashboard**: http://127.0.0.1:8000/dashboard/login/ — the normal interface for clinic staff
- **Django admin**: http://127.0.0.1:8000/admin/ — internal/emergency fallback only, not the staff UI

No default credentials are shipped with this project. Create your own staff account with
`createsuperuser` (or promote an existing user by setting `is_staff=True`) and use that
to log in at `/dashboard/login/`.

---

## Architecture

```
PUBLIC WEBSITE
  ├── Guest users — full booking flow, no account needed
  └── Optional patient accounts
          │
          ▼
      /portal/            ← patient's own appointment history, profile, PDF receipts


STAFF / ADMIN
      │
      ▼
  /dashboard/             ← the real staff interface, staff-only (server-side enforced)
      ├── Overview           — stats + real appointment calendar (yellow = upcoming)
      ├── Appointments        — list/detail, confirm/cancel/complete, conflict-checked
      ├── Patients
      ├── Healers / Staff
      ├── Services
      ├── Products
      ├── Orders
      ├── Messages / Inquiries
      ├── Notifications
      ├── Blog
      ├── Testimonials
      ├── Subscribers
      └── Site Settings       — phone, WhatsApp number, branding, SEO, etc.


  /admin/                 ← Django admin, internal/developer/emergency fallback only.
                             Normal day-to-day staff work happens in /dashboard/, not here.
```

---

## All Pages

| URL | Description |
|-----|-------------|
| `/` | Home |
| `/services/` | Healing services |
| `/products/` | Herbal products |
| `/healers/` | Healers listing |
| `/about/` | About + Google Maps |
| `/blog/` | Blog |
| `/contact/` | Contact + Google Maps |
| `/book/` | Book appointment (guest OR logged-in patient) |
| `/portal/login/` | Patient login |
| `/portal/register/` | Patient registration (optional) |
| `/portal/dashboard/` | Patient dashboard |
| `/portal/appointments/` | Patient's appointment history + PDF receipt |
| `/portal/profile/` | Edit patient profile |
| `/dashboard/login/` | **Staff login** |
| `/dashboard/` | **Staff dashboard** — overview, calendar, and every management section listed above |
| `/admin/` | Django admin — internal/emergency fallback, not the normal staff workflow |

---

## Features

### Booking
- **Guest booking** — no account needed, works immediately
- **Logged-in booking** — form pre-fills with patient details, and the appointment is
  linked to the patient's account via `Appointment.patient` (not just email matching)
- Backend availability check at booking time: rejects a request only if every active
  healer is already confirmed for that exact date+time — not just because one specific
  healer (which the patient never chose) happens to be busy
- A second, healer-specific conflict check runs again when staff confirm the appointment,
  backed by a database-level constraint so two simultaneous confirmations can never both succeed
- Pre-filled WhatsApp notification link generated for staff (opens WhatsApp with the
  appointment's operational details — this is **not** automatic sending; WhatsApp requires
  the staff member to actually send it)
- Email confirmation sent to patient (configure SMTP in `.env` for production; console
  backend is used automatically in development)
- Dashboard notification created for staff, with real unread-count badges

### Patient Portal (`/portal/`)
- Optional — patients can book without ever signing up
- Create account → track appointment history → download PDF receipts
- Edit profile (name, phone, address, date of birth)

### Staff Dashboard (`/dashboard/`)
- Staff-only, enforced server-side (not just hidden UI) — patients and anonymous
  visitors are redirected out
- Real appointment calendar: month view built from the actual `Appointment` table
  (not mock data), yellow-highlighted dates for upcoming pending/confirmed
  appointments, click a date to see that day's real bookings, links straight to the
  appointment detail page
- Manage appointments, patients, healers, services, products, orders, blog,
  testimonials, and subscribers without needing Django admin for normal work
- Site Settings page — change the clinic's phone number, WhatsApp number, branding,
  SEO fields, etc.; changes propagate to the public site immediately
- Medical notes are only ever visible here, to authenticated staff — never in
  WhatsApp messages, public pages, or patient-facing confirmations

### Email Notifications
Configure in `.env`:
```
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-app-password
```
The email backend switches automatically: console backend (prints to terminal) when
`DEBUG=True`, SMTP when `DEBUG=False`, unless `EMAIL_BACKEND` is set explicitly.

### Cloudinary Images
Set in `.env`:
```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```
Sign up free at cloudinary.com. Service/product/healer photos and blog cover images
can be uploaded directly from `/dashboard/`.

### PostgreSQL (Production)
Set in `.env`:
```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```
SQLite is used automatically for local development when `DATABASE_URL` is unset.

---

## Testing

```bash
python manage.py test
```

Runs the full automated test suite (staff auth, guest/registered booking, appointment
conflict handling, calendar behavior, notification/message read-state, SiteSettings
propagation, and more) against a fresh, disposable test database — it never touches
your real `db.sqlite3` or production data.

---

## Stack
- **Backend**: Django 5.2.5
- **Frontend**: Tailwind CSS v4 (CDN) for the public site; hand-styled dashboard
- **Images**: Cloudinary
- **PDF**: xhtml2pdf
- **Database**: SQLite (dev) → PostgreSQL via `DATABASE_URL` (prod)
- **Static files**: WhiteNoise (`static/` is source; `staticfiles/` is generated by
  `collectstatic` during deployment and isn't part of this repository)
- **Fonts**: Cormorant Garamond + DM Sans + Amiri
