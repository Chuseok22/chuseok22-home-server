from django.urls import path

from apps.sejong.library.views import (
    ReservationAttendeeDestroyView,
    ReservationAttendeeListCreateView,
    StudyRoomListView,
    StudyRoomReserveView,
)

urlpatterns = [
    path('study-rooms/', StudyRoomListView.as_view(), name='study-room-list'),
    path('study-rooms/reserve/', StudyRoomReserveView.as_view(), name='study-room-reserve'),
    path('study-rooms/attendees/', ReservationAttendeeListCreateView.as_view(), name='study-room-attendee-list'),
    path('study-rooms/attendees/<int:pk>/', ReservationAttendeeDestroyView.as_view(), name='study-room-attendee-destroy'),
]
