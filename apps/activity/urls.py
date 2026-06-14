from django.urls import path

from apps.activity.views import ActivityListView

urlpatterns = [
    path('', ActivityListView.as_view(), name='activity-list'),
]
