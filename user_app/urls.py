from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("list/", views.participants, name="participants"),
    path("<int:pk>/", views.user_details, name="user_details"),
]
