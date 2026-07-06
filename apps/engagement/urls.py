from django.urls import path

from apps.engagement import views

app_name = 'engagement'

urlpatterns = [
    path('<str:app_label>/<str:model>/<int:object_id>/comments/', views.comment_create, name='comment-create'),
    path('<str:app_label>/<str:model>/<int:object_id>/like/toggle/', views.like_toggle, name='like-toggle'),
]
