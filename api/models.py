from django.db import models
from django.utils.text import slugify
from cloudinary.models import CloudinaryField


# ── SITE SETTINGS (one row — the whole site config) ──────────────────────────
class SiteSettings(models.Model):
    site_name          = models.CharField(max_length=100, default='Daaru Najat')
    tagline            = models.CharField(max_length=200, default='...healing hands, divine touch!')
    logo               = CloudinaryField('logo', folder='daaru/branding', blank=True, null=True)
    favicon            = CloudinaryField('favicon', folder='daaru/branding', blank=True, null=True)
    primary_color      = models.CharField(max_length=7, default='#3A7D44')
    secondary_color    = models.CharField(max_length=7, default='#C49A3C')
    accent_color       = models.CharField(max_length=7, default='#B0683A')
    contact_email      = models.EmailField(default='abiodunnajaat@gmail.com')
    contact_phone      = models.CharField(max_length=20, default='08029001826')
    contact_phone2     = models.CharField(max_length=20, blank=True)
    whatsapp_number    = models.CharField(max_length=20, default='2348062952711',
                                          help_text='Digits only e.g. 2348062952711')
    whatsapp_greeting  = models.TextField(default='Salaam! I am interested in the healing services at Daaru Najat.')
    address            = models.TextField(default='11, Animasahun Close, Alaguntan, Iyana-ipaja, Lagos')
    city               = models.CharField(max_length=100, default='Lagos')
    country            = models.CharField(max_length=100, default='Nigeria')
    hero_headline      = models.CharField(max_length=200, default='Healing Rooted in Tradition')
    hero_subheadline   = models.TextField(default='Experience the sacred art of tradomedical healing.')
    hero_cta_primary   = models.CharField(max_length=100, default='Explore Our Services')
    hero_cta_secondary = models.CharField(max_length=100, default='Book a Session')
    hero_video_url     = models.URLField(blank=True)
    social_facebook    = models.CharField(max_length=200, blank=True, default='Daaru Najat Tradomedicals')
    social_instagram   = models.CharField(max_length=200, blank=True)
    social_tiktok      = models.CharField(max_length=200, blank=True)
    footer_description = models.TextField(default='Daaru Najat is a sacred traditional medical healing home.')
    seo_title          = models.CharField(max_length=200, default='Daaru Najat | Tradomedical Healing Home')
    seo_description    = models.TextField(default='Experience the sacred power of traditional healing in Lagos.')
    seo_keywords       = models.TextField(default='traditional healing, herbal medicine, Lagos')
    about_title        = models.CharField(max_length=200, default='About Daaru Najat')
    about_description  = models.TextField(default='A sacred tradomedical healing home serving Lagos and beyond.')
    about_mission      = models.TextField(default='To restore health and harmony through traditional medicine.')
    about_vision       = models.TextField(default='A world where ancient healing wisdom brings complete wellness.')
    registration_no    = models.CharField(max_length=50, default='RC-2705184', blank=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        # Enforce singleton — only one settings row ever
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ── SERVICE ───────────────────────────────────────────────────────────────────
class Service(models.Model):
    CATEGORY_CHOICES = [
        ('herbal_medicine',   'Herbal Medicine'),
        ('spiritual_healing', 'Spiritual Healing'),
        ('cupping',           'Cupping Therapy'),
        ('massage_therapy',   'Massage Therapy'),
        ('dietary_healing',   'Dietary Healing'),
        ('other',             'Other'),
    ]

    title             = models.CharField(max_length=200)
    slug              = models.SlugField(unique=True, blank=True)
    short_description = models.CharField(max_length=300)
    description       = models.TextField()
    image             = CloudinaryField('image', folder='daaru/services', blank=True, null=True)
    icon_name         = models.CharField(max_length=50, default='Leaf',
                                         help_text='Lucide icon name e.g. Leaf, Heart, Star')
    category          = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    duration_minutes  = models.PositiveIntegerField(default=60)
    price             = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_featured       = models.BooleanField(default=False)
    active            = models.BooleanField(default=True)
    sort_order        = models.PositiveIntegerField(default=0)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


# ── PRODUCT ───────────────────────────────────────────────────────────────────
class Product(models.Model):
    title             = models.CharField(max_length=200)
    slug              = models.SlugField(unique=True, blank=True)
    short_description = models.CharField(max_length=300)
    description       = models.TextField()
    image             = CloudinaryField('image', folder='daaru/products', blank=True, null=True)
    category          = models.CharField(max_length=100, default='Herbal Medicine')
    price             = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_featured       = models.BooleanField(default=False)
    active            = models.BooleanField(default=True)
    sort_order        = models.PositiveIntegerField(default=0)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


# ── PRODUCT ORDER ─────────────────────────────────────────────────────────────
class ProductOrder(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('contacted', 'Contacted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    product        = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='orders')
    product_name   = models.CharField(max_length=200)   # snapshot in case product deleted
    quantity       = models.PositiveIntegerField(default=1)
    price          = models.DecimalField(max_digits=10, decimal_places=2)
    customer_name  = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order — {self.product_name} by {self.customer_name}'

    @property
    def total(self):
        return self.quantity * self.price


# ── HEALER ────────────────────────────────────────────────────────────────────
class Healer(models.Model):
    full_name        = models.CharField(max_length=200)
    photo            = CloudinaryField('photo', folder='daaru/healers', blank=True, null=True)
    specialty        = models.CharField(max_length=200)
    bio              = models.TextField()
    experience_years = models.PositiveIntegerField(default=0)
    languages        = models.CharField(max_length=200, default='Yoruba, English',
                                        help_text='Comma-separated e.g. Yoruba, English, Arabic')
    whatsapp_number  = models.CharField(max_length=20, blank=True,
                                        help_text='Digits only e.g. 2348012345678')
    phone            = models.CharField(max_length=20, blank=True)
    email            = models.EmailField(blank=True)
    is_featured      = models.BooleanField(default=False)
    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', 'full_name']

    def __str__(self):
        return self.full_name

    @property
    def language_list(self):
        return [l.strip() for l in self.languages.split(',') if l.strip()]


# ── APPOINTMENT ───────────────────────────────────────────────────────────────
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    TIME_CHOICES = [(f'{h:02d}:{m:02d}', f'{h:02d}:{m:02d}')
                    for h in range(8, 19) for m in (0, 30)]

    # Nullable so guest bookings (no account) keep working unchanged.
    # Registered patients get an explicit link instead of relying on
    # contact_email == user.email, which breaks if either changes.
    patient           = models.ForeignKey('accounts.PatientProfile', on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name='linked_appointments')
    service           = models.ForeignKey(Service, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='appointments')
    service_name      = models.CharField(max_length=200, blank=True)   # snapshot
    healer            = models.ForeignKey(Healer, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='appointments')
    appointment_date  = models.DateField(null=True, blank=True)
    preferred_time    = models.CharField(max_length=10, choices=TIME_CHOICES, blank=True)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                        default='pending', db_index=True)
    contact_name      = models.CharField(max_length=200)
    contact_email     = models.EmailField(blank=True)
    contact_phone     = models.CharField(max_length=20)
    notes             = models.TextField(blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['healer', 'appointment_date', 'preferred_time'],
                condition=models.Q(status='confirmed'),
                name='unique_confirmed_healer_slot',
            ),
        ]

    def __str__(self):
        return f'{self.contact_name} — {self.service_name or "General"} ({self.status})'

    def save(self, *args, **kwargs):
        if self.service and not self.service_name:
            self.service_name = self.service.title
        super().save(*args, **kwargs)

    def conflicts_with_confirmed(self):
        """
        True if a SPECIFIC healer already has a CONFIRMED appointment at
        this exact date+time. This only means something once a healer is
        assigned, so it's used by staff confirmation
        (dashboard.views.appointment_update_status), where a healer has
        been picked, and returns False if no healer is set.

        For public booking, which doesn't collect a healer, use
        slot_has_available_healer() instead -- checking "is any single
        healer busy" there would wrongly reject a request just because
        one particular healer (not necessarily the one who'll be
        assigned) already has something else booked.
        """
        if not (self.appointment_date and self.preferred_time and self.healer_id):
            return False
        qs = Appointment.objects.filter(
            status='confirmed',
            appointment_date=self.appointment_date,
            preferred_time=self.preferred_time,
            healer_id=self.healer_id,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.exists()

    @classmethod
    def slot_has_available_healer(cls, appointment_date, preferred_time):
        """
        Used by the public booking form (api.forms.AppointmentForm.clean),
        which doesn't collect a healer. Returns False only if EVERY active
        healer already has a confirmed appointment at this exact
        date+time -- i.e. the clinic genuinely has no capacity then.
        Builds on the same 'confirmed' + date+time filter as
        conflicts_with_confirmed() rather than a separate, unrelated
        conflict-checking system.
        """
        if not (appointment_date and preferred_time):
            return True
        total_active_healers = Healer.objects.filter(is_active=True).count()
        if total_active_healers == 0:
            # No healer roster configured yet -- don't block bookings on
            # missing catalog data; staff will sort out assignment.
            return True
        busy_healer_count = (Appointment.objects
                              .filter(status='confirmed', appointment_date=appointment_date,
                                      preferred_time=preferred_time, healer__is_active=True)
                              .values('healer_id').distinct().count())
        return busy_healer_count < total_active_healers


# ── BLOG POST ─────────────────────────────────────────────────────────────────
class BlogPost(models.Model):
    title        = models.CharField(max_length=300)
    slug         = models.SlugField(unique=True, blank=True)
    excerpt      = models.CharField(max_length=400)
    content      = models.TextField()
    image        = CloudinaryField('image', folder='daaru/blog', blank=True, null=True)
    category     = models.CharField(max_length=100, blank=True)
    author       = models.CharField(max_length=100, default='Daaru Najat Team')
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        from django.utils import timezone
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def reading_time(self):
        word_count = len(self.content.split())
        return max(1, round(word_count / 200))


# ── INQUIRY ───────────────────────────────────────────────────────────────────
class Inquiry(models.Model):
    name       = models.CharField(max_length=200)
    email      = models.EmailField(blank=True)
    phone      = models.CharField(max_length=20, blank=True)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Inquiries'

    def __str__(self):
        return f'Inquiry from {self.name}'


# ── TESTIMONIAL ───────────────────────────────────────────────────────────────
class Testimonial(models.Model):
    name        = models.CharField(max_length=200)
    location    = models.CharField(max_length=100, blank=True)
    content     = models.TextField()
    condition   = models.CharField(max_length=100, blank=True,
                                   help_text='e.g. Fibroid Treatment, Diabetes')
    rating      = models.PositiveSmallIntegerField(default=5)
    is_approved = models.BooleanField(default=False, db_index=True)
    sort_order  = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return f'{self.name} — {self.condition or "General"}'


# ── SUBSCRIBER ────────────────────────────────────────────────────────────────
class Subscriber(models.Model):
    email         = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


# ── NOTIFICATION ──────────────────────────────────────────────────────────────
class Notification(models.Model):
    TYPE_CHOICES = [
        ('appointment',    'New Appointment'),
        ('inquiry',        'New Inquiry'),
        ('product_order',  'New Product Order'),
        ('subscriber',     'New Subscriber'),
        ('general',        'General'),
    ]

    type       = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general')
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
