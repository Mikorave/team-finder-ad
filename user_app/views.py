from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from .forms import LoginForm, ProfileForm, RegistrationForm
from .models import User


@sensitive_post_parameters("password")
@never_cache
@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("projects:project_list")
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error("email", "Эта электронная почта уже используется.")
        else:
            messages.success(request, "Аккаунт создан. Войдите с электронной почтой и паролем.")
            return redirect("users:login")
    return render(request, "users/register.html", {"form": form})


@sensitive_post_parameters("password")
@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("projects:project_list")
    next_url = request.POST.get("next", "") if request.method == "POST" else request.GET.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        next_url = ""
    form = LoginForm(request, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        return redirect(next_url or settings.LOGIN_REDIRECT_URL)
    return render(request, "users/login.html", {"form": form, "next": next_url})


@require_POST
def logout_view(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
@require_http_methods(["GET", "POST"])
def edit_profile(request):
    form = ProfileForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            form.add_error(None, "Электронная почта или телефон уже используются. Проверьте данные.")
        else:
            messages.success(request, "Профиль сохранён.")
            return redirect(user)
    return render(request, "users/edit_profile.html", {"form": form})


@sensitive_post_parameters("old_password", "new_password1", "new_password2")
@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Пароль изменён.")
        return redirect(user)
    return render(request, "users/change_password.html", {"form": form})


@require_safe
def participants(request):
    users = User.objects.filter(is_active=True).prefetch_related("skills")
    page = Paginator(users, 12).get_page(request.GET.get("page"))
    return render(request, "users/participants.html", {"page_obj": page})


@require_safe
def user_details(request, pk):
    user = get_object_or_404(
        User.objects.prefetch_related("skills", "owned_projects__participants"), pk=pk, is_active=True,
    )
    return render(request, "users/user-details.html", {"user": user})
