from django.urls import path

from apps.sejong.student.views import StudentSearchView

urlpatterns = [
    path('search/', StudentSearchView.as_view(), name='student-search'),
]
