from django.urls import path

from apps.dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),

    path('projects/', views.project_list, name='project-list'),
    path('projects/table/', views.project_table_body, name='project-table-body'),
    path('projects/new/', views.project_form, name='project-create'),
    path('projects/<int:pk>/edit/', views.project_form, name='project-update'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project-delete'),
]
