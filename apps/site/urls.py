from django.urls import path

from apps.site import views

app_name = 'site'

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/', views.projects, name='projects'),
    path('blog/', views.blog_list, name='blog-list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog-detail'),
    path('blog/<slug:slug>/edit/', views.blog_post_edit, name='blog-post-edit'),
    path('blog/edit/upload-image/', views.blog_post_upload_image, name='blog-post-upload-image'),
    path('lab/', views.lab_index, name='lab-index'),
    path('lab/library/', views.lab_library, name='lab-library'),
    path('lab/library/rooms/', views.lab_library_rooms, name='lab-library-rooms'),
    path('lab/library/reserve-form/', views.lab_library_reserve_form, name='lab-library-reserve-form'),
    path('lab/library/reserve/', views.lab_library_reserve, name='lab-library-reserve'),
    path('lab/library/my-reservations/', views.lab_library_my_reservations, name='lab-library-my-reservations'),
    path(
        'lab/library/attendees/<int:pk>/',
        views.lab_library_attendee_delete,
        name='lab-library-attendee-delete',
    ),
    path('lab/student/', views.lab_student, name='lab-student'),
    path('lab/student/search/', views.lab_student_search, name='lab-student-search'),
    path('lab/lecture/', views.lab_lecture, name='lab-lecture'),
    path('lab/lecture/courses/', views.lab_lecture_courses, name='lab-lecture-courses'),
    path('lab/lecture/download/', views.lab_lecture_download, name='lab-lecture-download'),
    path(
        'lab/lecture/irregular/courses/',
        views.lab_lecture_irregular_courses,
        name='lab-lecture-irregular-courses',
    ),
    path(
        'lab/lecture/irregular/download/',
        views.lab_lecture_irregular_download,
        name='lab-lecture-irregular-download',
    ),
    path('lab/lecture/history/', views.lab_lecture_history, name='lab-lecture-history'),
    path(
        'lab/lecture/history/<int:job_id>/delete/',
        views.lab_lecture_history_delete,
        name='lab-lecture-history-delete',
    ),
    path(
        'lab/lecture/history/<int:job_id>/file/',
        views.lab_lecture_history_file,
        name='lab-lecture-history-file',
    ),
    path('certifications/', views.certifications, name='certifications'),
    path('places/', views.places, name='places'),
    path('places/suggest/', views.place_suggest, name='place-suggest'),
    path('places/<int:pk>/', views.place_detail, name='place-detail'),
    path('chat/', views.chat, name='chat'),
]
