from tempfile import TemporaryDirectory

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from user_app.models import User

from .models import Project


class ProjectTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.owner = User.objects.create_user(email="owner@example.com", name="Иван", surname="Петров")
        self.projects = [Project.objects.create(name=f"Проект {number}", owner=self.owner) for number in range(13)]

    def test_home_redirect_and_project_pagination(self):
        url = reverse("projects:project_list")
        self.assertRedirects(self.client.get("/"), url)
        response = self.client.get(url)
        self.assertEqual(len(response.context["page_obj"]), 12)
        self.assertEqual(response.context["page_obj"][0], self.projects[-1])
        self.assertEqual(len(self.client.get(url, {"page": 2}).context["page_obj"]), 1)
        self.assertEqual(self.client.get(url, {"page": "invalid"}).status_code, 200)

    def test_closed_project_is_available_only_by_direct_link(self):
        project = self.projects[-1]
        project.status = Project.Status.CLOSED
        project.save()
        response = self.client.get(reverse("projects:project_list"))
        self.assertNotIn(project, response.context["projects"])
        self.assertContains(self.client.get(project.get_absolute_url()), project.name)

    def test_invalid_status_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Project.objects.create(name="Ошибка", owner=self.owner, status="wrong")

    def test_user_relations_and_owner_deletion(self):
        project = self.projects[0]
        project.participants.add(self.owner)
        self.owner.favorites.add(project)
        self.assertIn(project, self.owner.participated_projects.all())
        self.assertIn(self.owner, project.interested_users.all())
        self.owner.delete()
        self.assertFalse(Project.objects.exists())

    def test_public_lists_and_missing_pages(self):
        response = self.client.get(reverse("users:participants"))
        self.assertContains(response, "Иван Петров")
        self.assertEqual(self.client.get("/projects/99999/").status_code, 404)
        self.assertEqual(self.client.get("/users/99999/").status_code, 404)
        self.assertEqual(self.client.post(reverse("projects:project_list")).status_code, 405)
