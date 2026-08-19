from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


def staff_required(view_func):
    """
    Protects every /dashboard/ route. Ordinary patients (even logged in
    via the patient portal) are redirected out — this is enforced here on
    the backend, not just by hiding a link in a template.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('dashboard:login')}?next={request.path}")
        if not request.user.is_staff:
            messages.error(request, "You don't have access to the staff dashboard.")
            return redirect('api:home')
        return view_func(request, *args, **kwargs)
    return wrapper
