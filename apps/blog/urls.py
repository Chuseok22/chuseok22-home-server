from django.urls import path

from apps.blog.views import BlogCategoryListView, BlogIngestView

urlpatterns = [
    path('ingest/', BlogIngestView.as_view(), name='blog-ingest'),
    path('categories/', BlogCategoryListView.as_view(), name='blog-category-list'),
]
