from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from .models import Project


@require_safe
def project_list(request):
    projects = Project.objects.filter(status=Project.Status.OPEN).select_related("owner").prefetch_related("participants")
    page = Paginator(projects, 12).get_page(request.GET.get("page"))
    return render(request, "projects/project_list.html", {"projects": page.object_list, "page_obj": page})


@require_safe
def project_details(request, pk):
    project = get_object_or_404(Project.objects.select_related("owner").prefetch_related("participants"), pk=pk)
    is_participant = request.user.is_authenticated and project.participants.filter(pk=request.user.pk).exists()
    return render(request, "projects/project-details.html", {"project": project, "is_participant": is_participant})
