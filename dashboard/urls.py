from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('login/',  views.dashboard_login,  name='login'),
    path('logout/', views.dashboard_logout, name='logout'),
    path('',         views.overview, name='overview'),

    path('appointments/',                    views.appointments_list,          name='appointments'),
    path('appointments/<int:pk>/',           views.appointment_detail,         name='appointment_detail'),
    path('appointments/<int:pk>/status/',    views.appointment_update_status,  name='appointment_update_status'),

    path('patients/',            views.patients_list,  name='patients'),
    path('patients/<int:pk>/',   views.patient_detail,  name='patient_detail'),

    path('messages/',            views.messages_list,  name='messages'),
    path('messages/<int:pk>/',   views.message_detail,  name='message_detail'),

    path('notifications/',                       views.notifications_list,          name='notifications'),
    path('notifications/<int:pk>/read/',         views.notification_mark_read,      name='notification_mark_read'),
    path('notifications/mark-all-read/',         views.notifications_mark_all_read, name='notifications_mark_all_read'),

    path('orders/',                     views.orders_list,         name='orders'),
    path('orders/<int:pk>/status/',     views.order_update_status, name='order_update_status'),

    path('services/',                 views.services_list, name='services'),
    path('services/add/',             views.service_edit,  name='service_add'),
    path('services/<int:pk>/edit/',   views.service_edit,  name='service_edit'),

    path('products/',                 views.products_list, name='products'),
    path('products/add/',             views.product_edit,  name='product_add'),
    path('products/<int:pk>/edit/',   views.product_edit,  name='product_edit'),

    path('healers/',                  views.healers_list, name='healers'),
    path('healers/add/',              views.healer_edit,  name='healer_add'),
    path('healers/<int:pk>/edit/',    views.healer_edit,  name='healer_edit'),

    path('blog/',                 views.blog_list, name='blog'),
    path('blog/add/',             views.blog_edit, name='blog_add'),
    path('blog/<int:pk>/edit/',   views.blog_edit, name='blog_edit'),
    path('testimonials/',                     views.testimonials_list,             name='testimonials'),
    path('testimonials/<int:pk>/toggle/',     views.testimonial_toggle_approved,   name='testimonial_toggle'),
    path('subscribers/',   views.subscribers_list,  name='subscribers'),

    path('settings/', views.site_settings, name='site_settings'),
]
