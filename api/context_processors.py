from .models import SiteSettings, Notification


def site_settings(request):
    site = SiteSettings.get()
    unread_notifications = 0

    if request.user.is_authenticated and request.user.is_staff:
        unread_notifications = Notification.objects.filter(is_read=False).count()

    return {
        'site': site,
        'unread_notifications': unread_notifications,
    }