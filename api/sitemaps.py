from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Service, Product, Healer, BlogPost


class StaticViewSitemap(Sitemap):
    """
    Public, indexable static pages only. Deliberately does NOT include
    /dashboard/, /portal/, /accounts/login/, /accounts/register/, or any
    other private/internal/auth-gated route.
    """
    changefreq = 'weekly'

    _priority_overrides = {'api:home': 1.0}

    def items(self):
        return [
            'api:home', 'api:about', 'api:services', 'api:products',
            'api:healers', 'api:blog', 'api:contact', 'api:book',
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self._priority_overrides.get(item, 0.7)


class ServiceSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.8

    def items(self):
        return Service.objects.filter(active=True)

    def location(self, obj):
        return reverse('api:service_detail', args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at


class ProductSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Product.objects.filter(active=True)

    def location(self, obj):
        return reverse('api:product_detail', args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at


class HealerSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return Healer.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('api:healer_detail', args=[obj.pk])

    def lastmod(self, obj):
        return obj.updated_at


class BlogSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return BlogPost.objects.filter(is_published=True)

    def location(self, obj):
        return reverse('api:blog_detail', args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {
    'static':   StaticViewSitemap,
    'services': ServiceSitemap,
    'products': ProductSitemap,
    'healers':  HealerSitemap,
    'blog':     BlogSitemap,
}
