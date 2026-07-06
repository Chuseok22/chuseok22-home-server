from django.urls import path

from apps.site import views

app_name = 'site'

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/', views.projects, name='projects'),
    path('blog/', views.blog_list, name='blog-list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog-detail'),
    path('lab/', views.lab_index, name='lab-index'),
    path('lab/library/', views.lab_library, name='lab-library'),
    path('lab/library/rooms/', views.lab_library_rooms, name='lab-library-rooms'),
    path('lab/library/reserve-form/', views.lab_library_reserve_form, name='lab-library-reserve-form'),
    path('lab/library/reserve/', views.lab_library_reserve, name='lab-library-reserve'),
    path('lab/student/', views.lab_student, name='lab-student'),
    path('lab/student/search/', views.lab_student_search, name='lab-student-search'),
]
