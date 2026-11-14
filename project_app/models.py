from django.conf import settings
from django.db import models
from django.urls import reverse


class Project(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Открыт"
        CLOSED = "closed", "Закрыт"

    name = models.CharField("Название", max_length=200)
    description = models.TextField("Описание", blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Автор",
        on_delete=models.CASCADE, related_name="owned_projects",
    )
    created_at = models.DateTimeField("Дата публикации", auto_now_add=True, db_index=True)
    github_url = models.URLField("GitHub", blank=True)
    status = models.CharField("Статус", max_length=6, choices=Status.choices, default=Status.OPEN)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, verbose_name="Участники",
        related_name="participated_projects", blank=True,
    )

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "проект"
        verbose_name_plural = "проекты"
        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=["open", "closed"]),
                                   name="valid_project_status"),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("projects:project_details", args=[self.pk])
