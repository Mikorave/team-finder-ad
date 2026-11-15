from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import authenticate
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
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


class AccountTests(TestCase):
    password = "Forest-river-728!"

    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = User.objects.create_user(
            email="anna@example.com", password=self.password, name="Анна", surname="Иванова",
        )
        self.other = User.objects.create_user(
            email="other@example.com", password=self.password, name="Иван", surname="Петров",
            phone="89991234567",
        )

    def profile_data(self, **changes):
        data = {
            "name": "Анна", "surname": "Иванова", "email": "anna@example.com",
            "phone": "", "about": "Разработчик", "github_url": "https://github.com/anna",
        }
        return data | changes

    def test_registration_redirects_to_login_without_signing_in(self):
        response = self.client.post(reverse("users:register"), {
            "email": " NEW@Example.COM ", "name": " Мария ", "surname": "Петрова",
            "password": self.password, "is_staff": "on", "is_superuser": "on",
        }, follow=True)
        self.assertEqual(response.redirect_chain, [(reverse("users:login"), 302)])
        self.assertContains(response, "Аккаунт создан")
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.name, "Мария")
        self.assertTrue(user.check_password(self.password))
        self.assertTrue(user.avatar)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_registration_rejects_duplicate_email_and_weak_password(self):
        for data, field in [
            ({"email": "ANNA@EXAMPLE.COM", "password": self.password}, "email"),
            ({"email": "new@example.com", "password": "12345678"}, "password"),
            ({"email": "new@example.com", "password": self.password, "name": " "}, "name"),
        ]:
            with self.subTest(field=field):
                response = self.client.post(reverse("users:register"), {
                    "name": "Мария", "surname": "Петрова", **data,
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.assertEqual(User.objects.count(), 2)

    def test_login_accepts_email_case_and_preserves_safe_next(self):
        target = self.user.get_absolute_url()
        response = self.client.get(reverse("users:login"), {"next": target})
        self.assertContains(response, f'value="{target}"')
        response = self.client.post(reverse("users:login"), {
            "email": " ANNA@EXAMPLE.COM ", "password": self.password, "next": target,
        })
        self.assertRedirects(response, target)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_rejects_external_next(self):
        for target in ("https://example.org/", "//example.org/", "http://testserver.evil.org/"):
            with self.subTest(target=target):
                response = self.client.post(reverse("users:login"), {
                    "email": self.user.email, "password": self.password, "next": target,
                })
                self.assertRedirects(response, reverse("projects:project_list"))
                self.client.logout()

    def test_wrong_password_and_blocked_user_have_same_error(self):
        url = reverse("users:login")
        response = self.client.post(url, {"email": self.user.email, "password": "wrong"})
        self.assertContains(response, "Неверный email или пароль.")
        self.user.is_active = False
        self.user.save()
        response = self.client.post(url, {"email": self.user.email, "password": self.password})
        self.assertContains(response, "Неверный email или пароль.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_and_password_require_login(self):
        for name in ("edit_profile", "change_password"):
            url = reverse(f"users:{name}")
            for method in (self.client.get, self.client.post):
                response = method(url)
                self.assertRedirects(response, f"{reverse('users:login')}?next={url}")

    def test_edit_profile_updates_only_current_user_and_keeps_url(self):
        self.client.force_login(self.user)
        url = self.user.get_absolute_url()
        response = self.client.get(reverse("users:edit_profile"))
        self.assertEqual(response.context["form"].initial["email"], self.user.email)
        response = self.client.post(reverse("users:edit_profile"), self.profile_data(
            email=" Changed@Example.COM ", phone="89995554433", name="Мария",
            id=self.other.pk, is_staff="on", is_superuser="on",
        ), follow=True)
        self.assertContains(response, "Профиль сохранён")
        self.user.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.user.email, "changed@example.com")
        self.assertEqual(self.user.phone, "+79995554433")
        self.assertEqual(self.user.get_absolute_url(), url)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.other.name, "Иван")
        self.assertEqual(self.other.email, "other@example.com")
        self.assertEqual(authenticate(email="CHANGED@EXAMPLE.COM", password=self.password), self.user)
        self.assertIsNone(authenticate(email="anna@example.com", password=self.password))

    def test_invalid_profile_does_not_save_other_fields(self):
        self.client.force_login(self.user)
        cases = [
            ({"phone": "89991234567"}, "phone"),
            ({"phone": "+79991234567"}, "phone"),
            ({"phone": "+7 (999) 555-44-33"}, "phone"),
            ({"phone": "+19995554433"}, "phone"),
            ({"email": "OTHER@EXAMPLE.COM"}, "email"),
            ({"github_url": "https://github.com.evil.org/anna"}, "github_url"),
            ({"github_url": "https://github.com@evil.org/anna"}, "github_url"),
            ({"github_url": "https://[invalid"}, "github_url"),
            ({"about": "x" * 257}, "about"),
        ]
        for changes, field in cases:
            with self.subTest(changes=changes):
                response = self.client.post(reverse("users:edit_profile"), self.profile_data(name="Другая", **changes))
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.user.refresh_from_db()
                self.assertEqual(self.user.name, "Анна")
                self.assertEqual(self.user.phone, "")

    def test_phone_is_optional_and_current_number_is_allowed(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("users:edit_profile"), self.profile_data(
            email=self.other.email, phone="89991234567",
        ))
        self.assertEqual(response.status_code, 302)
        self.other.refresh_from_db()
        self.assertEqual(self.other.phone, "+79991234567")
        response = self.client.post(reverse("users:edit_profile"), self.profile_data(email=self.other.email))
        self.assertEqual(response.status_code, 302)
        self.other.refresh_from_db()
        self.assertEqual(self.other.phone, "")

    def test_phone_uniqueness_is_enforced_by_database(self):
        self.user.phone = "89991234567"
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.user.save()

    def test_avatar_upload_and_invalid_file(self):
        self.client.force_login(self.user)
        output = BytesIO()
        Image.new("RGB", (32, 32), "green").save(output, format="PNG")
        upload = SimpleUploadedFile("avatar.png", output.getvalue(), content_type="image/png")
        response = self.client.post(reverse("users:edit_profile"), self.profile_data(avatar=upload))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        avatar_name = self.user.avatar.name
        with self.user.avatar.open() as avatar, Image.open(avatar) as image:
            self.assertEqual(image.size, (32, 32))
        upload = SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")
        response = self.client.post(reverse("users:edit_profile"), self.profile_data(avatar=upload))
        self.assertIn("avatar", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar.name, avatar_name)

    def test_password_change_keeps_current_session_and_invalidates_other_session(self):
        self.client.force_login(self.user)
        other_client = Client()
        other_client.force_login(self.user)
        new_password = "Mountain-lake-913!"
        response = self.client.post(reverse("users:change_password"), {
            "old_password": self.password, "new_password1": new_password, "new_password2": new_password,
        }, follow=True)
        self.assertContains(response, "Пароль изменён")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertIsNone(authenticate(email=self.user.email, password=self.password))
        self.assertEqual(authenticate(email=self.user.email, password=new_password), self.user)
        self.assertEqual(other_client.get(reverse("users:edit_profile")).status_code, 302)

    def test_invalid_password_change_preserves_password(self):
        self.client.force_login(self.user)
        for changes, field in [
            ({"old_password": "wrong"}, "old_password"),
            ({"new_password2": "mismatch"}, "new_password2"),
            ({"new_password1": "12345678", "new_password2": "12345678"}, "new_password2"),
        ]:
            with self.subTest(field=field):
                response = self.client.post(reverse("users:change_password"), {
                    "old_password": self.password,
                    "new_password1": "Mountain-lake-913!", "new_password2": "Mountain-lake-913!",
                    **changes,
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password(self.password))

    def test_logout_requires_post_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        url = reverse("users:logout")
        self.assertEqual(client.get(url).status_code, 405)
        self.assertEqual(client.post(url).status_code, 403)
        self.assertIn("_auth_user_id", client.session)
        client.get(self.user.get_absolute_url())
        response = client.post(url, {"csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertRedirects(response, reverse("projects:project_list"))
        self.assertNotIn("_auth_user_id", client.session)

    def test_account_forms_are_csrf_protected(self):
        client = Client(enforce_csrf_checks=True)
        for name in ("register", "login"):
            self.assertEqual(client.post(reverse(f"users:{name}"), {}).status_code, 403)
        client.force_login(self.user)
        for name in ("edit_profile", "change_password"):
            self.assertEqual(client.post(reverse(f"users:{name}"), {}).status_code, 403)
