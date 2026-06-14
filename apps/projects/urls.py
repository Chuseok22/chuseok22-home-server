from django.urls import path

from apps.projects.views import ProjectListView

urlpatterns = [
    path('', ProjectListView.as_view(), name='project-list'),
]
