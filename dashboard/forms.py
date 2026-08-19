from django import forms
from api.models import SiteSettings, Service, Product, Healer, BlogPost

INPUT = 'form-input'


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            'site_name', 'tagline', 'logo', 'favicon',
            'primary_color', 'secondary_color', 'accent_color',
            'contact_email', 'contact_phone', 'contact_phone2', 'whatsapp_number', 'whatsapp_greeting',
            'address', 'city', 'country',
            'hero_headline', 'hero_subheadline', 'hero_cta_primary', 'hero_cta_secondary', 'hero_video_url',
            'social_facebook', 'social_instagram', 'social_tiktok',
            'footer_description', 'seo_title', 'seo_description', 'seo_keywords',
            'about_title', 'about_description', 'about_mission', 'about_vision', 'registration_no',
        ]
        widgets = {
            'whatsapp_greeting':  forms.Textarea(attrs={'class': INPUT, 'rows': 3}),
            'address':            forms.Textarea(attrs={'class': INPUT, 'rows': 2}),
            'hero_subheadline':   forms.Textarea(attrs={'class': INPUT, 'rows': 3}),
            'footer_description': forms.Textarea(attrs={'class': INPUT, 'rows': 3}),
            'seo_description':    forms.Textarea(attrs={'class': INPUT, 'rows': 2}),
            'seo_keywords':       forms.Textarea(attrs={'class': INPUT, 'rows': 2}),
            'about_description':  forms.Textarea(attrs={'class': INPUT, 'rows': 3}),
            'about_mission':      forms.Textarea(attrs={'class': INPUT, 'rows': 2}),
            'about_vision':       forms.Textarea(attrs={'class': INPUT, 'rows': 2}),
            'primary_color':      forms.TextInput(attrs={'class': INPUT, 'type': 'color'}),
            'secondary_color':    forms.TextInput(attrs={'class': INPUT, 'type': 'color'}),
            'accent_color':       forms.TextInput(attrs={'class': INPUT, 'type': 'color'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in self.Meta.widgets:
                field.widget.attrs.setdefault('class', INPUT)

    def clean_contact_phone(self):
        phone = self.cleaned_data.get('contact_phone', '').strip()
        digits = ''.join(c for c in phone if c.isdigit())
        if phone and len(digits) < 8:
            raise forms.ValidationError('Please enter a valid phone number.')
        return phone

    def clean_whatsapp_number(self):
        number = self.cleaned_data.get('whatsapp_number', '').strip()
        digits = ''.join(c for c in number if c.isdigit())
        if number and len(digits) < 8:
            raise forms.ValidationError('Please enter digits only, e.g. 2348012345678.')
        return digits

    def clean_hero_video_url(self):
        url = self.cleaned_data.get('hero_video_url', '').strip()
        return url


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['title', 'short_description', 'description', 'icon_name', 'category',
                  'duration_minutes', 'price', 'image', 'is_featured', 'active', 'sort_order']
        widgets = {
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.CheckboxInput,)):
                continue
            field.widget.attrs.setdefault('class', INPUT)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'short_description', 'description', 'category',
                  'price', 'image', 'is_featured', 'active', 'sort_order']
        widgets = {
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.CheckboxInput,)):
                continue
            field.widget.attrs.setdefault('class', INPUT)


class HealerForm(forms.ModelForm):
    class Meta:
        model = Healer
        fields = ['full_name', 'specialty', 'bio', 'experience_years', 'languages',
                  'whatsapp_number', 'phone', 'email', 'photo', 'is_featured', 'is_active']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.CheckboxInput,)):
                continue
            field.widget.attrs.setdefault('class', INPUT)


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'excerpt', 'content', 'image', 'category', 'author', 'is_published']
        widgets = {
            'excerpt': forms.Textarea(attrs={'rows': 2}),
            'content': forms.Textarea(attrs={'rows': 12}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.CheckboxInput,)):
                continue
            field.widget.attrs.setdefault('class', INPUT)

