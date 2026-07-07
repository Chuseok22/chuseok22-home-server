from django.urls import path

from apps.blog.views import BlogIngestView

urlpatterns = [
    path('ingest/', BlogIngestView.as_view(), name='blog-ingest'),
]
