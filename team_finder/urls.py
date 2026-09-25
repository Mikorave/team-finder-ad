from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from projects import views as project_views
from users import views as user_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # projects
    path('', project_views.project_list, name='project_list'),
    path('projects/create/', project_views.create_project, name='create_project'),
    path('projects/<int:pk>/', project_views.project_details, name='project_details'),
    path('projects/favorites/', project_views.favorite_projects, name='favorite_projects'),

    # users
    path('users/login/', user_views.login_view, name='login'),
    path('users/register/', user_views.register_view, name='register'),
    path('users/<int:pk>/', user_views.user_details, name='user_details'),
    path('users/edit/', user_views.edit_profile, name='edit_profile'),
    path('users/password/', user_views.change_password, name='change_password'),
    path('users/participants/', user_views.participants, name='participants'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)