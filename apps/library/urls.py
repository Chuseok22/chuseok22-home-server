from django.urls import path

from apps.library.views import StudyRoomListView

urlpatterns = [
    path('study-rooms/', StudyRoomListView.as_view(), name='study-room-list'),
]
