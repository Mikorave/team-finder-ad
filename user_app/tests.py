from tempfile import TemporaryDirectory

from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Skill, User


class UserTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = User.objects.create_user(
            email="Anna@Example.COM", password="test-password-42",
            name="Анна", surname="Иванова",
        )

    def test_email_login_and_generated_avatar(self):
        self.assertEqual(self.user.email, "anna@example.com")
        self.assertEqual(authenticate(email=self.user.email, password="test-password-42"), self.user)
        self.assertNotEqual(self.user.password, "test-password-42")
        with self.user.avatar.open() as avatar, Image.open(avatar) as image:
            self.assertEqual(image.size, (256, 256))
            self.assertGreater(len(image.getcolors(maxcolors=65536)), 1)

    def test_email_must_be_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                email="ANNA@example.com", name="Анна", surname="Другая",
            )

    def test_skill_name_must_be_unique_ignoring_case(self):
        Skill.objects.create(name="Python")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Skill.objects.create(name="python")

    def test_skill_can_belong_to_multiple_users(self):
        other = User.objects.create_user(email="other@example.com", name="Иван", surname="Петров")
        skill = Skill.objects.create(name="Python")
        self.user.skills.add(skill)
        other.skills.add(skill)
        self.user.skills.remove(skill)
        self.assertTrue(other.skills.filter(pk=skill.pk).exists())
        self.assertTrue(Skill.objects.filter(pk=skill.pk).exists())

    def test_public_profile_and_inactive_user(self):
        url = self.user.get_absolute_url()
        self.assertContains(self.client.get(url), "Анна Иванова")
        self.user.name = "Мария"
        self.user.save()
        self.assertEqual(self.user.get_absolute_url(), url)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertIsNone(authenticate(email=self.user.email, password="test-password-42"))

    def test_admin_can_create_user_and_change_password(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="admin-password-42", name="Админ", surname="Сайта",
        )
        self.client.force_login(admin)
        response = self.client.post(reverse("admin:user_app_user_add"), {
            "email": "new@example.com", "name": "Новый", "surname": "Участник",
            "password1": "complex-test-password-42", "password2": "complex-test-password-42",
            "usable_password": "true",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="new@example.com")
        self.assertTrue(user.check_password("complex-test-password-42"))
        response = self.client.post(reverse("admin:auth_user_password_change", args=[user.pk]), {
            "password1": "another-complex-password-42", "password2": "another-complex-password-42",
            "usable_password": "true",
        })
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password("another-complex-password-42"))
