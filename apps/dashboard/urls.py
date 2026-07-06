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

    path('posts/', views.post_list, name='post-list'),
    path('posts/table/', views.post_table_body, name='post-table-body'),
    path('posts/new/', views.post_form, name='post-create'),
    path('posts/<int:pk>/edit/', views.post_form, name='post-update'),
    path('posts/<int:pk>/delete/', views.post_delete, name='post-delete'),

    path('automation/', views.automation_list, name='automation-list'),
    path('automation/table/', views.automation_table_body, name='automation-table-body'),
    path('automation/<str:job_id>/edit/', views.automation_form, name='automation-form'),
    path('automation/<str:job_id>/update/', views.automation_update, name='automation-update'),
]
