from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone

from .avatars import create_avatar
from .managers import UserManager
from .validators import normalize_phone, validate_github_url, validate_phone


class Skill(models.Model):
    name = models.CharField("Название", max_length=124, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "навык"
        verbose_name_plural = "навыки"
        constraints = [
            models.UniqueConstraint(Lower("name"), name="unique_skill_name_ci"),
        ]

    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("Электронная почта", unique=True)
    name = models.CharField("Имя", max_length=124)
    surname = models.CharField("Фамилия", max_length=124)
    avatar = models.ImageField("Аватар", upload_to="avatars/%Y/%m/", blank=True)
    phone = models.CharField("Телефон", max_length=12, blank=True, validators=[validate_phone])
    github_url = models.URLField("GitHub", blank=True, validators=[validate_github_url])
    about = models.TextField("О себе", max_length=256, blank=True)
    skills = models.ManyToManyField(Skill, verbose_name="Навыки", related_name="users", blank=True)
    favorites = models.ManyToManyField(
        "project_app.Project", verbose_name="Избранные проекты",
        related_name="interested_users", blank=True,
    )
    is_active = models.BooleanField("Активен", default=True)
    is_staff = models.BooleanField("Доступ в админку", default=False)
    date_joined = models.DateTimeField("Дата регистрации", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "surname"]

    class Meta:
        ordering = ["-date_joined", "-pk"]
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_user_email_ci"),
            models.UniqueConstraint(fields=["phone"], condition=~models.Q(phone=""), name="unique_user_phone"),
        ]

    def __str__(self):
        return f"{self.name} {self.surname}"

    def get_full_name(self):
        return str(self)

    def get_short_name(self):
        return self.name

    def get_absolute_url(self):
        return reverse("users:user_details", args=[self.pk])

    def clean(self):
        super().clean()
        self.email = self.email.strip().lower()
        self.phone = normalize_phone(self.phone)

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        self.phone = normalize_phone(self.phone)
        if not self.avatar:
            avatar = create_avatar(self.name)
            self.avatar.save(avatar.name, avatar, save=False)
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = set(kwargs["update_fields"]) | {"avatar"}
        super().save(*args, **kwargs)
