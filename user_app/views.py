from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from .models import User


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
