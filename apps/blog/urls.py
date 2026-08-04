from django.urls import path

from apps.blog.views import BlogCategoryListView, BlogIngestImageUploadView, BlogIngestView

urlpatterns = [
    path('ingest/', BlogIngestView.as_view(), name='blog-ingest'),
    path('ingest/images/', BlogIngestImageUploadView.as_view(), name='blog-ingest-image-upload'),
    path('categories/', BlogCategoryListView.as_view(), name='blog-category-list'),
]
